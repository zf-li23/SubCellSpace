# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Stereo-seq Data Ingestor
#
# Implements ``BaseIngestor`` for BGI / MGI Stereo-seq data.
# Stereo-seq GEM / CSV input → canonical transcript table → SpatialData.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..constants import (
    COL_CELL_ID,
    COL_GENE,
    COL_X,
    COL_Y,
    PLATFORM_STEREOSEQ,
)
from .base import BaseIngestor, register_ingestor


@register_ingestor(PLATFORM_STEREOSEQ)
class StereoSeqIngestor(BaseIngestor):
    """Ingestor for BGI / MGI Stereo-seq data.

    Stereo-seq uses a regular grid layout (bin-based, not cell-based by
    default).  The ``cell_id`` may not be present — in that case, cells
    will be defined by the segmentation step later.
    """

    platform: str = PLATFORM_STEREOSEQ

    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        resolved = self._resolve_path(input_path)
        sep = "\t" if resolved.suffix == ".gem" else ","
        df = pd.read_csv(resolved, sep=sep)

        # geneID is preferred; fall back to gene
        if "geneID" in df.columns:
            required = {"x", "y", "geneID"}
        else:
            required = {"x", "y", "gene"}
        self._validate_raw_columns(df, required)
        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        return [
            ("x", COL_X),
            ("y", COL_Y),
            ("geneID", COL_GENE),
            ("gene", COL_GENE),
            ("cell_id", COL_CELL_ID),
            ("MIDCounts", "mid_counts"),
        ]

