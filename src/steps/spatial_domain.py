from __future__ import annotations

import numpy as np
import scanpy as sc
from sklearn.cluster import KMeans

AVAILABLE_SPATIAL_DOMAIN_BACKENDS = ("spatial_leiden", "spatial_kmeans")


def _spatial_leiden(adata: sc.AnnData, domain_resolution: float) -> str:
    if "spatial_connectivities" not in adata.obsp:
        raise ValueError("`spatial_connectivities` not found. Run spatial neighbor construction first.")

    try:
        sc.tl.leiden(
            adata,
            adjacency=adata.obsp["spatial_connectivities"],
            resolution=domain_resolution,
            key_added="spatial_domain",
            flavor="igraph",
            directed=False,
            n_iterations=2,
        )
        return "spatial_leiden_igraph"
    except Exception:
        sc.tl.leiden(
            adata,
            adjacency=adata.obsp["spatial_connectivities"],
            resolution=domain_resolution,
            key_added="spatial_domain",
        )
        return "spatial_leiden_legacy"


def _spatial_kmeans(adata: sc.AnnData, n_spatial_domains: int | None) -> str:
    if "spatial" not in adata.obsm:
        raise ValueError("`spatial` not found in adata.obsm.")

    coords = adata.obsm["spatial"]
    if n_spatial_domains is None:
        n_spatial_domains = max(2, min(12, int(np.sqrt(max(adata.n_obs, 2)) // 2 + 2)))

    n_spatial_domains = max(2, min(int(n_spatial_domains), adata.n_obs))
    labels = KMeans(n_clusters=n_spatial_domains, n_init="auto", random_state=0).fit_predict(coords)
    adata.obs["spatial_domain"] = labels.astype(str)
    return "spatial_kmeans"


def run_spatial_domain_identification(
    adata: sc.AnnData,
    backend: str,
    domain_resolution: float,
    n_spatial_domains: int | None,
) -> tuple[sc.AnnData, dict[str, int | float | str | dict[str, int]]]:
    if backend not in AVAILABLE_SPATIAL_DOMAIN_BACKENDS:
        raise ValueError(f"Unknown spatial domain backend: {backend}")

    if backend == "spatial_leiden":
        backend_used = _spatial_leiden(adata, domain_resolution=domain_resolution)
    else:
        backend_used = _spatial_kmeans(adata, n_spatial_domains=n_spatial_domains)

    distribution = adata.obs["spatial_domain"].astype(str).value_counts().to_dict()
    summary = {
        "spatial_domain_backend_requested": backend,
        "spatial_domain_backend_used": backend_used,
        "domain_resolution": float(domain_resolution),
        "n_spatial_domains_requested": int(n_spatial_domains) if n_spatial_domains is not None else None,
        "n_spatial_domains": int(adata.obs["spatial_domain"].nunique()),
        "spatial_domain_distribution": {str(k): int(v) for k, v in distribution.items()},
    }
    return adata, summary
