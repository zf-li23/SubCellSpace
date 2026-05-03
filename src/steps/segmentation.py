from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from ..constants import COL_CELL_ID, COL_FOV, COL_GENE, COL_X, COL_Y, resolve_col_strict
from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)


# ── Helper: validate required columns ───────────────────────────────


def _validate_columns(df: pd.DataFrame, required: set[str], backend: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Segmentation backend '{backend}' requires columns: {sorted(required)}, "
            f"but missing: {sorted(missing)}"
        )


# ── Backend: provided_cells ─────────────────────────────────────────


def _seg_provided_cells(df: pd.DataFrame) -> pd.DataFrame:
    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)
    return df[df[cell_col].notna() & (df[cell_col].astype(str) != "")].copy()


# ── Backend: fov_cell_id ────────────────────────────────────────────


def _seg_fov_cell_id(df: pd.DataFrame) -> pd.DataFrame:
    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)
    fov_col = resolve_col_strict(df.columns, COL_FOV)
    assigned = df.copy()
    assigned[cell_col] = assigned[fov_col].astype(str) + "_" + assigned[cell_col].astype(str)
    return assigned


# ── Backend: cellpose (image-based) ──────────────────────────────────


try:
    from cellpose import models as cp_models

    _CELLPOSE_AVAILABLE = True
except ImportError:
    _CELLPOSE_AVAILABLE = False


def _seg_cellpose(
    df: pd.DataFrame,
    image_path: str | Path | None = None,
    model_type: str = "nuclei",
    diameter: float | None = None,
    flow_threshold: float = 0.4,
    cellprob_threshold: float = 0.0,
    channels: list[int] | None = None,
) -> pd.DataFrame:
    if not _CELLPOSE_AVAILABLE:
        raise ImportError("Cellpose backend requires 'cellpose' to be installed. Run: pip install cellpose")
    if image_path is None:
        raise ValueError(
            "Cellpose backend requires an 'image_path' parameter. "
            "Set 'segmentation_image_path' in your pipeline config."
        )

    x_col = resolve_col_strict(df.columns, COL_X)
    y_col = resolve_col_strict(df.columns, COL_Y)
    fov_col = resolve_col_strict(df.columns, COL_FOV)
    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)

    _validate_columns(df, {x_col, y_col, fov_col}, "cellpose")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Cellpose image not found: {image_path}")

    channels = channels or [0, 0]

    logger.info("Cellpose: loading image '%s' (model=%s, diameter=%s)", image_path, model_type, diameter)

    from cellpose import io as cp_io

    img = cp_io.imread(str(image_path))
    if img.ndim == 2:
        img = img[:, :, np.newaxis]

    model = cp_models.CellposeModel(model_type=model_type)
    masks, flows, styles = model.eval(
        img, diameter=diameter, flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold, channels=channels,
    )

    if masks.ndim == 3:
        masks = masks[0]

    n_masks = int(masks.max())
    logger.info("Cellpose: detected %d cell masks", n_masks)

    assigned = df.copy()
    cell_labels = []
    for _, row in assigned.iterrows():
        xi = int(round(row[x_col]))
        yi = int(round(row[y_col]))
        if 0 <= yi < masks.shape[0] and 0 <= xi < masks.shape[1]:
            mask_id = masks[yi, xi]
            if mask_id > 0:
                cell_labels.append(f"cellpose_{int(mask_id)}")
            else:
                cell_labels.append(None)
        else:
            cell_labels.append(None)

    assigned[cell_col] = cell_labels
    assigned = assigned.dropna(subset=[cell_col]).reset_index(drop=True)

    extra = {"n_cellpose_masks": int(n_masks), "model_type": model_type}
    return assigned, extra


# ── Backend: baysor (transcript-coordinate-based) ───────────────────


