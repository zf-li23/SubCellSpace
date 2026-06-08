# ─────────────────────────────────────────────────────────────────────
# SubCellSpace MERFISH Data Ingestor
#
# Implements ``BaseIngestor`` for MERFISH / Vizgen MERSCOPE data.
# Reads MERFISH CSV input and integrates companion files:
#   - *_cell_by_gene.csv → pre-computed expression matrix
#   - *_cell_metadata.csv → cell metadata
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from ..constants import (
    COL_CELL_ID,
    COL_FOV,
    COL_GENE,
    COL_X,
    COL_Y,
    COL_Z,
    KEY_PROVIDED_BOUNDARIES,
    PLATFORM_MERFISH,
)
from .base import BaseIngestor, register_ingestor

logger = logging.getLogger(__name__)


def _read_csv_or_gz(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV file, transparently handling .gz compression.

    Unlike relying on pandas auto-detection, this explicitly checks
    the file extension and uses ``gzip.open()`` when needed — matching
    the CosMx ``_read_csv_or_gz`` pattern for consistency.
    """
    if path.suffix == ".gz":
        import gzip
        with gzip.open(path, "rt") as f:
            return pd.read_csv(f, **kwargs)
    return pd.read_csv(path, **kwargs)


def _find_companion(tx_path: Path, pattern_suffix: str) -> Path | None:
    """Look for a companion file next to *tx_path* matching *pattern_suffix*."""
    tx_name = tx_path.name
    # Try replacing 'detected_transcripts' in the filename
    companion_name = tx_name.replace("detected_transcripts", pattern_suffix)
    for suffix in ("", ".gz"):
        candidate = tx_path.parent / (companion_name + suffix)
        if candidate.exists():
            return candidate
    # Fallback: glob
    for f in tx_path.parent.glob(f"*{pattern_suffix}*"):
        return f
    return None


@register_ingestor(PLATFORM_MERFISH)
class MERFISHIngestor(BaseIngestor):
    """Ingestor for MERFISH / Vizgen MERSCOPE data.

    Accepts either:
    - Path to ``*_detected_transcripts.csv`` (auto-detects companion files)
    - Path to a generic transcripts CSV file
    """

    platform: str = PLATFORM_MERFISH

    def ingest(self, input_path: str | Path) -> Any:
        input_path = Path(input_path)
        tx_path = self._resolve_path(input_path)

        # Parse transcripts
        logger.info("[%s] Parsing transcripts from %s …", self.platform, tx_path)
        df_raw = self._parse_transcripts(tx_path)
        logger.info("[%s] Standardising columns to canonical schema …", self.platform)
        df = self._standardise_columns(df_raw)
        self._validate_canonical(df)

        # Load companion files
        companion_dir = tx_path.parent
        expr_matrix = self._load_expression_matrix(companion_dir, tx_path)
        cell_metadata = self._load_cell_metadata(companion_dir, tx_path)

        # Build summary
        summary = self._build_summary(df, input_path)

        # Build transcript points
        logger.info("[%s] Building point layer …", self.platform)
        points_df = self._build_points_dataframe(df)

        # Build shapes
        shapes: dict[str, Any] = {}
        if self._has_valid_cell_id(df):
            logger.info("[%s] Building provided_boundaries from cell_id …", self.platform)
            b = self._build_provided_boundaries(df)
            if b is not None:
                shapes[KEY_PROVIDED_BOUNDARIES] = b

        # Store extra attrs
        attrs_extra: dict[str, Any] = {}
        if expr_matrix is not None:
            attrs_extra["merfish_expr_matrix"] = expr_matrix
        if cell_metadata is not None:
            attrs_extra["merfish_cell_metadata"] = cell_metadata

        # Assemble SpatialData
        logger.info("[%s] Assembling SpatialData …", self.platform)
        sdata = self._assemble_sdata(
            points_df, shapes, images={}, reference=None,
            summary=summary, has_cell_id=self._has_valid_cell_id(df),
        )
        sdata.attrs.update(attrs_extra)
        sdata.attrs["companion_files"] = {
            "expr_matrix": expr_matrix is not None,
            "cell_metadata": cell_metadata is not None,
        }

        logger.info(
            "[%s] Ingestion complete: %d transcripts, %d cells, %d genes%s",
            self.platform, summary.n_transcripts, summary.n_cells, summary.n_genes,
            f" (+{sum(1 for v in sdata.attrs['companion_files'].values() if v)} companion files)"
            if any(sdata.attrs['companion_files'].values()) else "",
        )
        return sdata

    # ── Companion file loaders ──────────────────────────────────────

    def _load_expression_matrix(self, companion_dir: Path, tx_path: Path) -> pd.DataFrame | None:
        path = _find_companion(tx_path, "cell_by_gene")
        if path is None:
            return None
        logger.info("[%s] Loading expression matrix from %s …", self.platform, path.name)
        try:
            df = _read_csv_or_gz(path)
            # First column is typically barcode/cell_id
            id_col = df.columns[0]
            df = df.set_index(id_col)
            df.index = df.index.astype(str)
            return df.astype("float32")
        except Exception as exc:
            logger.warning("[%s] Failed to load expression matrix: %s", self.platform, exc)
            return None

    def _load_cell_metadata(self, companion_dir: Path, tx_path: Path) -> pd.DataFrame | None:
        path = _find_companion(tx_path, "cell_metadata")
        if path is None:
            return None
        logger.info("[%s] Loading cell metadata from %s …", self.platform, path.name)
        try:
            return _read_csv_or_gz(path)
        except Exception as exc:
            logger.warning("[%s] Failed to load cell metadata: %s", self.platform, exc)
            return None

    # ── Original methods ───────────────────────────────────────────

    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        resolved = self._resolve_path(input_path)
        if resolved.suffix == ".gz":
            import gzip
            with gzip.open(resolved, "rt") as f:
                df = pd.read_csv(f)
        else:
            df = pd.read_csv(resolved)

        has_long = {"global_x", "global_y"}.issubset(df.columns)
        has_short = {"x", "y"}.issubset(df.columns)
        if has_long and has_short:
            df = df.drop(columns=["x", "y"], errors="ignore")
        if has_long:
            required = {"global_x", "global_y", "gene"}
        elif has_short:
            required = {"x", "y", "gene"}
        else:
            required = {"global_x", "global_y"}

        self._validate_raw_columns(df, required)
        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        cell_id_col = getattr(self, "_cell_id_column", None) or "barcode_id"
        return [
            ("global_x", COL_X),
            ("global_y", COL_Y),
            ("gene", COL_GENE),
            (cell_id_col, COL_CELL_ID),
            ("fov", COL_FOV),
            ("global_z", COL_Z),
            ("z", COL_Z),
        ]

