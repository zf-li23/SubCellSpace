# ─────────────────────────────────────────────────────────────────────
# SubCellSpace MERFISH Data Ingestor
#
# Implements ``BaseIngestor`` for MERFISH / Vizgen MERSCOPE data.
# MERFISH CSV input → canonical transcript table → SpatialData.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..constants import (
    COL_CELL_ID,
    COL_FOV,
    COL_GENE,
    COL_X,
    COL_Y,
    COL_Z,
    PLATFORM_MERFISH,
)
from .base import BaseIngestor, register_ingestor


@register_ingestor(PLATFORM_MERFISH)
class MERFISHIngestor(BaseIngestor):
    """Ingestor for MERFISH / Vizgen MERSCOPE data.

    Expected columns: ``global_x, global_y, gene, cell_id`` (or short
    names ``x, y``).
    """

    platform: str = PLATFORM_MERFISH

    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        resolved = self._resolve_path(input_path)
        df = pd.read_csv(resolved)

        # Accept either long or short coordinate column names
        has_long = {"global_x", "global_y"}.issubset(df.columns)
        has_short = {"x", "y"}.issubset(df.columns)
        if has_long:
            required = {"global_x", "global_y", "gene"}
        elif has_short:
            required = {"x", "y", "gene"}
        else:
            required = {"global_x", "global_y"}

        self._validate_raw_columns(df, required)
        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        return [
            ("global_x", COL_X),
            ("x", COL_X),
            ("global_y", COL_Y),
            ("y", COL_Y),
            ("gene", COL_GENE),
            ("cell_id", COL_CELL_ID),
            ("fov", COL_FOV),
            ("global_z", COL_Z),
            ("z", COL_Z),
        ]

