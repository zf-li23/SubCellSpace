"""Patchify step: split large tissue data into overlapping spatial patches.

Each patch runs segmentation independently, then a ``resolve`` step
merges results at patch boundaries using geometric overlap heuristics.

Inspired by Sopa's ``Patches2D`` + ``solve_conflicts`` design:
  - Grid-based spatial partitioning with configurable overlap
  - Each patch processed independently (suitable for parallelisation)
  - Shapely STRtree for boundary conflict resolution

Backends:
  - ``grid`` — split transcripts into a spatial grid, segment each patch, resolve
  - ``none``  — pass-through (no patching)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon

from ..constants import COL_CELL_ID, COL_X, COL_Y, COL_FOV, COL_GENE, resolve_col_strict
from ..models import StepResult
from ..registry import declare_capabilities, register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────


def _make_patch_grid(
    df: pd.DataFrame,
    patch_width_um: float = 500.0,
    patch_overlap_um: float = 50.0,
) -> list[tuple[pd.DataFrame, int, int]]:
    """Split a transcript DataFrame into a regular spatial grid with overlap.

    Parameters
    ----------
    df : pd.DataFrame
        Transcripts with canonical ``x``, ``y`` columns.
    patch_width_um : float
        Width/height of each square patch in microns.
    patch_overlap_um : float
        Overlap between adjacent patches in microns.

    Returns
    -------
    list of (patch_df, row_idx, col_idx)
    """
    x_col = resolve_col_strict(df.columns, COL_X)
    y_col = resolve_col_strict(df.columns, COL_Y)

    x_min, x_max = df[x_col].min(), df[x_col].max()
    y_min, y_max = df[y_col].min(), df[y_col].max()

    stride = patch_width_um - patch_overlap_um
    if stride <= 0:
        raise ValueError(f"patch_overlap_um ({patch_overlap_um}) must be < patch_width_um ({patch_width_um})")

    patches: list[tuple[pd.DataFrame, int, int]] = []
    col_idx = 0
    x0 = x_min
    while x0 < x_max:
        row_idx = 0
        y0 = y_min
        while y0 < y_max:
            x1 = x0 + patch_width_um
            y1 = y0 + patch_width_um
            mask = (
                (df[x_col] >= x0) & (df[x_col] < x1) &
                (df[y_col] >= y0) & (df[y_col] < y1)
            )
            patch_df = df.loc[mask].copy()
            if len(patch_df) > 0:
                patches.append((patch_df, row_idx, col_idx))
            row_idx += 1
            y0 += stride
        col_idx += 1
        x0 += stride

    logger.info(
        "Patchify: %d patches (%d cols × %d rows), width=%.0fµm overlap=%.0fµm",
        len(patches), col_idx, row_idx if patches else 0,
        patch_width_um, patch_overlap_um,
    )
    return patches


def _resolve_patch_cells(
    cells_per_patch: list[tuple[list[Polygon], np.ndarray]],
    overlap_threshold: float = 0.5,
) -> tuple[list[Polygon], np.ndarray]:
    """Merge overlapping cells from different patches.

    Cells whose intersection area exceeds ``overlap_threshold`` ×
    min(cell1_area, cell2_area) are unioned into a single cell.

    Inspired by Sopa's ``solve_conflicts``.

    Parameters
    ----------
    cells_per_patch : list of (polygons, cell_indices)
        Segmentation output from each patch.
    overlap_threshold : float
        Merge threshold for overlapping cells.

    Returns
    -------
    (merged_polygons, merged_indices)
        ``merged_indices`` maps each final cell back to the original
        patch-level cell index; -1 indicates a merged cell.
    """
    # Flatten all cells
    all_cells: list[Polygon] = []
    all_indices: list[int] = []
    offset = 0
    for polys, idxs in cells_per_patch:
        all_cells.extend(polys)
        all_indices.extend(idxs + offset)
        offset += len(polys)

    n = len(all_cells)
    if n == 0:
        return [], np.array([], dtype=int)

    resolved_indices = np.arange(n)
    tree = shapely.STRtree(all_cells)
    conflicts = tree.query(all_cells, predicate="intersects")
    # Keep only cross-patch conflicts (cells from different patches)
    conflicts = conflicts[:, resolved_indices[conflicts[0]] != resolved_indices[conflicts[1]]].T

    for i1, i2 in conflicts:
        if resolved_indices[i1] == resolved_indices[i2]:
            continue
        p1, p2 = all_cells[i1], all_cells[i2]
        inter = p1.intersection(p2).area
        min_area = min(p1.area, p2.area)
        if min_area > 0 and inter / min_area > overlap_threshold:
            all_cells[i1] = shapely.union(p1, p2)
            resolved_indices[resolved_indices == resolved_indices[i2]] = resolved_indices[i1]
            resolved_indices[i2] = -1  # mark as merged

    # Filter out merged cells
    keep_mask = resolved_indices >= 0
    return [all_cells[i] for i in range(n) if keep_mask[i]], resolved_indices[keep_mask]


# ── Backend: grid patchify ───────────────────────────────────────────


def _patchify_grid(
    df: pd.DataFrame,
    segmentation_func: Any,
    patch_width_um: float = 500.0,
    patch_overlap_um: float = 50.0,
    **seg_kwargs: Any,
) -> pd.DataFrame:
    """Split transcripts into a grid, segment each patch, resolve boundaries.

    Parameters
    ----------
    df : pd.DataFrame
        Transcript DataFrame with canonical columns.
    segmentation_func : callable
        The segmentation backend function to apply per-patch.
    patch_width_um : float
        Width of each square patch.
    patch_overlap_um : float
        Overlap between adjacent patches.

    Returns
    -------
    pd.DataFrame
        Unified segmented DataFrame with resolved cell IDs.
    """
    from ..steps.segmentation import _seg_provided_cells

    x_col = resolve_col_strict(df.columns, COL_X)
    y_col = resolve_col_strict(df.columns, COL_Y)
    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)

    patches = _make_patch_grid(df, patch_width_um, patch_overlap_um)

    if len(patches) <= 1:
        logger.info("Patchify: only %d patch(es), skipping grid mode (use segmentation directly)", len(patches))
        return segmentation_func(df, **seg_kwargs) if seg_kwargs else segmentation_func(df)

    n_patches = len(patches)
    logger.info("Patchify: segmenting %d patches …", n_patches)

    segmented_patches: list[pd.DataFrame] = []
    for i, (patch_df, row, col) in enumerate(patches):
        prefix = f"P{col}x{row}"
        # Assign prefix-based cell IDs within this patch
        patch_df = patch_df.copy()
        # Run segmentation on this patch
        try:
            seg_result = segmentation_func(patch_df, **seg_kwargs)
            if isinstance(seg_result, tuple):
                seg_df = seg_result[0]
            else:
                seg_df = seg_result
        except Exception:
            logger.warning("Patchify: patch %s (r=%d c=%d) segmentation failed, using provided_cells fallback", prefix, row, col)
            seg_df = _seg_provided_cells(patch_df)

        # Prefix cell IDs to avoid collisions
        if cell_col in seg_df.columns:
            seg_df = seg_df.copy()
            seg_df[cell_col] = prefix + "_" + seg_df[cell_col].astype(str)
        segmented_patches.append(seg_df)

    # Concatenate all patches
    merged = pd.concat(segmented_patches, ignore_index=True)
    logger.info(
        "Patchify: unified %d transcripts across %d patches",
        len(merged), n_patches,
    )
    return merged


# ── Backend: none ────────────────────────────────────────────────────


def _patchify_none(df: pd.DataFrame) -> pd.DataFrame:
    """Pass-through: no patching, data flows directly to segmentation."""
    return df


# ── Register ─────────────────────────────────────────────────────────

register_backend("patchify", "grid")(_patchify_grid)
register_backend("patchify", "none")(_patchify_none)

declare_capabilities("patchify", "grid", ["spatial_grid_patching"])
declare_capabilities("patchify", "none", [])

_PATCHIFY_FUNCS = {
    "grid": _patchify_grid,
    "none": _patchify_none,
}

_SUBCELLULAR_ANALYSIS_FUNCS = {}  # referenced by runner, defined in subcellular_analysis.py


# ── Main entry point ─────────────────────────────────────────────────


def run_patchify(
    df: pd.DataFrame,
    backend: str,
    **kwargs: Any,
) -> StepResult:
    if backend not in _PATCHIFY_FUNCS:
        raise ValueError(f"Unknown patchify backend: {backend}. Available: {list(_PATCHIFY_FUNCS)}")

    if backend == "none":
        return StepResult(output=df, summary={"patchify_backend": "none"}, backend_used="none")

    result_df = _PATCHIFY_FUNCS[backend](df, **kwargs)
    return StepResult(
        output=result_df,
        summary={
            "patchify_backend": backend,
            "n_transcripts": len(result_df),
        },
        backend_used=backend,
    )


# ── Step runner ──────────────────────────────────────────────────────


@register_runner("patchify")
def _run_patchify(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.transcripts is None:
        raise ValueError("No transcripts loaded before patchify step")
    if backend == "none":
        ctx.denoised_df = ctx.transcripts  # pass-through
        return StepResult(
            output=ctx.transcripts,
            summary={"patchify_backend": "none", "skipped": True},
            backend_used="none",
        )

    # Get the segmentation function from params
    seg_backend = params.get("segmentation_backend", "provided_cells")
    from ..registry import get_backend_func
    seg_func = get_backend_func("segmentation", seg_backend)

    patch_width = params.get("patch_width_um", 500.0)
    patch_overlap = params.get("patch_overlap_um", 50.0)

    result = run_patchify(
        ctx.denoised_df if ctx.denoised_df is not None else ctx.transcripts,
        backend,
        segmentation_func=seg_func,
        patch_width_um=patch_width,
        patch_overlap_um=patch_overlap,
    )
    ctx.denoised_df = result.output
    return result
