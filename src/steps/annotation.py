from __future__ import annotations

from typing import TYPE_CHECKING, Any

import scanpy as sc

from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

# ── Backend implementations ────────────────────────────────────────────────


def _anno_cluster_label(adata: sc.AnnData) -> str:
    if "cluster" not in adata.obs:
        raise ValueError("`cluster` not found in adata.obs. Run clustering before annotation.")
    adata.obs["cell_type"] = adata.obs["cluster"].astype(str).map(lambda x: f"Cluster_{x}")
    return "cluster_label"


def _anno_rank_marker(adata: sc.AnnData) -> str:
    if "cluster" not in adata.obs:
        raise ValueError("`cluster` not found in adata.obs. Run clustering before annotation.")

    rank_kwargs = {
        "groupby": "cluster",
        "method": "t-test",
        "use_raw": False,
    }
    if "lognorm" in adata.layers:
        rank_kwargs["layer"] = "lognorm"

    sc.tl.rank_genes_groups(adata, **rank_kwargs)
    markers = adata.uns["rank_genes_groups"]["names"]

    cluster_to_label: dict[str, str] = {}
    for cluster in adata.obs["cluster"].astype(str).unique():
        top_gene = str(markers[cluster][0]) if cluster in markers.dtype.names else "UnknownMarker"
        cluster_to_label[cluster] = f"CT_{top_gene}"

    adata.obs["cell_type"] = adata.obs["cluster"].astype(str).map(cluster_to_label).fillna("CT_Unknown")
    return "rank_marker"


# Register backends
register_backend("annotation", "cluster_label")(_anno_cluster_label)
register_backend("annotation", "rank_marker")(_anno_rank_marker)

# Dispatch table
_ANNOTATION_FUNCS = {
    "cluster_label": _anno_cluster_label,
    "rank_marker": _anno_rank_marker,
}


# ── Main entry point ──────────────────────────────────────────────────────


def run_cell_type_annotation(
    adata: sc.AnnData,
    backend: str,
) -> StepResult:
    if backend not in _ANNOTATION_FUNCS:
        raise ValueError(f"Unknown annotation backend: {backend}. Available: {list(_ANNOTATION_FUNCS)}")

    backend_used = _ANNOTATION_FUNCS[backend](adata)

    distribution = adata.obs["cell_type"].astype(str).value_counts().to_dict()
    summary = {
        "annotation_backend_requested": backend,
        "annotation_backend_used": backend_used,
        "n_cell_types": int(adata.obs["cell_type"].nunique()),
        "cell_type_distribution": {str(k): int(v) for k, v in distribution.items()},
    }
    return StepResult(output=adata, summary=summary, backend_used=backend_used)


# ── Step runner (registered for pipeline engine) ──────────────────────────


@register_runner("annotation")
def _run_annotation(
    ctx: ExecutionContext,
    backend: str,
    _params: dict[str, Any],  # noqa: ARG001
) -> StepResult:
    if ctx.adata is None:
        raise ValueError("No AnnData before annotation step")
    if "cluster" not in ctx.adata.obs or ctx.adata.n_obs == 0:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Skipping annotation step — no 'cluster' column or empty adata.")
        result = StepResult(
            output=ctx.adata,
            summary={"annotation_backend": backend, "skipped": True},
            backend_used=backend,
        )
    else:
        result = run_cell_type_annotation(ctx.adata, backend=backend)
    ctx.adata = result.output
    return result
