"""Subcellular Analysis step.

Provides backends for:
- Subcellular spatial domain clustering (hdbscan, dbscan, leiden_spatial, phenograph)
- RNA localization quantification (mean distance to nucleus)
- RNA co-localization network (SCRIN) — real integration, default off

Subcellular domain clustering runs as an optional pre-processing step
inside the runner, controlled by the ``domain_backend`` parameter.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc
from sklearn.cluster import DBSCAN
from sklearn.neighbors import kneighbors_graph

from ..constants import COL_CELL_ID, COL_CELLCOMP, COL_GENE, COL_X, COL_Y, resolve_col_strict
from ..models import StepResult
from ..registry import declare_capabilities, register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)

# ── Backend availability flags ───────────────────────────────────────

_HDBSCAN_AVAILABLE: bool = False
_PHENOGRAPH_AVAILABLE: bool = False
_SCRIN_AVAILABLE: bool = False

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

try:
    import scrin  # noqa: F401

    _SCRIN_AVAILABLE = True
except ImportError:
    pass


# ── Subcellular domain clustering functions ──────────────────────────


def _hdbscan_subcellular_domains(
    cell_df: pd.DataFrame,
    min_cluster_size: int = 30,
    min_samples: int = 5,
) -> pd.Series:
    try:
        import hdbscan as _hdbscan
    except ImportError as exc:
        raise ImportError("HDBSCAN backend requires 'hdbscan' to be installed.") from exc

    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    n = len(coords)
    if n < min_cluster_size:
        return pd.Series(["0"] * n, index=cell_df.index)

    clusterer = _hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        algorithm="best",
    )
    labels = clusterer.fit_predict(coords)
    return pd.Series(np.where(labels == -1, "noise", labels.astype(str)), index=cell_df.index)


def _dbscan_subcellular_domains(
    cell_df: pd.DataFrame,
    eps: float = 20.0,
    min_samples: int = 10,
) -> pd.Series:
    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    if len(coords) < min_samples:
        return pd.Series(["0"] * len(cell_df), index=cell_df.index)
    clustering = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1).fit(coords)
    labels = clustering.labels_
    return pd.Series(np.where(labels == -1, "noise", labels.astype(str)), index=cell_df.index)


def _leiden_spatial_subcellular_domains(
    cell_df: pd.DataFrame,
    n_neighbors: int = 25,
    resolution: float = 0.5,
    random_state: int = 42,
) -> pd.Series:
    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    n = len(coords)
    if n < n_neighbors + 1:
        return pd.Series(["0"] * n, index=cell_df.index)
    adj = kneighbors_graph(coords, n_neighbors=n_neighbors, mode="connectivity", n_jobs=-1)
    adj = adj.maximum(adj.T)
    adata_tmp = ad.AnnData(X=coords, dtype=np.float64)
    adata_tmp.obsp["spatial_connectivities"] = adj.tocsc()
    try:
        sc.tl.leiden(
            adata_tmp,
            resolution=resolution,
            random_state=random_state,
            adjacency=adj.tocsc(),
            key_added="spatial_cluster",
            flavor="igraph",
            n_iterations=2,
        )
    except (ImportError, AttributeError):
        sc.tl.leiden(
            adata_tmp,
            resolution=resolution,
            random_state=random_state,
            adjacency=adj.tocsc(),
            key_added="spatial_cluster",
        )
    labels = adata_tmp.obs["spatial_cluster"].to_numpy()
    return pd.Series(labels.astype(str), index=cell_df.index)


def _phenograph_subcellular_domains(
    cell_df: pd.DataFrame,
    k: int = 30,
    min_cluster_size: int = 10,
) -> pd.Series:
    try:
        import phenograph as _pg
    except ImportError as exc:
        raise ImportError("PhenoGraph backend requires 'PhenoGraph' to be installed.") from exc
    x_col = resolve_col_strict(cell_df.columns, COL_X)
    y_col = resolve_col_strict(cell_df.columns, COL_Y)
    coords = cell_df[[x_col, y_col]].to_numpy(dtype=np.float64)
    n = len(coords)
    if n < max(k + 1, min_cluster_size):
        return pd.Series(["0"] * n, index=cell_df.index)
    communities, _ = _pg.cluster(
        coords, k=k, min_cluster_size=min_cluster_size,
        primary_metric="euclidean", n_jobs=-1,
    )
    return pd.Series(communities.astype(str), index=cell_df.index)


_SUBCELL_DOMAIN_FUNCS: dict[str, Any] = {
    "hdbscan": _hdbscan_subcellular_domains,
    "dbscan": _dbscan_subcellular_domains,
    "leiden_spatial": _leiden_spatial_subcellular_domains,
    "phenograph": _phenograph_subcellular_domains,
    "none": lambda df, **kw: pd.Series(["0"] * len(df), index=df.index),
}

_SUBCELL_DOMAIN_DEFAULTS: dict[str, dict[str, Any]] = {
    "hdbscan": {"min_cluster_size": 30, "min_samples": 5},
    "dbscan": {"eps": 20.0, "min_samples": 10},
    "leiden_spatial": {"n_neighbors": 25, "resolution": 0.5},
    "phenograph": {"k": 30, "min_cluster_size": 10},
    "none": {},
}


def _run_subcellular_domain_clustering(
    segmented_df: pd.DataFrame,
    adata: ad.AnnData,
    domain_backend: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run subcellular domain clustering within each cell.

    Returns a summary dict with domain statistics.
    """
    if domain_backend not in _SUBCELL_DOMAIN_FUNCS:
        raise ValueError(
            f"Unknown subcellular domain backend: {domain_backend}. "
            f"Available: {list(_SUBCELL_DOMAIN_FUNCS)}"
        )

    if domain_backend == "none":
        segmented_df["subcellular_domain"] = "0"
        for col in ["n_subcellular_domains", "subcellular_domain_distribution"]:
            if col in adata.obs.columns:
                del adata.obs[col]
        return {
            "subcellular_domain_backend": "none",
            "n_cells_processed": 0,
            "n_cells_with_multiple_domains": 0,
            "mean_domains_per_cell": 1.0,
            "total_noise_transcripts": 0,
        }

    cluster_func = _SUBCELL_DOMAIN_FUNCS[domain_backend]

    # Merge defaults with provided kwargs
    cluster_kwargs = dict(_SUBCELL_DOMAIN_DEFAULTS.get(domain_backend, {}))
    cluster_kwargs.update(kwargs)

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
    return {
        "subcellular_domain_backend": domain_backend,
        "n_cells_processed": n_cells,
        "n_cells_with_multiple_domains": n_cells_with_multiple,
        "fraction_multi_domain": round(n_cells_with_multiple / max(n_cells, 1), 4),
        "mean_domains_per_cell": round(
            np.mean(list(cell_domain_counts.values())) if cell_domain_counts else 1.0,
            3,
        ),
        "total_noise_transcripts": total_noise,
    }


