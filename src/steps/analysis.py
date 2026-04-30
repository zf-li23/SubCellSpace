from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import scanpy as sc
import squidpy as sq
from sklearn.cluster import KMeans

from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

# ── Backend implementations ────────────────────────────────────────────────


def _cluster_leiden(adata: sc.AnnData, resolution: float, **kwargs: Any) -> str:  # noqa: ARG001
    try:
        sc.tl.leiden(
            adata,
            resolution=resolution,
            key_added="cluster",
            flavor="igraph",
            directed=False,
            n_iterations=2,
        )
        return "leiden_igraph"
    except Exception:
        try:
            sc.tl.leiden(adata, resolution=resolution, key_added="cluster")
            return "leiden_legacy"
        except Exception:
            n_clusters = min(8, max(2, adata.n_obs))
            labels = KMeans(n_clusters=n_clusters, n_init="auto", random_state=0).fit_predict(adata.obsm["X_pca"])
            adata.obs["cluster"] = labels.astype(str)
            return "kmeans_fallback"


def _cluster_kmeans(adata: sc.AnnData, resolution: float, **kwargs: Any) -> str:  # noqa: ARG001
    n_clusters = min(8, max(2, adata.n_obs))
    labels = KMeans(n_clusters=n_clusters, n_init="auto", random_state=0).fit_predict(adata.obsm["X_pca"])
    adata.obs["cluster"] = labels.astype(str)
    return "kmeans"


def _cluster_scvi(
    adata: sc.AnnData,
    resolution: float,
    denoised_expression: pd.DataFrame | np.ndarray | None = None,
) -> str:
    """scVI: single-cell Variational Inference for clustering.

    Uses scVI to learn a latent representation of the data (optionally using
    the denoised expression matrix from a prior step such as spARC), then
    runs Leiden clustering on the scVI latent space.

    Parameters
    ----------
    adata : AnnData
        Filtered, normalised, log1p-transformed AnnData.
    resolution : float
        Leiden clustering resolution.
    denoised_expression : pd.DataFrame or np.ndarray or None
        Optional denoised expression matrix (e.g. from spARC).  If provided,
        this is used as input to scVI instead of ``adata.X``.

    Returns
    -------
    str
        Backend identifier ``"scvi"``.
    """
    import scvi

    # Build a temporary AnnData with the right input for scVI
    adata_tmp = adata.copy()

    if denoised_expression is not None:
        # Use denoised expression matrix (align cells by index)
        if isinstance(denoised_expression, pd.DataFrame):
            common_cells = adata_tmp.obs_names.intersection(denoised_expression.index)
            if len(common_cells) < 2:
                raise ValueError(
                    f"Fewer than 2 common cells between adata ({adata_tmp.n_obs}) "
                    f"and denoised expression ({len(denoised_expression)})."
                )
            adata_tmp = adata_tmp[common_cells].copy()
            adata_tmp.X = denoised_expression.loc[common_cells].to_numpy()
        else:
            # numpy array: assume rows match adata.obs_names order
            if len(denoised_expression) != adata_tmp.n_obs:
                raise ValueError(
                    f"denoised_expression shape mismatch: {len(denoised_expression)} vs "
                    f"adata.n_obs={adata_tmp.n_obs}"
                )
            adata_tmp.X = np.asarray(denoised_expression, dtype=np.float64)
    else:
        # Normal standard preprocessing (already normalised + log1p in caller)
        pass

    # Setup and train scVI
    scvi.model.SCVI.setup_anndata(adata_tmp)
    model = scvi.model.SCVI(adata_tmp)
    model.train(max_epochs=100)

    # Get latent representation
    latent = model.get_latent_representation()
    adata.obsm["X_scVI"] = latent

    # Neighbors + Leiden on scVI latent space
    n_neighbors = min(15, max(2, adata.n_obs - 1))
    n_pcs = min(30, latent.shape[1])
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs, use_rep="X_scVI")
    sc.tl.leiden(adata, resolution=resolution, key_added="cluster")

    return "scvi"


