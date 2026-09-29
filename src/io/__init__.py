# ─────────────────────────────────────────────────────────────────────
# SubCellSpace I/O module
# Platform-specific data ingestors for spatial transcriptomics data.
#
# Usage::
#
#     from subcellspace.io import ingest, detect_platform
#     platform = detect_platform("data/test/sample.csv")
#     sdata = ingest(platform, "data/test/sample.csv")
#
# Each platform ingestor produces a standardised ``SpatialData`` object.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

# Import platform modules to trigger @register_ingestor decorators
from . import (
    cosmx,  # noqa: F401
    generic,  # noqa: F401 — minimal CSV (x, y, gene)
    merfish,  # noqa: F401
    xenium,  # noqa: F401
)
from .base import (
    BaseIngestor,
    DataLoadError,
    DataValidationError,
    get_available_platforms,
    get_ingestor,
    register_ingestor,
)

# ── Platform auto-detection ─────────────────────────────────────────

# Detection rules: (condition, platform_name)
# Evaluated in order — first match wins.

def _detect_by_columns(columns: set[str]) -> str | None:
    """Detect platform from column names."""
    # Xenium (standard): x_location + feature_name + cell_id
    if {"x_location", "y_location", "feature_name", "cell_id"}.issubset(columns):
        return "xenium"
    # Xenium (flexible): feature_name + cell_id + (x|y or x_location|y_location)
    # Handles CSV exports where coords are named x/y instead of x_location/y_location
    if {"feature_name", "cell_id"}.issubset(columns):
        has_xy = {"x", "y"}.issubset(columns) or {"x_location", "y_location"}.issubset(columns)
        if has_xy:
            return "xenium"
    # CosMx: x_global_px + target (+ CellComp)
    if {"x_global_px", "y_global_px", "target"}.issubset(columns):
        return "cosmx"
    # MERFISH (long names): global_x + global_y + gene + barcode_id
    if {"global_x", "global_y", "gene"}.issubset(columns) and "barcode_id" in columns:
        return "merfish"
    # MERFISH (short names): x + y + gene + barcode_id
    if {"x", "y", "gene", "barcode_id"}.issubset(columns):
        return "merfish"
    # CosMx fallback: x_global_px + target (without CellComp)
    if "x_global_px" in columns and "y_global_px" in columns and "target" in columns:
        return "cosmx"

    # Generic fallback: any file with spatial x, y and a gene/feature column
    from ..constants import _LEGACY_ALIASES as _aliases

    has_x = "x" in columns or any(a in columns for a in _aliases.get("x", []))
    has_y = "y" in columns or any(a in columns for a in _aliases.get("y", []))
    has_gene = "gene" in columns or any(a in columns for a in _aliases.get("gene", []))
    if has_x and has_y and has_gene:
        return "generic"

    return None


def detect_platform(input_path: str | Path) -> str:
    """Auto-detect the spatial transcriptomics platform from a file.

    Detection order:
    1. File extension (``.parquet`` → Xenium, ``.gem`` → Stereo-seq)
    2. Column name signature (reads first rows of CSV/TSV)

    Parameters
    ----------
    input_path : str or Path
        Path to the input data file.

    Returns
    -------
    str
        Detected platform name ("cosmx", "xenium", "merfish", "generic").

    Raises
    ------
    DataLoadError
        If the platform cannot be detected.
    """
    resolved = Path(input_path)
    if not resolved.exists():
        raise DataLoadError(f"Input file does not exist: {resolved}", path=resolved)

    # ── If input is a directory, search for transcript files inside ──
    if resolved.is_dir():
        # Priority order: platform-specific patterns first, then generic CSV
        patterns = [
            "*tx_file.csv*",            # CosMx
            "*detected_transcripts.csv*",  # MERFISH
            "transcripts.csv*",         # Xenium
            "transcripts.parquet",      # Xenium parquet
            "*.csv", "*.csv.gz",        # Generic fallback
        ]
        for pattern in patterns:
            candidates = sorted(resolved.glob(pattern))
            if candidates:
                # Try detecting platform from the first match
                try:
                    return detect_platform(candidates[0])
                except DataLoadError:
                    continue  # try next pattern
        raise DataLoadError(
            f"Cannot auto-detect platform for directory {resolved}. "
            f"No recognized transcript file found. "
            f"Please specify --platform explicitly.",
            path=resolved,
        )

    suffix = resolved.suffix.lower()

    # 1. By extension — strongest signal
    if suffix == ".parquet":
        return "xenium"

    # 2. By column signature
    try:
        sep = "\t" if suffix == ".tsv" else ","
        df = pd.read_csv(resolved, sep=sep, nrows=5)
        platform = _detect_by_columns(set(df.columns))
        if platform:
            return platform
    except Exception:
        pass

    raise DataLoadError(
        f"Cannot auto-detect platform for {resolved}. "
        f"Please specify --platform explicitly (cosmx/xenium/merfish/generic).",
        path=resolved,
    )


def ingest(platform: str, input_path: str | Path, cell_id_column: str | None = None) -> Any:
    """Run data ingestion for *platform* and return a SpatialData object.

    Parameters
    ----------
    platform : str
        One of ``"cosmx"``, ``"xenium"``, ``"merfish"``, ``"generic"``.
    input_path : str or Path
        Path to the input data file or directory.
    cell_id_column : str or None
        Override the cell ID column name (e.g. ``"barcode_id"`` for MERFISH
        data where the default cell_id column differs from actual cells).

    Returns
    -------
    SpatialData
        Standardised spatial data object.
    """
    ingestor = get_ingestor(platform)
    if cell_id_column is not None:
        ingestor._cell_id_column = cell_id_column
    return ingestor.ingest(Path(input_path))


__all__ = [
    "BaseIngestor",
    "DataLoadError",
    "DataValidationError",
    "get_ingestor",
    "get_available_platforms",
    "register_ingestor",
    "detect_platform",
    "ingest",
]
