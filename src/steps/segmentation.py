from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

# ── Backend implementations ────────────────────────────────────────────────


def _seg_provided_cells(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["cell"].notna() & (df["cell"].astype(str) != "")].copy()


def _seg_fov_cell_id(df: pd.DataFrame) -> pd.DataFrame:
    assigned = df.copy()
    assigned["cell"] = assigned["fov"].astype(str) + "_" + assigned["cell_ID"].astype(str)
    return assigned


# Register backends
register_backend("segmentation", "provided_cells")(_seg_provided_cells)
register_backend("segmentation", "fov_cell_id")(_seg_fov_cell_id)

# Dispatch table
_SEGMENTATION_FUNCS = {
    "provided_cells": _seg_provided_cells,
    "fov_cell_id": _seg_fov_cell_id,
}


# ── Main entry point ──────────────────────────────────────────────────────


def assign_cells(df: pd.DataFrame, backend: str) -> StepResult:
    if backend not in _SEGMENTATION_FUNCS:
        raise ValueError(f"Unknown segmentation backend: {backend}. Available: {list(_SEGMENTATION_FUNCS)}")

    assigned = _SEGMENTATION_FUNCS[backend](df)
    summary = {
        "segmentation_backend": backend,
        "n_transcripts_assigned": int(len(assigned)),
        "n_cells_assigned": int(assigned["cell"].nunique()),
    }
    return StepResult(output=assigned, summary=summary, backend_used=backend)


# ── Step runner (registered for pipeline engine) ──────────────────────────


@register_runner("segmentation")
def _run_segmentation(
    ctx: ExecutionContext,
    backend: str,
    _params: dict[str, Any],  # noqa: ARG001
) -> StepResult:
    if ctx.denoised_df is None:
        raise ValueError("No denoised data before segmentation step")
    result = assign_cells(ctx.denoised_df, backend)
    ctx.segmented_df = result.output
    return result
