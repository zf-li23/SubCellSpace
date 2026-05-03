"""Phase 6: Spatial Analysis step.

Provides backends for:
- SVG (spatially variable genes)  — squidpy
- neighbourhood enrichment          — squidpy
- cell co-occurrence                — squidpy
- spatial domains                   — (delegates to spatial_domain step)

Each backend declares its capabilities so the frontend can render only
the analyses that the chosen backend actually supports.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import scanpy as sc
import squidpy as sq

from ..models import StepResult
from ..registry import declare_capabilities, register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)

# ── Squidpy backend ──────────────────────────────────────────────────


def _spatial_squidpy(
    adata: sc.AnnData,
    n_top_svg: int = 100,
    cluster_key: str = "cluster",
) -> dict[str, Any]:
    """Run squidpy-based spatial analyses: SVG, neighborhood, co-occurrence.

    Returns a dict of results stored in ``adata.uns``:
    - ``squidpy_svg_results``
    - ``squidpy_neighborhood_enrichment``
    - ``squidpy_co_occurrence``
    """
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
                    "clusters": adata.obs[cluster_key].cat.categories.tolist()
                    if hasattr(adata.obs[cluster_key], "cat")
                    else sorted(adata.obs[cluster_key].unique().tolist()),
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


# ── Main entry point ─────────────────────────────────────────────────


def run_spatial_analysis(
    adata: sc.AnnData,
    backend: str,
    cluster_key: str = "cluster",
    n_top_svg: int = 100,
) -> StepResult:
    if backend not in _SPATIAL_ANALYSIS_FUNCS:
        raise ValueError(f"Unknown spatial analysis backend: {backend}. Available: {list(_SPATIAL_ANALYSIS_FUNCS)}")

    results = _SPATIAL_ANALYSIS_FUNCS[backend](adata, cluster_key=cluster_key, n_top_svg=n_top_svg)

    # Build summary from available results
    summary: dict[str, Any] = {"spatial_analysis_backend": backend}
    for cap_key, result_key in [
        ("svg", "svg_results"),
        ("neighborhood", "neighborhood_enrichment"),
        ("co_occurrence", "co_occurrence"),
    ]:
        val = results.get(result_key)
        summary[cap_key] = "success" if val is not None else "unavailable"

    return StepResult(output=adata, summary=summary, backend_used=backend)


# ── Register ─────────────────────────────────────────────────────────

register_backend("spatial_analysis", "squidpy")(_spatial_squidpy)

declare_capabilities("spatial_analysis", "squidpy", ["svg", "neighborhood", "co_occurrence"])

_SPATIAL_ANALYSIS_FUNCS = {
    "squidpy": _spatial_squidpy,
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

    result = run_spatial_analysis(ctx.adata, backend, cluster_key=cluster_key, n_top_svg=n_top_svg)
    ctx.adata = result.output
    return result
