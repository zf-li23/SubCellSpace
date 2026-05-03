from __future__ import annotations

from typing import TYPE_CHECKING, Any

import anndata as ad
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.neighbors import kneighbors_graph

from ..constants import COL_CELL_ID, COL_X, COL_Y, resolve_col_strict
from ..models import StepResult
from ..registry import declare_capabilities, register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

# ── Backend availability flags ─────────────────────────────────────────────

_HDBSCAN_AVAILABLE: bool = False
_PHENOGRAPH_AVAILABLE: bool = False

try:
    import hdbscan  # noqa: F401
    _HDBSCAN_AVAILABLE = True
except ImportError:
    pass

try:
    import phenograph  # noqa: F401
    _PHENOGRAPH_AVAILABLE = True
except ImportError:
    pass


# ── per-backend clustering functions ──────────────────────────────────────


def _hdbscan_subcellular_domains(
    cell_df: pd.DataFrame,
    min_cluster_size: int = 30,
    min_samples: int = 5,
) -> pd.Series:
    try:
        import hdbscan
    except ImportError as exc:
        raise ImportError("HDBSCAN backend requires 'hdbscan' to be installed.") from exc

    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    n = len(coords)
    if n < min_cluster_size:
        return pd.Series(["0"] * n, index=cell_df.index)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples,
                                metric="euclidean", algorithm="best")
    labels = clusterer.fit_predict(coords)
    return pd.Series(np.where(labels == -1, "noise", labels.astype(str)), index=cell_df.index)


def _dbscan_subcellular_domains(cell_df, eps=20.0, min_samples=10):
    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    if len(coords) < min_samples:
        return pd.Series(["0"] * len(cell_df), index=cell_df.index)
    clustering = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1).fit(coords)
    labels = clustering.labels_
    return pd.Series(np.where(labels == -1, "noise", labels.astype(str)), index=cell_df.index)


def _leiden_spatial_subcellular_domains(cell_df, n_neighbors=25, resolution=0.5, random_state=42):
    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    n = len(coords)
    if n < n_neighbors + 1:
        return pd.Series(["0"] * n, index=cell_df.index)
    adj = kneighbors_graph(coords, n_neighbors=n_neighbors, mode="connectivity", n_jobs=-1)
    adj = adj.maximum(adj.T)
    import scanpy as sc
    adata_tmp = ad.AnnData(X=coords, dtype=np.float64)
    adata_tmp.obsp["spatial_connectivities"] = adj.tocsc()
    try:
        sc.tl.leiden(adata_tmp, resolution=resolution, random_state=random_state,
                     adjacency=adj.tocsc(), key_added="spatial_cluster",
                     flavor="igraph", n_iterations=2)
    except (ImportError, AttributeError):
        sc.tl.leiden(adata_tmp, resolution=resolution, random_state=random_state,
                     adjacency=adj.tocsc(), key_added="spatial_cluster")
    labels = adata_tmp.obs["spatial_cluster"].to_numpy()
    return pd.Series(labels.astype(str), index=cell_df.index)


def _phenograph_subcellular_domains(cell_df, k=30, min_cluster_size=10):
    try:
        import phenograph
    except ImportError as exc:
        raise ImportError("PhenoGraph backend requires 'PhenoGraph' to be installed.") from exc
    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    n = len(coords)
    if n < max(k + 1, min_cluster_size):
        return pd.Series(["0"] * n, index=cell_df.index)
    communities, _ = phenograph.cluster(coords, k=k, min_cluster_size=min_cluster_size,
                                        primary_metric="euclidean", n_jobs=-1)
    return pd.Series(communities.astype(str), index=cell_df.index)


def _none_subcellular_domains(cell_df):
    return pd.Series(["0"] * len(cell_df), index=cell_df.index)


# Register backends (order: (step_name, backend_name))
register_backend("subcellular_spatial_domain", "hdbscan")(_hdbscan_subcellular_domains)
register_backend("subcellular_spatial_domain", "dbscan")(_dbscan_subcellular_domains)
register_backend("subcellular_spatial_domain", "leiden_spatial")(_leiden_spatial_subcellular_domains)
register_backend("subcellular_spatial_domain", "phenograph")(_phenograph_subcellular_domains)
register_backend("subcellular_spatial_domain", "none")(_none_subcellular_domains)

declare_capabilities("subcellular_spatial_domain", "hdbscan", ["subcellular_domains", "rna_localization"])
declare_capabilities("subcellular_spatial_domain", "dbscan", ["subcellular_domains", "rna_localization"])
declare_capabilities("subcellular_spatial_domain", "leiden_spatial", ["subcellular_domains", "rna_localization"])
declare_capabilities("subcellular_spatial_domain", "phenograph", ["subcellular_domains", "rna_localization"])
declare_capabilities("subcellular_spatial_domain", "none", [])

# Dispatch table
_CLUSTER_FUNCS = {
    "hdbscan": _hdbscan_subcellular_domains,
    "dbscan": _dbscan_subcellular_domains,
    "leiden_spatial": _leiden_spatial_subcellular_domains,
    "phenograph": _phenograph_subcellular_domains,
    "none": _none_subcellular_domains,
}


# ── main entry point ──────────────────────────────────────────────────────