# ── RNA localization backend ─────────────────────────────────────────


def _subcell_rna_localization(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
) -> dict[str, Any]:
    """Compute RNA localization metrics per cell.

    Metrics:
    - mean_radial_distance: mean distance from nuclear centroid
    """
    cell_col = resolve_col_strict(segmented_df.columns, COL_CELL_ID)
    x_col = resolve_col_strict(segmented_df.columns, COL_X)
    y_col = resolve_col_strict(segmented_df.columns, COL_Y)

    cell_centroids = pd.DataFrame(
        adata.obsm["spatial"],
        index=adata.obs_names,
        columns=["cx", "cy"],
    )

    per_cell: dict[str, dict[str, float]] = {}
    segmented_df = segmented_df.copy()
    segmented_df[cell_col] = segmented_df[cell_col].astype(str)
    centroids_idx = set(cell_centroids.index)

    for cell_id, group in segmented_df.groupby(cell_col, sort=False):
        if cell_id not in centroids_idx:
            continue
        cx, cy = cell_centroids.loc[cell_id]
        dists = np.sqrt((group[x_col] - cx) ** 2 + (group[y_col] - cy) ** 2)
        per_cell[str(cell_id)] = {
            "mean_radial_distance": float(dists.mean()) if len(dists) else 0.0,
            "max_radial_distance": float(dists.max()) if len(dists) else 0.0,
        }

    rna_dist = pd.Series(
        {k: v["mean_radial_distance"] for k, v in per_cell.items()},
        name="mean_rna_radial_distance",
        dtype=float,
    )
    adata.obs["mean_rna_radial_distance"] = rna_dist.reindex(adata.obs_names, fill_value=0.0).astype(float)

    summary = {
        "n_cells_analyzed": len(per_cell),
        "mean_distance_overall": float(adata.obs["mean_rna_radial_distance"].mean())
        if "mean_rna_radial_distance" in adata.obs
        else 0.0,
    }
    adata.uns["rna_localization_metrics"] = summary
    return summary


