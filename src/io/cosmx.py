# ─────────────────────────────────────────────────────────────────────
# SubCellSpace CosMx Data Ingestor
#
# Implements ``BaseIngestor`` for NanoString CosMx SMI data.
# Reads the full NanoString output directory (or single tx_file CSV)
# and integrates all available companion files:
#   - *_polygons.csv(.gz)        → proper cell boundaries (ShapesModel)
#   - *_exprMat_file.csv(.gz)    → pre-computed expression matrix
#   - *_metadata_file.csv(.gz)   → cell-level metadata for adata.obs
#   - *_fov_positions_file.csv   → FOV spatial layout
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from spatialdata import SpatialData
from spatialdata.models import ShapesModel

from ..constants import (
    COL_CELL_ID,
    COL_CELLCOMP,
    COL_FOV,
    COL_GENE,
    COL_X,
    COL_Y,
    KEY_PROVIDED_BOUNDARIES,
    PLATFORM_COSMX,
)
from .base import BaseIngestor, DataLoadError, register_ingestor

logger = logging.getLogger(__name__)


# ── Helper: discover companion files ────────────────────────────────


def _find_companion(tx_path: Path, pattern_suffix: str) -> Path | None:
    """Look for a companion file next to *tx_path* matching *pattern_suffix*.

    Tries exact name first (replace 'tx_file' with pattern), then glob.
    Returns the first match or None.
    """
    tx_name = tx_path.name
    # Try replacing 'tx_file' in the filename
    companion_name = tx_name.replace("tx_file", pattern_suffix)
    for suffix in ("", ".gz"):
        candidate = tx_path.parent / (companion_name + suffix)
        if candidate.exists():
            return candidate
    # Fallback: glob for any file ending with the pattern
    for f in tx_path.parent.glob(f"*{pattern_suffix}*"):
        return f
    return None


