"""Spatial Analysis step.

Provides backends for:
- Spatial domain identification (spatial_leiden, spatial_kmeans)
- SVG (spatially variable genes) — squidpy
- neighbourhood enrichment — squidpy
- cell co-occurrence — squidpy
- tree inference + pseudotime — scFates

Domain identification runs as an optional pre-processing step inside the
runner, controlled by the ``domain_backend`` parameter.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import scanpy as sc
import squidpy as sq
from sklearn.cluster import KMeans

from ..models import StepResult
from ..registry import declare_capabilities, register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)

# ── Backend availability flags ───────────────────────────────────────

_SCFATES_AVAILABLE: bool = False

try:
    import scFates  # noqa: F401

    _SCFATES_AVAILABLE = True
except ImportError:
    pass


# ── Domain identification helpers ────────────────────────────────────


def _ensure_spatial_neighbors(adata: sc.AnnData) -> None:
    """Compute spatial neighbors if not already present."""
    if "spatial_connectivities" not in adata.obsp:
        sq.gr.spatial_neighbors(adata, spatial_key="spatial", coord_type="generic")


def _run_domain_identification(
    adata: sc.AnnData,
    domain_backend: str,
    domain_resolution: float,
    n_spatial_domains: int | None,
) -> str:
    """Run spatial domain identification on *adata*.

    Returns the actual backend used (may differ from requested due to
    fallback).
    """
    _DOMAIN_FUNCS = {
        "spatial_leiden": _domain_spatial_leiden,
        "spatial_kmeans": _domain_spatial_kmeans,
        "none": lambda a, r, n: "none",
    }
    if domain_backend not in _DOMAIN_FUNCS:
        raise ValueError(
            f"Unknown domain backend: {domain_backend}. "
            f"Available: {list(_DOMAIN_FUNCS)}"
        )
    return _DOMAIN_FUNCS[domain_backend](adata, domain_resolution, n_spatial_domains)


def _domain_spatial_leiden(
    adata: sc.AnnData,
    domain_resolution: float,
    n_spatial_domains: int | None = None,  # noqa: ARG001
) -> str:
    """Spatial Leiden clustering on spatial neighbor graph.

    Tries three strategies in order:
    1. Leiden with igraph flavor
    2. Leiden with default flavor
    3. KMeans fallback on spatial coordinates
    """
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
    n_spatial_domains: int | None = None,
) -> str:
    """Spatial domain identification via KMeans on spatial coordinates."""
    if "spatial" not in adata.obsm:
        raise ValueError("`spatial` not found in adata.obsm.")

    coords = adata.obsm["spatial"]
    if n_spatial_domains is None:
        n_spatial_domains = max(2, min(12, int(np.sqrt(max(adata.n_obs, 2)) // 2 + 2)))

    n_spatial_domains = max(2, min(int(n_spatial_domains), adata.n_obs))
    labels = KMeans(n_clusters=n_spatial_domains, n_init="auto", random_state=0).fit_predict(coords)
    adata.obs["spatial_domain"] = labels.astype(str)
    return "spatial_kmeans"


# ── Squidpy backend ──────────────────────────────────────────────────


def _spatial_squidpy(
    adata: sc.AnnData,
    n_top_svg: int = 100,
    cluster_key: str = "cluster",
) -> dict[str, Any]:
    """Run squidpy-based spatial analyses: SVG, neighborhood, co-occurrence."""
    results: dict[str, Any] = {}

    # ── 1. Spatially Variable Genes ─────────────────────────────────
    try:
        sq.gr.spatial_neighbors(adata, spatial_key="spatial", coord_type="generic")
        sq.gr.spatial_autocorr(
            adata,
            mode="moran",
            n_perms=100,
            n_jobs=-1,
        )
        if "moranI" in adata.uns:
            moran_df = adata.uns["moranI"].copy()
            top_svg = moran_df.sort_values("I", ascending=False).head(n_top_svg)
            results["svg_results"] = {
                "top_genes": top_svg.index.tolist(),
                "moran_I": top_svg["I"].to_dict(),
                "pval_norm": top_svg["pval_norm"].to_dict() if "pval_norm" in top_svg.columns else {},
                "n_tested": len(moran_df),
            }
    except Exception as exc:
        logger.warning("squidpy SVG failed: %s", exc)
        results["svg_results"] = None

    # ── 2. Neighborhood Enrichment ───────────────────────────────────
    try:
        if cluster_key in adata.obs:
            sq.gr.nhood_enrichment(adata, cluster_key=cluster_key)
            if "cluster_nhood_enrichment" in adata.uns:
                enrich = adata.uns["cluster_nhood_enrichment"]
                results["neighborhood_enrichment"] = {
                    "z_scores": enrich.get("zscore", {}),
                    "pvalues": enrich.get("pvalue", {}),
                }
            else:
                results["neighborhood_enrichment"] = None
        else:
            results["neighborhood_enrichment"] = None
    except Exception as exc:
        logger.warning("squidpy neighborhood enrichment failed: %s", exc)
        results["neighborhood_enrichment"] = None

    # ── 3. Cell Co-occurrence ───────────────────────────────────────
    try:
        if cluster_key in adata.obs:
            sq.gr.co_occurrence(adata, cluster_key=cluster_key)
            if "co_occurrence" in adata.uns:
                cooc = adata.uns["co_occurrence"]
                results["co_occurrence"] = {
                    "clusters": (
                        adata.obs[cluster_key].cat.categories.tolist()
                        if hasattr(adata.obs[cluster_key], "cat")
                        else sorted(adata.obs[cluster_key].unique().tolist())
                    ),
                    "occ": cooc.get("occ", {}),
                    "interval": cooc.get("interval", []),
                }
            else:
                results["co_occurrence"] = None
        else:
            results["co_occurrence"] = None
    except Exception as exc:
        logger.warning("squidpy co-occurrence failed: %s", exc)
        results["co_occurrence"] = None

    # Store in adata.uns
    adata.uns["squidpy_svg_results"] = results.get("svg_results")
    adata.uns["squidpy_neighborhood_enrichment"] = results.get("neighborhood_enrichment")
    adata.uns["squidpy_co_occurrence"] = results.get("co_occurrence")

    return results


# ── scFates backend ─────────────────────────────────────────────────


def _spatial_scfates(
    adata: sc.AnnData,
    cluster_key: str = "cluster",
) -> dict[str, Any]:
    """Run scFates tree inference and pseudotime analysis."""
    try:
        import scFates as scf
    except ImportError as exc:
        raise ImportError(
            "scFates backend requires 'scFates' to be installed. "
            "Run: pip install -e tools/scFates/"
        ) from exc

    results: dict[str, Any] = {}

    # ── 1. Tree inference ───────────────────────────────────────────
    try:
        if "X_umap" not in adata.obsm:
            logger.warning("scFates: no UMAP embedding found, computing it now.")
            sc.tl.umap(adata)

        scf.tl.tree(adata, basis="umap")
        n_milestones = (
            len(adata.uns.get("ppt", {}).get("F", []))
            if "ppt" in adata.uns
            else 0
        )
        results["tree_inference"] = {"n_milestones": n_milestones}
    except Exception as exc:
        logger.warning("scFates tree inference failed: %s", exc)
        results["tree_inference"] = None

    # ── 2. Root + Pseudotime ────────────────────────────────────────
    try:
        if "ppt" in adata.uns and "X_R" in adata.obsm:
            graph_tips = adata.uns.get("graph", {}).get("tips", [])
            if len(graph_tips) > 0:
                root_id: int = int(graph_tips[0])
                scf.tl.root(adata, root=root_id)
                scf.tl.pseudotime(adata)

                pt_key = "t" if "t" in adata.obs else "pseudotime"
                if pt_key in adata.obs:
                    pt = adata.obs[pt_key]
                    results["pseudotime"] = {
                        "min": float(pt.min()),
                        "max": float(pt.max()),
                        "root_tip": root_id,
                    }
                else:
                    results["pseudotime"] = None
            else:
                results["pseudotime"] = None
        else:
            results["pseudotime"] = None
    except Exception as exc:
        logger.warning("scFates pseudotime failed (non-critical): %s", exc)
        results["pseudotime"] = None

    adata.uns["scfates_results"] = results
    return results


# ── Main entry point ─────────────────────────────────────────────────


def run_spatial_analysis(
    adata: sc.AnnData,
    backend: str,
    cluster_key: str = "cluster",
    n_top_svg: int = 100,
    domain_backend: str = "spatial_leiden",
    domain_resolution: float = 1.0,
    n_spatial_domains: int | None = None,
) -> StepResult:
    """Run spatial analysis: optional domain identification + analysis.

    Parameters
    ----------
    adata : AnnData
    backend : str
        Analysis backend ("squidpy" or "scfates").
    domain_backend : str
        Domain identification backend ("spatial_leiden", "spatial_kmeans",
        or "none" to skip).
    """
    if backend not in _SPATIAL_ANALYSIS_FUNCS:
        raise ValueError(
            f"Unknown spatial analysis backend: {backend}. "
            f"Available: {list(_SPATIAL_ANALYSIS_FUNCS)}"
        )

    # ── Phase 1: Spatial domain identification (optional) ───────────
    domain_used = "none"
    if domain_backend != "none":
        domain_used = _run_domain_identification(
            adata, domain_backend, domain_resolution, n_spatial_domains
        )

    # ── Phase 2: Spatial analysis ───────────────────────────────────
    if backend == "scfates":
        results = _SPATIAL_ANALYSIS_FUNCS[backend](adata, cluster_key=cluster_key)
    else:
        results = _SPATIAL_ANALYSIS_FUNCS[backend](adata, cluster_key=cluster_key, n_top_svg=n_top_svg)

    # Build summary
    summary: dict[str, Any] = {
        "spatial_analysis_backend": backend,
        "domain_backend_requested": domain_backend,
        "domain_backend_used": domain_used,
    }

    # Domain-level summary
    if domain_used != "none" and "spatial_domain" in adata.obs:
        distribution = adata.obs["spatial_domain"].astype(str).value_counts().to_dict()
        summary.update({
            "n_spatial_domains": int(adata.obs["spatial_domain"].nunique()),
            "spatial_domain_distribution": {str(k): int(v) for k, v in distribution.items()},
        })

    # Analysis-level summary
    if backend == "squidpy":
        for cap_key, result_key in [
            ("svg", "svg_results"),
            ("neighborhood", "neighborhood_enrichment"),
            ("co_occurrence", "co_occurrence"),
        ]:
            val = results.get(result_key)
            summary[cap_key] = "success" if val is not None else "unavailable"
    elif backend == "scfates":
        for cap_key, cap_label in [
            ("tree_inference", "tree_inference"),
            ("pseudotime", "pseudotime"),
        ]:
            val = results.get(cap_label)
            summary[cap_key] = "success" if val is not None else "unavailable"

    return StepResult(output=adata, summary=summary, backend_used=backend)


# ── Register ─────────────────────────────────────────────────────────

register_backend("spatial_analysis", "squidpy")(_spatial_squidpy)
register_backend("spatial_analysis", "scfates")(_spatial_scfates)

declare_capabilities("spatial_analysis", "squidpy", ["svg", "neighborhood", "co_occurrence"])
declare_capabilities("spatial_analysis", "scfates", ["tree_inference", "pseudotime"])

_SPATIAL_ANALYSIS_FUNCS = {
    "squidpy": _spatial_squidpy,
    "scfates": _spatial_scfates,
}


# ── Step runner ──────────────────────────────────────────────────────


@register_runner("spatial_analysis")
def _run_spatial_analysis(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.adata is None:
        raise ValueError("No AnnData before spatial_analysis step")

    cluster_key = params.get("cluster_key", "cluster")
    n_top_svg = params.get("n_top_svg", 100)
    domain_backend = params.get("domain_backend", "spatial_leiden")
    domain_resolution = params.get("domain_resolution", 1.0)
    n_spatial_domains = params.get("n_spatial_domains")

    result = run_spatial_analysis(
        ctx.adata,
        backend,
        cluster_key=cluster_key,
        n_top_svg=n_top_svg,
        domain_backend=domain_backend,
        domain_resolution=domain_resolution,
        n_spatial_domains=n_spatial_domains,
    )
    ctx.adata = result.output
    return result
