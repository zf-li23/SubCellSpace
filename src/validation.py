# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Data Validation Layer
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import COL_CELL_ID, COL_GENE, COL_X, COL_Y, COL_CELLCOMP, COL_FOV, resolve_col

# ── Required column schemas per step ─────────────────────────────────

DENOISE_REQUIRED_COLUMNS = {COL_CELLCOMP}
SEGMENTATION_REQUIRED_COLUMNS = {COL_CELL_ID, COL_FOV}
SUBCELLULAR_REQUIRED_COLUMNS = {COL_CELL_ID, COL_X, COL_Y}
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

    Uses ``resolve_col`` to accept legacy column-name aliases.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    required_columns : set[str]
        Set of canonical column names that must be present.
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
    missing: list[str] = []
    for col in required_columns:
        if resolve_col(df.columns, col) is None:
            missing.append(col)
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


# ── Inter-step contract validation ──────────────────────────────────

# Each entry defines the data contract for the transition from one step
# to the next.  "source" is the step whose output is validated, "target"
# is the step that will consume that output.  The ``checks`` list
# specifies what must exist in the ExecutionContext after the source step.
#
# Contracts use set-based checks:
#   - "df_columns": required DataFrame columns in the named context attribute
#   - "obs_columns": required AnnData.obs columns
#   - "obsm_keys": required AnnData.obsm keys

StepContract = dict[str, Any]

STEP_CONTRACTS: list[StepContract] = [
    {
        "source": "denoise",
        "target": "segmentation",
        "checks": [
            {"type": "df_columns", "attr": "denoised_df",
             "required": {COL_CELL_ID, COL_FOV, COL_GENE, COL_X, COL_Y, COL_CELLCOMP}},
        ],
    },
    {
        "source": "segmentation",
        "target": "spatial_domain",
        "checks": [
            {"type": "df_columns", "attr": "segmented_df",
             "required": {COL_CELL_ID, COL_FOV}},
        ],
    },
    {
        "source": "segmentation",
        "target": "subcellular_spatial_domain",
        "checks": [
            {"type": "df_columns", "attr": "segmented_df",
             "required": {COL_CELL_ID, COL_X, COL_Y}},
        ],
    },
    {
        "source": "spatial_domain",
        "target": "analysis",
        "checks": [
            {"type": "obs_columns", "attr": "adata", "required": {"spatial_domain"}},
            {"type": "obsm_keys", "attr": "adata", "required": {"spatial"}},
        ],
    },
    {
        "source": "subcellular_spatial_domain",
        "target": "analysis",
        "checks": [
            {"type": "df_columns", "attr": "segmented_df", "required": {"subcellular_domain"}},
        ],
    },
    {
        "source": "analysis",
        "target": "annotation",
        "checks": [
            {"type": "obs_columns", "attr": "adata", "required": {"cluster"}},
            {"type": "obsm_keys", "attr": "adata", "required": {"X_pca", "spatial"}},
        ],
    },
    {
        "source": "annotation",
        "target": "__pipeline_end__",
        "checks": [
            {"type": "obs_columns", "attr": "adata", "required": {"cluster", "cell_type"}},
        ],
    },
]


def validate_contract(
    source_step: str,
    target_step: str,
    context: Any,  # ExecutionContext
) -> list[str]:
    """Validate the data contract between *source_step* and *target_step*.

    Parameters
    ----------
    source_step : str
        Name of the step that just completed.
    target_step : str
        Name of the next step to run (or ``"__pipeline_end__"`` for
        final output validation).
    context : ExecutionContext
        The current pipeline execution context.

    Returns
    -------
    list[str]
        Validation messages (empty if all checks pass).
    """
    msgs: list[str] = []

    for contract in STEP_CONTRACTS:
        if contract["source"] != source_step or contract["target"] != target_step:
            continue
        for check in contract["checks"]:
            check_type = check["type"]
            attr_name = check["attr"]
            required: set[str] = set(check["required"])

            obj = getattr(context, attr_name, None)
            if obj is None:
                msgs.append(
                    f"Contract [{source_step} → {target_step}]: "
                    f"context.{attr_name} is None (expected {required})"
                )
                continue

            if check_type == "df_columns":
                import pandas as pd
                if not isinstance(obj, pd.DataFrame):
                    msgs.append(
                        f"Contract [{source_step} → {target_step}]: "
                        f"context.{attr_name} is not a DataFrame"
                    )
                    continue
                # Use resolve_col to support legacy aliases
                from .constants import resolve_col as _rc
                missing = {c for c in required if _rc(obj.columns, c) is None}
                if missing:
                    msgs.append(
                        f"Contract [{source_step} → {target_step}]: "
                        f"context.{attr_name} missing columns: {sorted(missing)}"
                    )
            elif check_type == "obs_columns":
                missing = required - set(obj.obs.columns)
                if missing:
                    msgs.append(
                        f"Contract [{source_step} → {target_step}]: "
                        f"context.{attr_name}.obs missing columns: {sorted(missing)}"
                    )
            elif check_type == "obsm_keys":
                missing = required - set(obj.obsm.keys())
                if missing:
                    msgs.append(
                        f"Contract [{source_step} → {target_step}]: "
                        f"context.{attr_name}.obsm missing keys: {sorted(missing)}"
                    )

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
