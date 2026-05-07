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

import pandas as pd

from .base import (
    BaseIngestor,
    DataLoadError,
    DataValidationError,
    get_available_platforms,
    get_ingestor,
    register_ingestor,
)

# Import platform modules to trigger @register_ingestor decorators
from . import cosmx   # noqa: F401
from . import merfish  # noqa: F401
from . import stereoseq  # noqa: F401
from . import xenium   # noqa: F401


# ── Platform auto-detection ─────────────────────────────────────────

# Detection rules: (condition, platform_name)
# Evaluated in order — first match wins.

def _detect_by_columns(columns: set[str]) -> str | None:
    """Detect platform from column names."""
    # Xenium: x_location + feature_name + cell_id
    if {"x_location", "y_location", "feature_name", "cell_id"}.issubset(columns):
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
    # Stereo-seq: geneID + x + y (GEM format)
    if {"geneID", "x", "y"}.issubset(columns):
        return "stereoseq"
    # CosMx fallback: x_global_px + target (without CellComp)
    if "x_global_px" in columns and "y_global_px" in columns and "target" in columns:
        return "cosmx"
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
        Detected platform name ("cosmx", "xenium", "merfish", "stereoseq").

    Raises
    ------
    DataLoadError
        If the platform cannot be detected.
    """
    resolved = Path(input_path)
    if not resolved.exists():
        raise DataLoadError(f"Input file does not exist: {resolved}", path=resolved)

    suffix = resolved.suffix.lower()

    # 1. By extension — strongest signal
    if suffix == ".parquet":
        return "xenium"
    if suffix == ".gem":
        return "stereoseq"

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
        f"Please specify --platform explicitly (cosmx/xenium/merfish/stereoseq).",
        path=resolved,
    )


def ingest(platform: str, input_path: str | Path) -> Any:
    """Run data ingestion for *platform* and return a SpatialData object.

    Parameters
    ----------
    platform : str
        One of ``"cosmx"``, ``"xenium"``, ``"merfish"``, ``"stereoseq"``.
    input_path : str or Path
        Path to the input data file or directory.

    Returns
    -------
    SpatialData
        Standardised spatial data object.
    """
    return get_ingestor(platform).ingest(Path(input_path))


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