def _seg_baysor(
    df: pd.DataFrame,
    baysor_cmd: str = "baysor",
    config: str | None = None,
    scale: float | None = None,
    prior_segmentation_confidence: float = 0.5,
    min_molecules_per_cell: int = 10,
    max_cells: int | None = None,
) -> pd.DataFrame:
    x_col = resolve_col_strict(df.columns, COL_X)
    y_col = resolve_col_strict(df.columns, COL_Y)
    gene_col = resolve_col_strict(df.columns, COL_GENE)
    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)
    fov_col = resolve_col_strict(df.columns, COL_FOV)

    _validate_columns(df, {x_col, y_col, gene_col, fov_col}, "baysor")

    with tempfile.TemporaryDirectory(prefix="baysor_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_csv = tmpdir_path / "transcripts.csv"
        output_dir = tmpdir_path / "segmentation"

        baysor_df = pd.DataFrame({"x": df[x_col], "y": df[y_col], "gene": df[gene_col]})
        baysor_df.to_csv(input_csv, index=False)

        cmd = [
            baysor_cmd, "run", str(input_csv), str(output_dir),
            "--no-plot",
            f"--prior-segmentation-confidence={prior_segmentation_confidence}",
            f"--min-molecules-per-cell={min_molecules_per_cell}",
        ]
        if scale is not None:
            cmd.append(f"--scale={scale}")
        if max_cells is not None:
            cmd.append(f"--max-cells={max_cells}")
        if config is not None:
            cmd.extend(["--config", config])

        logger.info("Baysor: running command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,  # 15 min timeout
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Baysor CLI '{baysor_cmd}' not found. "
                "Please install Baysor from https://github.com/kharchenkolab/Baysor "
                "and ensure it is on your PATH."
            ) from None
        except subprocess.TimeoutExpired:
            raise TimeoutError("Baysor segmentation timed out after 15 minutes.") from None

        if result.returncode != 0:
            raise RuntimeError(
                f"Baysor failed with exit code {result.returncode}.\n"
                f"stderr: {result.stderr[:1000]}"
            )

        # ── Read Baysor output ──────────────────────────────────────
        # Baysor output: output_dir / segments.csv
        segments_csv = output_dir / "segments.csv"
        if not segments_csv.exists():
            # Try alternative output file name
            segments_csv = output_dir / "segmentation.csv"

        if not segments_csv.exists():
            raise FileNotFoundError(
                f"Baysor output not found at {segments_csv}. "
                f"Baysor stderr: {result.stderr[:500]}"
            )

        baysor_out = pd.read_csv(segments_csv)
        # Baysor columns: x, y, gene, cell (segmentation assignment)
        if "cell" not in baysor_out.columns:
            # Baysor may use a different column name
            possible_cols = ["segmentation", "cluster", "assignment"]
            found = [c for c in possible_cols if c in baysor_out.columns]
            if found:
                baysor_out.rename(columns={found[0]: "cell"}, inplace=True)
            else:
                raise ValueError(
                    f"Baysor output missing 'cell' column. Columns: {list(baysor_out.columns)}"
                )

        baysor_out["cell"] = "baysor_" + baysor_out["cell"].astype(str)

        # ── Merge back to original transcript positions ─────────────
        cell_col = resolve_col_strict(df.columns, COL_CELL_ID)
        result_df = df.copy()
        result_df[cell_col] = baysor_out["cell"].values

        result_df = result_df.dropna(subset=[cell_col]).reset_index(drop=True)
        result_df = result_df[result_df[cell_col] != "baysor_0"].reset_index(drop=True)

    n_baysor_cells = result_df[cell_col].nunique()
    extra = {"n_baysor_cells": int(n_baysor_cells)}
    return result_df, extra


# ── Register backends ────────────────────────────────────────────────

register_backend("segmentation", "provided_cells")(_seg_provided_cells)
register_backend("segmentation", "fov_cell_id")(_seg_fov_cell_id)
if _CELLPOSE_AVAILABLE:
    register_backend("segmentation", "cellpose")(_seg_cellpose)
register_backend("segmentation", "baysor")(_seg_baysor)

# Dispatch table
_SEGMENTATION_FUNCS: dict[str, Any] = {
    "provided_cells": _seg_provided_cells,
    "fov_cell_id": _seg_fov_cell_id,
}
if _CELLPOSE_AVAILABLE:
    _SEGMENTATION_FUNCS["cellpose"] = _seg_cellpose
_SEGMENTATION_FUNCS["baysor"] = _seg_baysor


# ── Main entry point ─────────────────────────────────────────────────


def assign_cells(df: pd.DataFrame, backend: str, **kwargs: Any) -> StepResult:
    """Assign transcripts to cells using the given segmentation *backend*.

    Parameters
    ----------
    df : pd.DataFrame
        Input transcript-level DataFrame.
    backend : str
        Backend name (``"provided_cells"``, ``"fov_cell_id"``,
        ``"cellpose"``, or ``"baysor"``).
    **kwargs
        Additional backend-specific keyword arguments (forwarded from config).

    Returns
    -------
    StepResult
        Standardised result with ``output`` (assigned DataFrame) and
        ``summary`` statistics.
    """
    if backend not in _SEGMENTATION_FUNCS:
        raise ValueError(
            f"Unknown segmentation backend: {backend}. "
            f"Available: {list(_SEGMENTATION_FUNCS)}"
        )

    func = _SEGMENTATION_FUNCS[backend]

    # Backends that return (df, extra_dict)
    if backend == "cellpose":
        if not _CELLPOSE_AVAILABLE:
            raise ImportError("Cellpose not installed. Run: pip install cellpose")
        assigned, extra = func(df, **kwargs)
    elif backend == "baysor":
        assigned, extra = func(df, **kwargs)
    else:
        assigned = func(df)
        extra = {}

    summary = {
        "segmentation_backend": backend,
        "n_transcripts_assigned": int(len(assigned)),
        "n_cells_assigned": int(assigned[resolve_col_strict(assigned.columns, COL_CELL_ID)].nunique()),
        **extra,
    }
    return StepResult(output=assigned, summary=summary, backend_used=backend)


# ── Step runner (registered for pipeline engine) ─────────────────────


@register_runner("segmentation")
def _run_segmentation(
    ctx: ExecutionContext,
    backend: str,
    _params: dict[str, Any],
) -> StepResult:
    """Pipeline engine runner for the segmentation step."""
    if ctx.denoised_df is None:
        raise ValueError("No denoised data before segmentation step")

    # Extract backend-specific params from _params
    # These are configured in pipeline.yaml under segmentation.params
    kwargs: dict[str, Any] = {}
    if backend == "cellpose":
        # Pull cellpose-related settings from params
        for key in ("image_path", "model_type", "diameter", "flow_threshold",
                     "cellprob_threshold", "channels"):
            if key in _params:
                kwargs[key] = _params[key]
    elif backend == "baysor":
        for key in ("baysor_cmd", "config", "scale",
                     "prior_segmentation_confidence", "min_molecules_per_cell",
                     "max_cells"):
            if key in _params:
                kwargs[key] = _params[key]

    result = assign_cells(ctx.denoised_df, backend, **kwargs)
    ctx.segmented_df = result.output
    return result
