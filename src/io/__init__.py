"""GEO sample readers.

    from src.io import read_sample
    sample = read_sample("/path/to/GSE…/GSM…/")   # platform auto-detected by touch

See :mod:`src.io.sample` for the conventions every reader follows.
"""

from __future__ import annotations

from pathlib import Path

from .readers import READERS, SampleReadError, read_sample, read_table
from .sample import Sample

__all__ = ["Sample", "SampleReadError", "read_sample", "read_table", "detect_platform", "get_available_platforms"]


def get_available_platforms() -> list[str]:
    return sorted(READERS)


def detect_platform(transcript_file: str | Path) -> str | None:
    """Guess the platform from a transcript file's column names (used by touch as a fallback)."""
    is_parquet = ".parquet" in str(transcript_file)
    cols = set(read_table(transcript_file).columns if is_parquet else read_table(transcript_file, nrows=5).columns)
    if {"feature_name", "x_location", "y_location"} <= cols:
        return "xenium"
    if {"x_global_px", "y_global_px", "target"} <= cols:
        return "cosmx"
    if "gene" in cols and ({"global_x", "global_y"} <= cols or "barcode_id" in cols):
        return "merfish"
    return None
