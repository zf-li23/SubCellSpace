"""Phase 6: Spatial Analysis step.

Provides backends for:
- SVG (spatially variable genes)  — squidpy
- neighbourhood enrichment          — squidpy
- cell co-occurrence                — squidpy
- tree inference + pseudotime       — scFates

Each backend declares its capabilities so the frontend can render only
the analyses that the chosen backend actually supports.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import scanpy as sc
import squidpy as sq

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


# ── scFates backend ─────────────────────────────────────────────────


def _spatial_scfates(
    adata: sc.AnnData,
    cluster_key: str = "cluster",
) -> dict[str, Any]:
    """Run scFates tree inference and pseudotime analysis.

    Builds a minimum-spanning-tree trajectory on the UMAP embedding,
    roots it at the cell with highest total counts, and computes
    pseudotime ordering.

    Results stored in:
    - ``adata.uns["scfates_tree"]`` — tree topology info
    - ``adata.obs["pseudotime"]``   — pseudotime per cell
    """
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
        # Ensure UMAP is available for tree inference
        if "X_umap" not in adata.obsm:
            logger.warning("scFates: no UMAP embedding found, computing it now.")
            sc.tl.umap(adata)

        # Tree fitting on UMAP space (scFates stores result in adata.uns['ppt'])
        scf.tl.tree(adata, basis="umap")
        n_milestones = (
            len(adata.uns.get("ppt", {}).get("F", []))
            if "ppt" in adata.uns
            else 0
        )
        results["tree_inference"] = {
            "n_milestones": n_milestones,
        }
    except Exception as exc:
        logger.warning("scFates tree inference failed: %s", exc)
        results["tree_inference"] = None

    # ── 2. Root + Pseudotime ────────────────────────────────────────
    try:
        if "ppt" in adata.uns and "X_R" in adata.obsm:
            # scFates root() expects either an int (tip index) or a str (obs column).
            graph_tips = adata.uns.get("graph", {}).get("tips", [])
            if len(graph_tips) > 0:
                root_id: int = int(graph_tips[0])
                scf.tl.root(adata, root=root_id)
                scf.tl.pseudotime(adata)

                # scFates stores pseudotime in adata.obs['t']
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

    # Store in adata.uns
    adata.uns["scfates_results"] = results

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

    if backend == "scfates":
        results = _SPATIAL_ANALYSIS_FUNCS[backend](adata, cluster_key=cluster_key)
    else:
        results = _SPATIAL_ANALYSIS_FUNCS[backend](adata, cluster_key=cluster_key, n_top_svg=n_top_svg)

    # Build summary from available results
    summary: dict[str, Any] = {"spatial_analysis_backend": backend}
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

    result = run_spatial_analysis(ctx.adata, backend, cluster_key=cluster_key, n_top_svg=n_top_svg)
    ctx.adata = result.output
    return result
