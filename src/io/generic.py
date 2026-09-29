# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Generic Data Ingestor
#
# Minimal ingestor for any CSV/TSV with spatial coordinates and gene
# names.  No platform-specific columns required — ideal for ad-hoc
# data or simple transcript-level CSV files.
#
# Expected minimal columns: x, y, gene  (canonical names preferred)
# Optional columns: cell_id, fov, z, CellComp, qv
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import gzip
from pathlib import Path

import pandas as pd

from ..constants import (
    COL_CELL_ID,
    COL_CELLCOMP,
    COL_FOV,
    COL_GENE,
    COL_QV,
    COL_X,
    COL_Y,
    COL_Z,
    PLATFORM_GENERIC,
)
from .base import BaseIngestor, register_ingestor


@register_ingestor(PLATFORM_GENERIC)
class GenericIngestor(BaseIngestor):
    """Ingestor for minimal transcript CSV files.

    Accepts any delimited file (.csv, .csv.gz, .tsv, .tsv.gz) with at
    least spatial coordinates and gene identifiers.  Column names are
    auto-detected via the canonical alias table.

    If ``cell_id`` is not present, cells will be assigned later by the
    segmentation step (e.g. fov_cell_id or cellpose).
    """

    platform: str = PLATFORM_GENERIC

    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        resolved = self._resolve_path(input_path)
        suffix = resolved.suffix.lower()
        suffixes = resolved.suffixes if hasattr(resolved, "suffixes") else [suffix]

        # Detect compression
        is_gz = suffix == ".gz" or ".gz" in [s.lower() for s in suffixes]
        is_tsv = ".tsv" in suffix or any(".tsv" in s.lower() for s in suffixes)

        # Read
        if is_gz:
            with gzip.open(resolved, "rt") as f:
                df = pd.read_csv(f, sep="\t" if is_tsv else ",")
        else:
            sep = "\t" if is_tsv else ","
            df = pd.read_csv(resolved, sep=sep)

        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])

        # Validate: must have spatial coords + gene
        found_x = _resolve_column(df.columns, COL_X)
        found_y = _resolve_column(df.columns, COL_Y)
        found_gene = _resolve_column(df.columns, COL_GENE)

        missing = []
        if found_x is None:
            missing.append(f"spatial x ({COL_X} / x_global_px / x_location / global_x)")
        if found_y is None:
            missing.append(f"spatial y ({COL_Y} / y_global_px / y_location / global_y)")
        if found_gene is None:
            missing.append(f"gene ({COL_GENE} / target / feature_name / geneID)")

        if missing:
            raise ValueError(
                f"Cannot ingest '{resolved.name}': missing required columns.\n"
                f"  Missing: {', '.join(missing)}\n"
                f"  Found:   {sorted(df.columns.tolist())}\n"
                f"Hint: The minimal CSV needs at least x, y, and gene columns. "
                f"Use canonical names ({COL_X}, {COL_Y}, {COL_GENE}) or "
                f"platform-native names."
            )

        # Report what was detected
        import logging
        log = logging.getLogger(__name__)
        log.info(
            "Generic ingestion: %d transcripts, columns=%s (x=%s, y=%s, gene=%s)",
            len(df),
            sorted(df.columns.tolist()),
            found_x,
            found_y,
            found_gene,
        )

        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        """Return all possible native→canonical column mappings.

        BaseIngestor._standardize_columns() will only apply those where
        the native column actually exists in the DataFrame.
        """
        from ..constants import _LEGACY_ALIASES

        mapping: list[tuple[str, str]] = []

        # Required columns — include all known aliases
        for canon in [COL_X, COL_Y, COL_GENE]:
            # Canonical name first
            mapping.append((canon, canon))
            # Then all legacy aliases
            for alias in _LEGACY_ALIASES.get(canon, []):
                mapping.append((alias, canon))

        # Optional columns
        for canon in [COL_CELL_ID, COL_FOV, COL_Z, COL_CELLCOMP, COL_QV]:
            mapping.append((canon, canon))
            for alias in _LEGACY_ALIASES.get(canon, []):
                mapping.append((alias, canon))

        return mapping


# ── Column name resolution helpers ───────────────────────────────────


def _resolve_column(columns: pd.Index, canonical: str) -> str | None:
    """Find the actual column name matching *canonical* in *columns*."""
    from ..constants import _LEGACY_ALIASES

    if canonical in columns:
        return canonical
    for alias in _LEGACY_ALIASES.get(canonical, []):
        if alias in columns:
            return alias
    return None