# ── SCRIN backend ────────────────────────────────────────────────────

_SCRIN_ALLOWED_KWARGS: set[str] = {
    "min_gene_number", "min_neighbor_number", "expression_level",
    "filter_threshold", "pair_keep", "intermediate_dir", "intermediate_split",
    "distribution_analysis", "r_dist", "around_count_threshold",
    "distribution_save_interval", "grid_check",
}


def _subcell_scrin(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    scrin_radius: float = 4.16,
    scrin_mode: str = "fast",
    scrin_background: str = "cooccurrence",
    scrin_detection: str = "radius",
    scrin_mpi_np: int = 1,
    scrin_timeout: int = 3600,
    **scrin_kwargs: Any,
) -> dict[str, Any]:
    """Run SCRIN co-localization network analysis.

    Exports the segmented transcript DataFrame as a temporary CSV,
    calls the ``scrin`` CLI, and stores the resulting co-localization
    network in ``adata.uns["scrin_colocalization_network"]``.
    """
    if not _SCRIN_AVAILABLE and not shutil.which("scrin"):
        return _subcell_scrin_stub(segmented_df, adata, scrin_radius=scrin_radius)

    cell_col = resolve_col_strict(segmented_df.columns, COL_CELL_ID)
    x_col = resolve_col_strict(segmented_df.columns, COL_X)
    y_col = resolve_col_strict(segmented_df.columns, COL_Y)
    gene_col = resolve_col_strict(segmented_df.columns, COL_GENE)

    scrin_df = segmented_df[[cell_col, x_col, y_col, gene_col]].copy()
    scrin_df.columns = ["cell_id", "x", "y", "gene"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_p = Path(tmpdir)
        input_csv = tmpdir_p / "transcripts.csv"
        scrin_df.to_csv(input_csv, index=False)

        output_dir = tmpdir_p / "scrin_output"
        output_dir.mkdir()

        cmd = [
            "scrin",
            "--input", str(input_csv),
            "--output", str(output_dir),
            "--r_check", str(scrin_radius),
            "--mode", scrin_mode,
            "--background", scrin_background,
            "--detection", scrin_detection,
        ]
        if scrin_mpi_np > 1:
            cmd = ["mpirun", "-np", str(scrin_mpi_np)] + cmd

        try:
            subprocess.run(cmd, check=True, timeout=scrin_timeout, capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            logger.warning("SCRIN timed out after %d seconds.", scrin_timeout)
            return {"scrin": "timeout", "n_pairs": 0}
        except subprocess.CalledProcessError as exc:
            logger.warning("SCRIN failed: %s", exc.stderr)
            return {"scrin": "failed", "n_pairs": 0}
        except FileNotFoundError:
            logger.warning("SCRIN executable not found on PATH.")
            return _subcell_scrin_stub(segmented_df, adata, scrin_radius=scrin_radius)

        n_pairs = 0
        result_csv = output_dir / "scrin_results.csv"
        if result_csv.exists():
            try:
                result_df = pd.read_csv(result_csv)
                n_pairs = len(result_df)
            except Exception:
                logger.warning("SCRIN: failed to parse output CSV.")

    scrin_meta = {
        "method": "SCRIN",
        "status": "completed",
        "n_significant_pairs": n_pairs,
        "parameters": {
            "r_check": scrin_radius,
            "mode": scrin_mode,
            "background": scrin_background,
            "detection": scrin_detection,
            "mpi_np": scrin_mpi_np,
        },
    }
    adata.uns["scrin_colocalization_network"] = scrin_meta
    logger.info("SCRIN: %d significant co-localization pairs found.", n_pairs)
    return {"scrin": "completed", "n_pairs": n_pairs}


def _subcell_scrin_stub(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    scrin_radius: float = 4.16,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Fallback stub when SCRIN is not available."""
    adata.uns["scrin_colocalization_network"] = {
        "method": "SCRIN",
        "status": "stub",
        "parameters": {"r_check": scrin_radius, "background": "cooccurrence", "mode": "fast"},
        "note": "SCRIN not installed or not on PATH.",
    }
    return {"scrin": "stub"}


# ── Main entry point ─────────────────────────────────────────────────


def run_subcellular_analysis(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    backend: str,
    domain_backend: str = "hdbscan",
    scrin_radius: float = 4.16,
    scrin_mode: str = "fast",
    scrin_background: str = "cooccurrence",
    scrin_detection: str = "radius",
    scrin_mpi_np: int = 1,
    scrin_timeout: int = 3600,
    **domain_kwargs: Any,
) -> StepResult:
    """Run subcellular analysis: optional domain clustering + analysis.

    Parameters
    ----------
    segmented_df : pd.DataFrame
        Transcript-level DataFrame.
    adata : AnnData
        Cell-level AnnData.
    backend : str
        Analysis backend ("rna_localization" or "scrin").
    domain_backend : str
        Subcellular domain clustering backend ("hdbscan", "dbscan",
        "leiden_spatial", "phenograph", or "none" to skip).
    """
    if backend not in _SUBCELLULAR_ANALYSIS_FUNCS:
        raise ValueError(
            f"Unknown subcellular analysis backend: {backend}. "
            f"Available: {list(_SUBCELLULAR_ANALYSIS_FUNCS)}"
        )

    # ── Phase 1: Subcellular domain clustering (optional) ───────────
    domain_summary: dict[str, Any] = {}
    if domain_backend != "none":
        domain_kwargs_clean = {k: v for k, v in domain_kwargs.items()
                               if k in _SUBCELL_DOMAIN_DEFAULTS.get(domain_backend, {})}
        domain_summary = _run_subcellular_domain_clustering(
            segmented_df, adata, domain_backend, **domain_kwargs_clean
        )

    # ── Phase 2: Subcellular analysis ───────────────────────────────
    func = _SUBCELLULAR_ANALYSIS_FUNCS[backend]
    if backend == "scrin":
        results = func(
            segmented_df, adata,
            scrin_radius=scrin_radius,
            scrin_mode=scrin_mode,
            scrin_background=scrin_background,
            scrin_detection=scrin_detection,
            scrin_mpi_np=scrin_mpi_np,
            scrin_timeout=scrin_timeout,
        )
    else:
        results = func(segmented_df, adata)

    # Merge summaries
    summary: dict[str, Any] = {**domain_summary, **results, "subcellular_analysis_backend": backend}

    return StepResult(
        output=(segmented_df, adata),
        summary=summary,
        backend_used=backend,
    )


# ── Register ─────────────────────────────────────────────────────────

register_backend("subcellular_analysis", "rna_localization")(_subcell_rna_localization)
register_backend("subcellular_analysis", "scrin")(_subcell_scrin)

declare_capabilities("subcellular_analysis", "rna_localization", [
    "subcellular_domains", "rna_localization",
])
declare_capabilities("subcellular_analysis", "scrin", [
    "subcellular_domains", "co_localization_network",
])

_SUBCELLULAR_ANALYSIS_FUNCS = {
    "rna_localization": lambda df, ad, **kw: _subcell_rna_localization(df, ad),
    "scrin": _subcell_scrin,
}


# ── Step runner ──────────────────────────────────────────────────────


@register_runner("subcellular_analysis")
def _run_subcellular_analysis(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.segmented_df is None or ctx.adata is None:
        raise ValueError("No segmented data or adata before subcellular analysis")

    domain_backend = params.get("subcellular_domain_backend", params.get("domain_backend", "hdbscan"))
    scrin_radius = params.get("scrin_radius", 4.16)
    scrin_mode = params.get("scrin_mode", "fast")
    scrin_background = params.get("scrin_background", "cooccurrence")
    scrin_detection = params.get("scrin_detection", "radius")
    scrin_mpi_np = params.get("scrin_mpi_np", 1)
    scrin_timeout = params.get("scrin_timeout", 3600)

    # Extract domain-specific kwargs
    domain_kwargs = {k: v for k, v in params.items()
                     if k in ("min_cluster_size", "min_samples", "eps",
                              "n_neighbors", "resolution", "k")}

    result = run_subcellular_analysis(
        ctx.segmented_df, ctx.adata, backend,
        domain_backend=domain_backend,
        scrin_radius=scrin_radius,
        scrin_mode=scrin_mode,
        scrin_background=scrin_background,
        scrin_detection=scrin_detection,
        scrin_mpi_np=scrin_mpi_np,
        scrin_timeout=scrin_timeout,
        **domain_kwargs,
    )
    output_tuple = result.output
    if isinstance(output_tuple, tuple) and len(output_tuple) == 2:
        ctx.segmented_df, ctx.adata = output_tuple
    else:
        ctx.adata = result.output
    return result