def run_subcellular_spatial_domain(
    segmented_df: pd.DataFrame,
    adata: ad.AnnData,
    backend: str = "hdbscan",
    # hdbscan params
    hdbscan_min_cluster_size: int = 30,
    hdbscan_min_samples: int = 5,
    # dbscan params
    dbscan_eps: float = 20.0,
    dbscan_min_samples: int = 10,
    # leiden_spatial params
    leiden_n_neighbors: int = 25,
    leiden_resolution: float = 0.5,
) -> StepResult:
    """Assign subcellular spatial domain labels to each transcript within each cell.

    Parameters
    ----------
    segmented_df : pd.DataFrame
        Transcript-level DataFrame.  Must contain a cell-id column and
        ``x`` / ``y`` spatial coordinate columns.
    adata : ad.AnnData
        Cell-level AnnData.
    backend : str
        One of "hdbscan", "dbscan", "leiden_spatial", "none".

    Returns
    -------
    StepResult
        ``.output`` is ``(segmented_df, adata)`` tuple.
        ``.summary`` contains summary statistics.
        ``.backend_used`` is the backend name.
    """
    if backend not in _CLUSTER_FUNCS and backend != "none":
        raise ValueError(
            f"Unknown subcellular spatial domain backend: {backend}. Choose from {list(_CLUSTER_FUNCS) + ['none']}"
        )

    if backend == "none":
        segmented_df = segmented_df.copy()
        segmented_df["subcellular_domain"] = "0"
        for col in ["n_subcellular_domains", "subcellular_domain_distribution"]:
            if col in adata.obs.columns:
                del adata.obs[col]
        summary = {
            "subcellular_spatial_domain_backend": "none",
            "n_cells_processed": 0,
            "n_cells_with_multiple_domains": 0,
            "mean_domains_per_cell": 1.0,
            "total_noise_transcripts": 0,
        }
        return StepResult(
            output=(segmented_df, adata),
            summary=summary,
            backend_used="none",
        )

    # Build kwargs for the chosen backend
    cluster_kwargs: dict
    if backend == "hdbscan":
        cluster_kwargs = {
            "min_cluster_size": hdbscan_min_cluster_size,
            "min_samples": hdbscan_min_samples,
        }
    elif backend == "dbscan":
        cluster_kwargs = {
            "eps": dbscan_eps,
            "min_samples": dbscan_min_samples,
        }
    elif backend == "leiden_spatial":
        cluster_kwargs = {
            "n_neighbors": leiden_n_neighbors,
            "resolution": leiden_resolution,
        }

    cluster_func = _CLUSTER_FUNCS[backend]

    segmented_df = segmented_df.copy()
    segmented_df["subcellular_domain"] = "0"
    all_labels: list[pd.Series] = []
    cell_col = resolve_col_strict(segmented_df.columns, COL_CELL_ID)

    n_cells_with_multiple = 0
    total_noise = 0
    cell_domain_counts: dict[str, int] = {}
    cell_domain_distributions: dict[str, str] = {}

    for cell_id, group in segmented_df.groupby(cell_col, sort=False):
        labels = cluster_func(group, **cluster_kwargs)
        all_labels.append(labels)

        n_domains = labels[labels != "noise"].nunique()
        noise_count = int((labels == "noise").sum())
        total_noise += noise_count

        if n_domains >= 2:
            n_cells_with_multiple += 1

        cell_domain_counts[str(cell_id)] = n_domains
        dist = labels.value_counts().to_dict()
        cell_domain_distributions[str(cell_id)] = ",".join(f"{k}:{v}" for k, v in sorted(dist.items()))

    if all_labels:
        segmented_df["subcellular_domain"] = pd.concat(all_labels)

    # Per-cell statistics → adata.obs
    all_cells = adata.obs_names.astype(str)
    n_domains_series = pd.Series(
        [cell_domain_counts.get(c, 1) for c in all_cells],
        index=adata.obs_names,
    )
    adata.obs["n_subcellular_domains"] = n_domains_series.astype(int)
    adata.obs["subcellular_domain_distribution"] = pd.Series(
        [cell_domain_distributions.get(c, "0:0") for c in all_cells],
        index=adata.obs_names,
    )

    n_cells = int(segmented_df[cell_col].nunique())
    summary = {
        "subcellular_spatial_domain_backend": backend,
        "n_cells_processed": n_cells,
        "n_cells_with_multiple_domains": n_cells_with_multiple,
        "fraction_multi_domain": round(n_cells_with_multiple / max(n_cells, 1), 4),
        "mean_domains_per_cell": round(
            np.mean(list(cell_domain_counts.values())) if cell_domain_counts else 1.0,
            3,
        ),
        "total_noise_transcripts": total_noise,
    }
    # Attach backend-specific params to summary
    summary.update(cluster_kwargs)

    return StepResult(
        output=(segmented_df, adata),
        summary=summary,
        backend_used=backend,
    )


# ── Step runner (registered for pipeline engine) ──────────────────────────


@register_runner("subcellular_spatial_domain")
def _run_subcellular_spatial_domain(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.segmented_df is None or ctx.adata is None:
        raise ValueError("No segmented data or adata before subcellular step")
    result = run_subcellular_spatial_domain(
        ctx.segmented_df,
        ctx.adata,
        backend=backend,
        **params,
    )
    output_tuple = result.output
    if isinstance(output_tuple, tuple) and len(output_tuple) == 2:
        ctx.segmented_df, ctx.adata = output_tuple
    else:
        ctx.adata = result.output
    return result