def _read_csv_or_gz(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV file, transparently handling .gz compression."""
    if path.suffix == ".gz":
        import gzip
        with gzip.open(path, "rt") as f:
            df = pd.read_csv(f, **kwargs)
    else:
        df = pd.read_csv(path, **kwargs)
    # Drop any Unnamed columns (caused by leading comma in some CosMx CSVs)
    unnamed = [c for c in df.columns if c.startswith("Unnamed:")]
    if unnamed:
        df = df.drop(columns=unnamed)
    return df


@register_ingestor(PLATFORM_COSMX)
class CosMxIngestor(BaseIngestor):
    """Ingestor for NanoString CosMx Spatial Molecular Imager data.

    Accepts either:
    - A path to the ``*_tx_file.csv`` (with companion files auto-detected)
    - A directory containing the NanoString output files
    """

    platform: str = PLATFORM_COSMX

    def ingest(self, input_path: str | Path) -> SpatialData:
        """Run full ingestion with companion file integration."""
        input_path = Path(input_path)
        tx_path = self._resolve_tx_path(input_path)

        # Parse transcripts
        logger.info("[%s] Parsing transcripts from %s …", self.platform, tx_path)
        df_raw = self._parse_transcripts(tx_path)

        # Standardise to canonical column names
        logger.info("[%s] Standardising columns to canonical schema …", self.platform)
        df = self._standardise_columns(df_raw)
        self._validate_canonical(df)

        # Detect and load companion files
        companion_dir = tx_path.parent
        boundaries_gdf = self._load_polygons(companion_dir, tx_path)
        expr_matrix = self._load_expression_matrix(companion_dir, tx_path)
        cell_metadata = self._load_cell_metadata(companion_dir, tx_path)
        fov_positions = self._load_fov_positions(companion_dir, tx_path)

        # Build summary
        summary = self._build_summary(df, input_path)

        # Build transcript points
        logger.info("[%s] Building point layer …", self.platform)
        points_df = self._build_points_dataframe(df)

        # Build shapes from polygon file if available, else fallback to convex hull
        shapes: dict[str, Any] = {}
        if boundaries_gdf is not None:
            logger.info("[%s] Using NanoString-provided cell boundaries (polygons) …", self.platform)
            shapes[KEY_PROVIDED_BOUNDARIES] = boundaries_gdf
        else:
            has_cell_id = self._has_valid_cell_id(df)
            if has_cell_id:
                logger.info("[%s] Building provided_boundaries from cell_id convex hull …", self.platform)
                b = self._build_provided_boundaries(df)
                if b is not None:
                    shapes[KEY_PROVIDED_BOUNDARIES] = b

        # Store companion data in attrs for downstream use
        attrs_extra: dict[str, Any] = {}
        if expr_matrix is not None:
            attrs_extra["cosmx_expr_matrix"] = expr_matrix
        if cell_metadata is not None:
            attrs_extra["cosmx_cell_metadata"] = cell_metadata
        if fov_positions is not None:
            attrs_extra["cosmx_fov_positions"] = fov_positions

        # Assemble SpatialData
        logger.info("[%s] Assembling SpatialData …", self.platform)
        sdata = self._assemble_sdata(
            points_df, shapes, images={}, reference=None,
            summary=summary, has_cell_id=bool(boundaries_gdf is not None or self._has_valid_cell_id(df)),
        )
        # Merge extra attrs
        sdata.attrs.update(attrs_extra)
        sdata.attrs["companion_files"] = {
            "polygons": boundaries_gdf is not None,
            "expr_matrix": expr_matrix is not None,
            "cell_metadata": cell_metadata is not None,
            "fov_positions": fov_positions is not None,
        }

        logger.info(
            "[%s] Ingestion complete: %d transcripts, %d cells, %d genes%s",
            self.platform,
            summary.n_transcripts,
            summary.n_cells,
            summary.n_genes,
            f" (+{sum(1 for v in sdata.attrs['companion_files'].values() if v)} companion files)"
            if any(sdata.attrs['companion_files'].values()) else "",
        )
        return sdata

    # ── Companion file loaders ──────────────────────────────────────

    def _resolve_tx_path(self, input_path: Path) -> Path:
        """Find the tx_file from either a file or directory input."""
        if input_path.is_dir():
            # Look for *tx_file.csv* in the directory
            candidates = list(input_path.glob("*tx_file.csv*"))
            if not candidates:
                raise DataLoadError(
                    f"No tx_file.csv found in directory {input_path}",
                    platform=self.platform, path=input_path,
                )
            return candidates[0]
        return self._resolve_path(input_path)

    def _load_polygons(self, companion_dir: Path, tx_path: Path) -> Any:
        """Load cell boundary polygons from companion file."""
        poly_path = _find_companion(tx_path, "polygons")
        if poly_path is None:
            return None
        logger.info("[%s] Loading cell boundaries from %s …", self.platform, poly_path.name)
        try:
            df = _read_csv_or_gz(poly_path)
            # Expected columns: cell_ID, x_local_px, y_local_px (or similar)
            # NanoString polygon format: fov, cellID, cell, x_local_px, y_local_px, x_global_px, y_global_px
            # We need to group by cell and build polygon from coordinates
            cell_col = None
            for candidate in ("cell_ID", "cellID", "cell_id"):
                if candidate in df.columns:
                    cell_col = candidate
                    break
            if cell_col is None:
                logger.warning("[%s] Polygon file has no cell ID column: %s", self.platform, list(df.columns))
                return None

            x_col = None
            for candidate in ("x_global_px", "x_local_px", "x"):
                if candidate in df.columns:
                    x_col = candidate
                    break
            y_col = None
            for candidate in ("y_global_px", "y_local_px", "y"):
                if candidate in df.columns:
                    y_col = candidate
                    break
            if x_col is None or y_col is None:
                logger.warning("[%s] Polygon file missing coordinate columns", self.platform)
                return None

            # Build polygons per (fov, cellID) — NanoString polygon files
            # have per-FOV vertex groups for each cell.  Grouping by cellID
            # alone would merge vertices from all FOVs into one giant polygon.
            records = []
            for (fov_id, cell_id_val), group in df.groupby(["fov", cell_col]):
                pts = group[[x_col, y_col]].dropna().to_numpy()
                if len(pts) < 3:
                    continue
                try:
                    poly = __import__("shapely", fromlist=["geometry"]).geometry.Polygon(pts)
                except Exception:
                    continue
                centroid = poly.centroid
                records.append({
                    "fov": int(fov_id),
                    "cell_id": f"{int(fov_id)}_{str(cell_id_val)}",
                    "cell_name": str(group.iloc[0].get("cell", "")),
                    "geometry": poly,
                    "area": poly.area,
                    "centroid_x": centroid.x,
                    "centroid_y": centroid.y,
                    "n_boundary_points": len(pts),
                })

            if not records:
                return None
            gdf = __import__("geopandas", fromlist=["GeoDataFrame"]).GeoDataFrame(records, crs=None)
            return ShapesModel.parse(gdf)
        except Exception as exc:
            logger.warning("[%s] Failed to load polygons from %s: %s", self.platform, poly_path, exc)
            return None

    def _load_expression_matrix(self, companion_dir: Path, tx_path: Path) -> pd.DataFrame | None:
        """Load pre-computed expression matrix if available."""
        expr_path = _find_companion(tx_path, "exprMat_file")
        if expr_path is None:
            expr_path = _find_companion(tx_path, "exprMat")
        if expr_path is None:
            return None
        logger.info("[%s] Loading expression matrix from %s …", self.platform, expr_path.name)
        try:
            df = _read_csv_or_gz(expr_path)
            # CosMx exprMat: may have (fov, cell_ID) as separate columns.
            # Create a combined "fov_cellID" index to ensure uniqueness.
            has_fov = "fov" in df.columns
            has_cell_id = any(c in df.columns for c in ("cell_ID", "cell_id"))
            if has_fov and has_cell_id:
                id_col = "cell_ID" if "cell_ID" in df.columns else "cell_id"
                df["fov_cellID"] = df["fov"].astype(str) + "_" + df[id_col].astype(str)
                df = df.set_index("fov_cellID")
            else:
                # Fallback: use the first identifier column found
                id_col = None
                for candidate in ("cell_ID", "cell_id", "fov"):
                    if candidate in df.columns:
                        id_col = candidate
                        break
                if id_col is None:
                    id_col = df.columns[0]
                df = df.set_index(id_col)
            df.index = df.index.astype(str)
            # Drop non-gene columns (fov, cell_ID, cell, etc.)
            drop_cols = [c for c in df.columns if c.lower() in ("fov", "cell_id", "cell", "fov_cellid", "")]
            if drop_cols:
                df = df.drop(columns=drop_cols, errors="ignore")
            return df.astype(np.float32)
        except Exception as exc:
            logger.warning("[%s] Failed to load expression matrix: %s", self.platform, exc)
            return None

    def _load_cell_metadata(self, companion_dir: Path, tx_path: Path) -> pd.DataFrame | None:
        """Load cell metadata if available."""
        meta_path = _find_companion(tx_path, "metadata_file")
        if meta_path is None:
            return None
        logger.info("[%s] Loading cell metadata from %s …", self.platform, meta_path.name)
        try:
            df = _read_csv_or_gz(meta_path)
            return df
        except Exception as exc:
            logger.warning("[%s] Failed to load cell metadata: %s", self.platform, exc)
            return None

    def _load_fov_positions(self, companion_dir: Path, tx_path: Path) -> pd.DataFrame | None:
        """Load FOV positions if available."""
        fov_path = _find_companion(tx_path, "fov_positions_file")
        if fov_path is None:
            fov_path = _find_companion(tx_path, "fov_positions")
        if fov_path is None:
            return None
        logger.info("[%s] Loading FOV positions from %s …", self.platform, fov_path.name)
        try:
            return _read_csv_or_gz(fov_path)
        except Exception as exc:
            logger.warning("[%s] Failed to load FOV positions: %s", self.platform, exc)
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
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])
        self._validate_raw_columns(df, {"x_global_px", "y_global_px", "target"})
        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        # Include all known aliases for cell_id so datasets that use
        # "cell_ID", "CellID", "barcode_id" etc. are handled correctly.
        # D0021 (organoid) uses "cell_ID" instead of "cell".
        return [
            ("x_global_px", COL_X),
            ("y_global_px", COL_Y),
            ("target", COL_GENE),
            ("cell", COL_CELL_ID),
            ("cell_id", COL_CELL_ID),
            ("cell_ID", COL_CELL_ID),
            ("CellID", COL_CELL_ID),
            ("cell_label", COL_CELL_ID),
            ("barcode_id", COL_CELL_ID),
            ("fov", COL_FOV),
            ("CellComp", COL_CELLCOMP),
        ]

