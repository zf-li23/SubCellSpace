from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import scanpy as sc
import squidpy as sq
from sklearn.cluster import KMeans

from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

# ── Backend implementations ────────────────────────────────────────────────


def _ensure_spatial_neighbors(adata: sc.AnnData) -> None:
    """Compute spatial neighbors if not already present."""
    if "spatial_connectivities" not in adata.obsp:
        sq.gr.spatial_neighbors(adata, spatial_key="spatial", coord_type="generic")


def _domain_spatial_leiden(adata: sc.AnnData, domain_resolution: float, n_spatial_domains: int | None = None) -> str:  # noqa: ARG001
    _ensure_spatial_neighbors(adata)

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
        pass

    try:
        sc.tl.leiden(
            adata,
            adjacency=adata.obsp["spatial_connectivities"],
            resolution=domain_resolution,
            key_added="spatial_domain",
        )
        return "spatial_leiden_default"
    except Exception:
        pass

    # Ultimate fallback: use KMeans-based spatial domain assignment
    n_cells = adata.n_obs
    n_domains = max(2, min(8, int(np.sqrt(n_cells) // 2 + 2)))
    coords = adata.obsm.get("spatial")
    if coords is None:
        coords = np.zeros((n_cells, 2))
    labels = KMeans(n_clusters=n_domains, n_init="auto", random_state=0).fit_predict(coords)
    adata.obs["spatial_domain"] = labels.astype(str)
    return "spatial_leiden_fallback_kmeans"


def _domain_spatial_kmeans(
    adata: sc.AnnData,
    _domain_resolution: float = 1.0,
    n_spatial_domains: int | None = None,  # noqa: ARG001
) -> str:
    if "spatial" not in adata.obsm:
        raise ValueError("`spatial` not found in adata.obsm.")

    coords = adata.obsm["spatial"]
    if n_spatial_domains is None:
        n_spatial_domains = max(2, min(12, int(np.sqrt(max(adata.n_obs, 2)) // 2 + 2)))

    n_spatial_domains = max(2, min(int(n_spatial_domains), adata.n_obs))
    labels = KMeans(n_clusters=n_spatial_domains, n_init="auto", random_state=0).fit_predict(coords)
    adata.obs["spatial_domain"] = labels.astype(str)
    return "spatial_kmeans"


# Register backends
register_backend("spatial_domain", "spatial_leiden")(_domain_spatial_leiden)
register_backend("spatial_domain", "spatial_kmeans")(_domain_spatial_kmeans)

# Dispatch table
_SPATIAL_DOMAIN_FUNCS = {
    "spatial_leiden": _domain_spatial_leiden,
    "spatial_kmeans": _domain_spatial_kmeans,
}


# ── Main entry point ──────────────────────────────────────────────────────


def run_spatial_domain_identification(
    adata: sc.AnnData,
    backend: str,
    domain_resolution: float,
    n_spatial_domains: int | None,
) -> StepResult:
    if backend not in _SPATIAL_DOMAIN_FUNCS:
        raise ValueError(f"Unknown spatial domain backend: {backend}. Available: {list(_SPATIAL_DOMAIN_FUNCS)}")

    backend_used = _SPATIAL_DOMAIN_FUNCS[backend](adata, domain_resolution, n_spatial_domains)

    distribution = adata.obs["spatial_domain"].astype(str).value_counts().to_dict()
    summary = {
        "spatial_domain_backend_requested": backend,
        "spatial_domain_backend_used": backend_used,
        "domain_resolution": float(domain_resolution),
        "n_spatial_domains_requested": int(n_spatial_domains) if n_spatial_domains is not None else None,
        "n_spatial_domains": int(adata.obs["spatial_domain"].nunique()),
        "spatial_domain_distribution": {str(k): int(v) for k, v in distribution.items()},
    }
    return StepResult(output=adata, summary=summary, backend_used=backend_used)


# ── Step runner (registered for pipeline engine) ──────────────────────────


@register_runner("spatial_domain")
def _run_spatial_domain(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.adata is None:
        raise ValueError("No AnnData before spatial_domain step")
    resolution = params.get("domain_resolution", 1.0)
    n_domains = params.get("n_spatial_domains")
    result = run_spatial_domain_identification(ctx.adata, backend, resolution, n_domains)
    ctx.adata = result.output
    return result
