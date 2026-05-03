# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Xenium Data Ingestor
#
# Implements ``BaseIngestor`` for 10x Genomics Xenium data.
# Xenium transcripts.parquet / CSV input → canonical transcript table
# → SpatialData.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..constants import (
    COL_CELL_ID,
    COL_FOV,
    COL_GENE,
    COL_QV,
    COL_X,
    COL_Y,
    PLATFORM_XENIUM,
)
from .base import BaseIngestor, register_ingestor


@register_ingestor(PLATFORM_XENIUM)
class XeniumIngestor(BaseIngestor):
    """Ingestor for 10x Genomics Xenium data.

    Supports both:
    - ``transcripts.parquet`` (native Xenium output)
    - ``transcripts.csv`` (exported from Xenium Explorer)
    """

    platform: str = PLATFORM_XENIUM

    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        resolved = self._resolve_path(input_path)
        if resolved.suffix == ".parquet":
            df = pd.read_parquet(resolved)
        else:
            df = pd.read_csv(resolved)
        self._validate_raw_columns(df, {"x_location", "y_location", "feature_name", "cell_id"})
        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        return [
            ("x_location", COL_X),
            ("y_location", COL_Y),
            ("feature_name", COL_GENE),
            ("cell_id", COL_CELL_ID),
            ("fov_name", COL_FOV),
            ("qv", COL_QV),
        ]

