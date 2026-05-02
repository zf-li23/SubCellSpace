from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc

from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)

# ── Backend availability flags ─────────────────────────────────────────────

_CELLTYPIST_AVAILABLE: bool = False

try:
    import celltypist  # noqa: F401
    _CELLTYPIST_AVAILABLE = True
except ImportError:
    pass


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


def _anno_celltypist(adata: sc.AnnData, model_name: str = "Immune_All_Low.pkl") -> str:
    """CellTypist: automated cell-type annotation using scRNA-seq reference models.

    Uses CellTypist to predict cell types based on pre-trained reference models.
    The ``model_name`` parameter specifies which CellTypist model to download
    and use (e.g. "Immune_All_Low.pkl", "Adult_Human_Brain.pkl").

    Parameters
    ----------
    adata : AnnData
        Preprocessed AnnData (normalised, log1p-transformed) with cluster labels.
    model_name : str
        Name of the CellTypist model to use.  Will be downloaded if not cached.

    Returns
    -------
    str
        Backend identifier ``"celltypist"``.
    """
    try:
        import celltypist
        from celltypist import models
    except ImportError as exc:
        raise ImportError(
            "CellTypist backend requires 'celltypist' to be installed. "
            "Run: pip install celltypist"
        ) from exc

    # Ensure the model is downloaded
    try:
        model = models.Model.load(model=model_name)
    except Exception:
        logger.info("Downloading CellTypist model '%s' ...", model_name)
        celltypist.models.download_models(model=model_name)
        model = models.Model.load(model=model_name)

    # CellTypist expects log1p-normalized expression (to 10k counts/cell).
    # The adata after analysis has been scaled (max_value=10), so we
    # restore the lognorm layer if available, or re-normalize from raw.
    adata_for_ct = adata.copy()
    if "lognorm" in adata.layers:
        adata_for_ct.X = adata.layers["lognorm"].copy()
    elif adata.raw is not None:
        adata_for_ct.X = adata.raw.X.copy()
        sc.pp.normalize_total(adata_for_ct, target_sum=1e4)
        sc.pp.log1p(adata_for_ct)
    else:
        # Last resort: assume adata.X is counts (unlikely but try)
        sc.pp.normalize_total(adata_for_ct, target_sum=1e4)
        sc.pp.log1p(adata_for_ct)

    # Run celltypist annotation
    prediction = celltypist.annotate(
        adata_for_ct,
        model=model,
        majority_voting=True,
        mode="best match",
        p_thres=0.5,
    )

    # Merge predicted labels into adata.obs
    pred_labels = prediction.predicted_labels
    adata.obs["cell_type"] = pred_labels["majority_voting"].values.astype(str)
    # 'score' column only present w/o majority_voting;
    # with majority_voting=True, no 'conf_score' column exists in pred_labels.
    # Use the probability_matrix to compute per-cell max confidence.
    if "score" in pred_labels.columns:
        adata.obs["celltypist_score"] = pred_labels["score"].values
        adata.obs["celltypist_confidence"] = pred_labels["score"].values
    elif "conf_score" in pred_labels.columns:
        adata.obs["celltypist_score"] = pred_labels["conf_score"].values
        adata.obs["celltypist_confidence"] = pred_labels["conf_score"].values
    else:
        # majority_voting=True: columns are ['predicted_labels', 'over_clustering', 'majority_voting']
        max_probs = prediction.probability_matrix.max(axis=1)
        adata.obs["celltypist_score"] = max_probs.values
        adata.obs["celltypist_confidence"] = max_probs.values

    return "celltypist"


# Register backends
register_backend("annotation", "cluster_label")(_anno_cluster_label)
register_backend("annotation", "rank_marker")(_anno_rank_marker)
register_backend("annotation", "celltypist")(_anno_celltypist)

# Dispatch table
_ANNOTATION_FUNCS = {
    "cluster_label": _anno_cluster_label,
    "rank_marker": _anno_rank_marker,
    "celltypist": _anno_celltypist,
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