# Register backends
register_backend("analysis", "leiden")(_cluster_leiden)
register_backend("analysis", "kmeans")(_cluster_kmeans)
register_backend("analysis", "scvi")(_cluster_scvi)

# Dispatch table
_CLUSTER_FUNCS = {
    "leiden": _cluster_leiden,
    "kmeans": _cluster_kmeans,
    "scvi": _cluster_scvi,
}


# ── Main entry point ──────────────────────────────────────────────────────


def run_expression_and_spatial_analysis(
    adata: sc.AnnData,
    min_transcripts: int,
    min_genes: int,
    clustering_backend: str,
    leiden_resolution: float,
    denoised_expression: Any = None,
) -> StepResult:
    if clustering_backend not in _CLUSTER_FUNCS:
        raise ValueError(f"Unknown clustering backend: {clustering_backend}. Available: {list(_CLUSTER_FUNCS)}")

    n_obs_before = adata.n_obs

    sc.pp.calculate_qc_metrics(adata, inplace=True, percent_top=[])
    adata = adata[adata.obs["total_counts"] >= min_transcripts].copy()
    adata = adata[adata.obs["n_genes_by_counts"] >= min_genes].copy()

    if adata.n_obs < 2:
        # Not enough cells left after filtering; return early with minimal summary
        summary = {
            "n_obs_before_qc": int(n_obs_before),
            "n_obs_after_qc": int(adata.n_obs),
            "n_vars_after_hvg": int(adata.n_vars),
            "clustering_backend_requested": clustering_backend,
            "clustering_backend_used": "none",
            "leiden_resolution": float(leiden_resolution),
        }
        return StepResult(output=adata, summary=summary, backend_used="none")

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    adata.layers["lognorm"] = adata.X.copy()
    try:
        sc.pp.highly_variable_genes(adata, flavor="cell_ranger", n_top_genes=min(2000, adata.n_vars))
        if "highly_variable" in adata.var and adata.var["highly_variable"].any():
            adata = adata[:, adata.var["highly_variable"]].copy()
    except (IndexError, ValueError):
        pass

    n_comps = min(50, adata.n_obs - 1, adata.n_vars - 1)
    n_comps = max(2, n_comps)
    sc.pp.scale(adata, max_value=10)
    sc.tl.pca(adata, n_comps=n_comps, svd_solver="randomized")
    sc.pp.neighbors(adata, n_neighbors=min(15, max(2, adata.n_obs - 1)), n_pcs=min(30, n_comps))
    cluster_backend_used = _CLUSTER_FUNCS[clustering_backend](adata, resolution=leiden_resolution, denoised_expression=denoised_expression)
    sc.tl.umap(adata)

    sq.gr.spatial_neighbors(adata, spatial_key="spatial", coord_type="generic")

    summary = {
        "n_obs_before_qc": int(n_obs_before),
        "n_obs_after_qc": int(adata.n_obs),
        "n_vars_after_hvg": int(adata.n_vars),
        "clustering_backend_requested": clustering_backend,
        "clustering_backend_used": cluster_backend_used,
        "leiden_resolution": float(leiden_resolution),
    }
    return StepResult(output=adata, summary=summary, backend_used=cluster_backend_used)


# ── Step runner (registered for pipeline engine) ──────────────────────────


@register_runner("analysis")
def _run_analysis(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.adata is None:
        raise ValueError("No AnnData before analysis step")
    min_transcripts = params.get("min_transcripts", 10)
    min_genes = params.get("min_genes", 10)
    clustering_backend = params.get("clustering_backend", backend)
    leiden_resolution = params.get("leiden_resolution", 1.0)
    result = run_expression_and_spatial_analysis(
        ctx.adata,
        min_transcripts=min_transcripts,
        min_genes=min_genes,
        clustering_backend=clustering_backend,
        leiden_resolution=leiden_resolution,
        denoised_expression=ctx.denoised_expression,
    )
    ctx.adata = result.output
    return result
