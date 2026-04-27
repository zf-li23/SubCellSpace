from __future__ import annotations

import scanpy as sc
import squidpy as sq
from sklearn.cluster import KMeans

AVAILABLE_CLUSTERING_BACKENDS = ("leiden", "kmeans")


def _cluster(adata: sc.AnnData, backend: str, resolution: float) -> str:
    if backend not in AVAILABLE_CLUSTERING_BACKENDS:
        raise ValueError(f"Unknown clustering backend: {backend}")

    if backend == "kmeans":
        n_clusters = min(8, max(2, adata.n_obs))
        labels = KMeans(n_clusters=n_clusters, n_init="auto", random_state=0).fit_predict(adata.obsm["X_pca"])
        adata.obs["cluster"] = labels.astype(str)
        return "kmeans"

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


def run_expression_and_spatial_analysis(
    adata: sc.AnnData,
    min_transcripts: int,
    min_genes: int,
    clustering_backend: str,
    leiden_resolution: float,
) -> tuple[sc.AnnData, dict[str, int | float | str]]:
    # Validate backend early, before any expensive computation
    if clustering_backend not in AVAILABLE_CLUSTERING_BACKENDS:
        raise ValueError(f"Unknown clustering backend: {clustering_backend}")

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
        return adata, summary

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    adata.layers["lognorm"] = adata.X.copy()
    try:
        sc.pp.highly_variable_genes(adata, flavor="cell_ranger", n_top_genes=min(2000, adata.n_vars))
        if "highly_variable" in adata.var and adata.var["highly_variable"].any():
            adata = adata[:, adata.var["highly_variable"]].copy()
    except (IndexError, ValueError):
        # Very small datasets may cause scanpy's hvg to fail (all-NaN dispersions etc.)
        # Keep all genes in that case.
        pass

    n_comps = min(50, adata.n_obs - 1, adata.n_vars - 1)
    n_comps = max(2, n_comps)
    sc.pp.scale(adata, max_value=10)
    sc.tl.pca(adata, n_comps=n_comps, svd_solver="randomized")
    sc.pp.neighbors(adata, n_neighbors=min(15, max(2, adata.n_obs - 1)), n_pcs=min(30, n_comps))
    cluster_backend_used = _cluster(adata, backend=clustering_backend, resolution=leiden_resolution)
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
    return adata, summary
