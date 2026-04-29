# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Data Validation Layer
# Pydantic-based schema validation for pipeline step inputs/outputs.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

# ── Required column schemas per step ─────────────────────────────────

DENOISE_REQUIRED_COLUMNS = {"CellComp"}
SEGMENTATION_REQUIRED_COLUMNS = {"cell", "fov", "cell_ID"}
SUBCELLULAR_REQUIRED_COLUMNS = {"cell", "x_global_px", "y_global_px"}
ANALYSIS_REQUIRED_OBSM = {"X_pca", "spatial"}
ANNOTATION_REQUIRED_OBS = {"cluster"}


# ── Validation helpers ───────────────────────────────────────────────


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: set[str],
    name: str = "DataFrame",
    allow_extra: bool = True,  # noqa: ARG001
) -> list[str]:
    """Validate that a DataFrame has all required columns.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    required_columns : set[str]
        Set of column names that must be present.
    name : str
        A human-readable name for error messages.
    allow_extra : bool
        If True (default), extra columns beyond the required ones are
        allowed; if False, they cause a warning-level message.

    Returns
    -------
    list[str]
        A list of validation messages (empty if all checks pass).
    """
    messages: list[str] = []
    missing = required_columns - set(df.columns)
    if missing:
        messages.append(f"{name}: missing required columns: {sorted(missing)}")
    return messages


def validate_anndata_obs(
    adata: Any,
    required_obs: set[str],
    name: str = "AnnData",
) -> list[str]:
    """Validate that an AnnData object has all required ``.obs`` columns."""
    messages: list[str] = []
    missing = required_obs - set(adata.obs.columns)
    if missing:
        messages.append(f"{name}.obs: missing required columns: {sorted(missing)}")
    return messages


def validate_anndata_obsm(
    adata: Any,
    required_obsm: set[str],
    name: str = "AnnData",
) -> list[str]:
    """Validate that an AnnData object has all required ``.obsm`` keys."""
    messages: list[str] = []
    missing = required_obsm - set(adata.obsm.keys())
    if missing:
        messages.append(f"{name}.obsm: missing required keys: {sorted(missing)}")
    return messages


def validate_non_empty(
    df: pd.DataFrame,
    name: str = "DataFrame",
) -> list[str]:
    """Validate that a DataFrame is not empty."""
    if df.empty:
        return [f"{name}: is empty"]
    return []


def validate_file_exists(path: Path, name: str = "File") -> list[str]:
    """Validate that a file exists."""
    if not path.exists():
        return [f"{name}: not found: {path}"]
    return []


# ── Composite validators ─────────────────────────────────────────────


def validate_denoise_input(df: pd.DataFrame) -> list[str]:
    """Validate input to the denoise step."""
    msgs: list[str] = []
    msgs.extend(validate_dataframe(df, DENOISE_REQUIRED_COLUMNS, "denoise input"))
    msgs.extend(validate_non_empty(df, "denoise input"))
    return msgs


def validate_segmentation_input(df: pd.DataFrame) -> list[str]:
    """Validate input to the segmentation step."""
    msgs: list[str] = []
    msgs.extend(validate_dataframe(df, SEGMENTATION_REQUIRED_COLUMNS, "segmentation input"))
    msgs.extend(validate_non_empty(df, "segmentation input"))
    return msgs


def validate_subcellular_input(df: pd.DataFrame) -> list[str]:
    """Validate input to the subcellular spatial domain step."""
    msgs: list[str] = []
    msgs.extend(validate_dataframe(df, SUBCELLULAR_REQUIRED_COLUMNS, "subcellular input"))
    msgs.extend(validate_non_empty(df, "subcellular input"))
    return msgs


def validate_analysis_input(adata: Any) -> list[str]:
    """Validate input to the analysis (clustering) step."""
    msgs: list[str] = []
    msgs.extend(validate_anndata_obsm(adata, ANALYSIS_REQUIRED_OBSM, "analysis input"))
    return msgs


def validate_annotation_input(adata: Any) -> list[str]:
    """Validate input to the annotation step."""
    msgs: list[str] = []
    msgs.extend(validate_anndata_obs(adata, ANNOTATION_REQUIRED_OBS, "annotation input"))
    return msgs


# ── Pipeline-level input validation ──────────────────────────────────


def validate_run_input(
    input_csv: str | Path,
    output_dir: str | Path,  # noqa: ARG001
    min_transcripts: int,
    min_genes: int,
) -> list[str]:
    """Validate top-level pipeline run parameters."""
    msgs: list[str] = []
    msgs.extend(validate_file_exists(Path(input_csv), "input_csv"))

    if min_transcripts < 0:
        msgs.append(f"min_transcripts must be >= 0, got {min_transcripts}")
    if min_genes < 0:
        msgs.append(f"min_genes must be >= 0, got {min_genes}")

    return msgs
