# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Multi-Platform Data Ingestion Abstraction
#
# ``BaseIngestor`` is the single entry-point for all platforms.  Each
# platform subclass implements ``_parse_transcripts()`` — the rest
# (column standardisation, points construction, shapes derivation,
# image loading, SpatialData assembly) is shared logic in the base
# class.
#
# The result is a ``SpatialData`` object with:
#   - points["raw_transcripts"]     — canonical transcript table
#   - shapes["provided_boundaries"] — cell polygons (if cell_id present)
#   - images["morphology_image"]    — (optional)
#   - tables["reference_table"]     — (optional)
#   - attrs                         — metadata pointers
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shapely.geometry as geom
from spatialdata import SpatialData
from spatialdata.models import PointsModel, ShapesModel

from ..constants import (
    ATTRS_CELL_ID_COLUMN,
    ATTRS_CELL_ID_EXISTS,
    ATTRS_CELL_SEGMENTATION_IMAGE,
    ATTRS_INGESTION_SUMMARY,
    ATTRS_MAIN_BOUNDARIES_KEY,
    ATTRS_MAIN_TRANSCRIPTS_KEY,
    ATTRS_PLATFORM,
    ATTRS_RAW_TRANSCRIPTS_KEY,
    COL_CELL_ID,
    COL_CELLCOMP,
    COL_FOV,
    COL_GENE,
    COL_QV,
    COL_X,
    COL_Y,
    COL_Z,
    KEY_HE_IMAGE,
    KEY_MORPHOLOGY_IMAGE,
    KEY_PROVIDED_BOUNDARIES,
    KEY_RAW_TRANSCRIPTS,
    KEY_REFERENCE_TABLE,
    OPTIONAL_CANONICAL_COLUMNS,
    REQUIRED_CANONICAL_COLUMNS,
)
from ..models import DatasetSummary

logger = logging.getLogger(__name__)


# ── Errors ───────────────────────────────────────────────────────────


class DataLoadError(Exception):
    """Raised when a data loader fails to read or validate input data."""

    def __init__(self, message: str, platform: str = "unknown", path: str | Path | None = None) -> None:
        self.platform = platform
        self.path = str(path) if path else None
        super().__init__(message)


class DataValidationError(DataLoadError):
    """Raised when loaded data fails structural/content validation."""
    pass


# ── Base Ingestor ────────────────────────────────────────────────────


class BaseIngestor(ABC):
    """Abstract base for all platform ingestors.

    A platform subclass only needs to implement:

        _parse_transcripts(input_path) → pd.DataFrame
        _column_mapping() → list[tuple[str, str]]
        _load_images(input_path) → dict[str, Any]          (optional)
        _load_reference_table(input_path) → Any             (optional)

    Everything else (column standardisation, SpatialData assembly,
    boundary construction, summary, attrs) is handled by the base class.
    """

    platform: str = "unknown"

    # ── Subclass contract ────────────────────────────────────────────

    @abstractmethod
    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        """Load raw transcripts from *input_path*.

        The returned DataFrame may use platform-native column names.
        It will be standardised to the canonical schema afterwards.
        """
        ...

    def _column_mapping(self) -> list[tuple[str, str]]:
        """Return ``[(native_name, canonical_name), ...]`` mapping.

        The list is ordered by priority: for a canonical column with
        multiple possible native names, put the preferred source first.

        Override in subclasses.  If empty, the DataFrame is expected
        to already use canonical names.
        """
        return []

    def _load_images(self, input_path: str | Path) -> dict[str, Any]:
        """Load platform-specific images (DAPI, H&E, etc.).

        Returns a dict of ``{key: SpatialImage}``.  Default returns empty.
        Subclasses that have images override this.
        """
        return {}

    def _load_reference_table(self, input_path: str | Path) -> Any:
        """Load an optional single-cell reference AnnData (for Tangram).

        Returns an ``AnnData`` or ``None``.  Subclasses that provide
        references override this.
        """
        return None

    # ── Shared helpers for _parse_transcripts ────────────────────────

    @staticmethod
    def _resolve_path(input_path: str | Path) -> Path:
        """Resolve and validate the input path."""
        resolved = Path(input_path)
        if not resolved.exists():
            raise DataLoadError(
                f"Input file does not exist: {resolved}",
                path=resolved,
            )
        return resolved

    def _validate_raw_columns(self, df: pd.DataFrame, required: set[str]) -> None:
        """Validate that the raw DataFrame has all required native columns.

        Called inside ``_parse_transcripts`` before standardisation.
        """
        missing = required - set(df.columns)
        if missing:
            raise DataValidationError(
                f"[{self.platform}] Missing required native columns: {sorted(missing)}. "
                f"Columns present: {sorted(df.columns)}",
                platform=self.platform,
            )

    # ── Public entry point ───────────────────────────────────────────

    def ingest(self, input_path: str | Path) -> SpatialData:
        """Run full ingestion: parse → standardise → build SpatialData.

        Parameters
        ----------
        input_path : str or Path
            Path to the input data file or directory.

        Returns
        -------
        SpatialData
            Standardised spatial data object with points, shapes,
            images, and attrs.
        """
        input_path = Path(input_path)

        # 1. Parse platform-specific transcripts
        logger.info("[%s] Parsing transcripts from %s …", self.platform, input_path)
        df_raw = self._parse_transcripts(input_path)

        # 2. Standardise to canonical column names
        logger.info("[%s] Standardising columns to canonical schema …", self.platform)
        df = self._standardise_columns(df_raw)

        # 3. Validate
        self._validate_canonical(df)

        # 4. Build summary
        summary = self._build_summary(df, input_path)

        # 5. Build transcript points
        logger.info("[%s] Building point layer …", self.platform)
        points_df = self._build_points_dataframe(df)

        # 6. Derive cell boundaries (if cell_id exists)
        shapes: dict[str, Any] = {}
        has_cell_id = self._has_valid_cell_id(df)
        if has_cell_id:
            logger.info("[%s] Building provided_boundaries from cell_id …", self.platform)
            boundaries = self._build_provided_boundaries(df)
            if boundaries is not None:
                shapes[KEY_PROVIDED_BOUNDARIES] = boundaries

        # 7. Load images
        logger.info("[%s] Loading images …", self.platform)
        images = self._load_images(input_path)

        # 8. Load reference table
        reference = self._load_reference_table(input_path)

        # 9. Assemble SpatialData
        logger.info("[%s] Assembling SpatialData …", self.platform)
        sdata = self._assemble_sdata(points_df, shapes, images, reference, summary, has_cell_id)

        logger.info(
            "[%s] Ingestion complete: %d transcripts, %d cells, %d genes",
            self.platform,
            summary.n_transcripts,
            summary.n_cells,
            summary.n_genes,
        )
        return sdata

    # ── Column standardisation ───────────────────────────────────────

    def _standardise_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map platform-native column names to canonical schema.

        Uses ``_column_mapping()`` which returns a **priority-ordered
        list** of ``(native_name, canonical_name)`` pairs.  For each
        canonical column, the first native column that actually exists
        in *df* wins — this avoids conflicts when multiple native names
        could map to the same canonical column (e.g. ``global_x`` and
        ``x`` both → ``x``).
        """
        mapping = self._column_mapping()
        if not mapping:
            return df.copy()

        # Build the rename map: for each canonical target, pick the
        # first native source column that exists in the DataFrame.
        seen_targets: set[str] = set()
        rename_map: dict[str, str] = {}
        for native, canonical in mapping:
            if canonical in seen_targets:
                continue
            if native in df.columns:
                rename_map[native] = canonical
                seen_targets.add(canonical)

        if rename_map:
            df = df.rename(columns=rename_map)

        # Fill missing optional columns with defaults
        for col in OPTIONAL_CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = self._default_value(col)

        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        """Return ``[(native_name, canonical_name), ...]`` mapping.

        The list is ordered by priority: for a canonical column with
        multiple possible native names, put the preferred source first.

        Override in subclasses.  If empty, the DataFrame is expected
        to already use canonical names.
        """
        return []

    @staticmethod
    def _default_value(col: str) -> Any:
        """Return a sensible default for an optional canonical column."""
        defaults: dict[str, Any] = {
            COL_CELL_ID: pd.NA,
            COL_FOV: 0,
            COL_CELLCOMP: "Unknown",
            COL_QV: np.nan,
            COL_Z: np.nan,
        }
        return defaults.get(col, pd.NA)

    # ── Validation ───────────────────────────────────────────────────

    def _validate_canonical(self, df: pd.DataFrame) -> None:
        """Ensure all required canonical columns are present."""
        missing = REQUIRED_CANONICAL_COLUMNS - set(df.columns)
        if missing:
            raise DataValidationError(
                f"[{self.platform}] Missing required canonical columns: {sorted(missing)}. "
                f"Columns present: {sorted(df.columns)}",
                platform=self.platform,
            )
        if df.empty:
            raise DataValidationError(
                f"[{self.platform}] Transcript DataFrame is empty.",
                platform=self.platform,
            )

    # ── Points construction ──────────────────────────────────────────

    def _build_points_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Build the point-level DataFrame that will become ``raw_transcripts``."""
        cols = [COL_X, COL_Y, COL_GENE]
        for opt in [COL_Z, COL_CELL_ID, COL_FOV, COL_CELLCOMP, COL_QV]:
            if opt in df.columns:
                cols.append(opt)

        points = df[cols].copy()

        # Ensure coordinates are numeric
        points[COL_X] = pd.to_numeric(points[COL_X], errors="coerce")
        points[COL_Y] = pd.to_numeric(points[COL_Y], errors="coerce")
        if COL_Z in points.columns:
            points[COL_Z] = pd.to_numeric(points[COL_Z], errors="coerce")

        # Ensure gene is string
        points[COL_GENE] = points[COL_GENE].astype(str)

        return points

    # ── Summary ──────────────────────────────────────────────────────

    def _build_summary(self, df: pd.DataFrame, source_path: Path) -> DatasetSummary:
        """Build dataset-level summary statistics."""
        n_transcripts = len(df)
        n_cells = df[COL_CELL_ID].dropna().nunique() if self._has_valid_cell_id(df) else 0
        n_genes = df[COL_GENE].nunique()
        n_fovs = df[COL_FOV].nunique() if COL_FOV in df.columns else 1

        extra: dict[str, Any] = {"platform": self.platform}

        if COL_CELLCOMP in df.columns and self._has_valid_cell_comp(df):
            nuclear_frac = float((df[COL_CELLCOMP] == "Nuclear").mean())
            cyto_frac = float((df[COL_CELLCOMP] == "Cytoplasm").mean())
            extra["nuclear_fraction"] = nuclear_frac
            extra["cytoplasm_fraction"] = cyto_frac

        return DatasetSummary(
            source_path=source_path,
            n_transcripts=n_transcripts,
            n_cells=n_cells,
            n_genes=n_genes,
            n_fovs=n_fovs,
            extra=extra,
        )

    # ── Cell boundaries ──────────────────────────────────────────────

    @staticmethod
    def _has_valid_cell_id(df: pd.DataFrame) -> bool:
        """Check whether the DataFrame has meaningful cell IDs."""
        if COL_CELL_ID not in df.columns:
            return False
        col = df[COL_CELL_ID].dropna()
        if col.empty:
            return False
        # Filter out placeholder values
        valid = col.astype(str).str.strip()
        valid = valid[(valid != "") & (valid != "nan") & (valid != "None") & (valid != "0")]
        return not valid.empty

    @staticmethod
    def _has_valid_cell_comp(df: pd.DataFrame) -> bool:
        if COL_CELLCOMP not in df.columns:
            return False
        return df[COL_CELLCOMP].dropna().isin(["Nuclear", "Cytoplasm"]).any()

    def _build_provided_boundaries(self, df: pd.DataFrame) -> Any:
        """Build cell boundary polygons from transcript coordinates.

        For each cell_id, computes the convex hull of all transcript
        positions.  Returns a ``GeoDataFrame`` with columns:
        ``[cell_id, geometry, area, centroid_x, centroid_y, n_transcripts]``.
        """
        valid = df[df[COL_CELL_ID].notna()]
        valid = valid[valid[COL_CELL_ID].astype(str).str.strip().isin(["", "nan", "None"]) == False]  # noqa: E712

        if valid.empty:
            logger.warning("[%s] No valid cell IDs — skipping boundary construction.", self.platform)
            return None

        records: list[dict[str, Any]] = []

        for cell_id, group in valid.groupby(COL_CELL_ID):
            pts = group[[COL_X, COL_Y]].dropna().to_numpy()
            if len(pts) < 3:
                cx, cy = pts.mean(axis=0) if len(pts) > 0 else (0.0, 0.0)
                poly = geom.Point(cx, cy).buffer(1.0)
            else:
                try:
                    from scipy.spatial import ConvexHull
                    hull = ConvexHull(pts)
                    poly = geom.Polygon(pts[hull.vertices])
                except Exception:
                    xmin, ymin = pts.min(axis=0)
                    xmax, ymax = pts.max(axis=0)
                    poly = geom.box(xmin, ymin, xmax, ymax)

            centroid = poly.centroid
            records.append({
                "cell_id": str(cell_id),
                "geometry": poly,
                "area": poly.area,
                "centroid_x": centroid.x,
                "centroid_y": centroid.y,
                "n_transcripts": len(group),
            })

        import geopandas as gpd
        gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=None)
        return gdf

    # ── Assembly ─────────────────────────────────────────────────────

    def _assemble_sdata(
        self,
        points_df: pd.DataFrame,
        shapes: dict[str, Any],
        images: dict[str, Any],
        reference: Any,
        summary: DatasetSummary,
        has_cell_id: bool,
    ) -> SpatialData:
        """Put all layers together into a SpatialData object."""
        # Points
        points_model = PointsModel.parse(points_df, coordinates={COL_X: COL_X, COL_Y: COL_Y})
        points_dict = {KEY_RAW_TRANSCRIPTS: points_model}

        # Shapes — wrap with ShapesModel if not already
        shapes_dict: dict[str, Any] = {}
        for key, gdf in shapes.items():
            try:
                shapes_dict[key] = ShapesModel.parse(gdf)
            except Exception:
                shapes_dict[key] = gdf

        # Tables
        tables_dict: dict[str, Any] = {}
        if reference is not None:
            tables_dict[KEY_REFERENCE_TABLE] = reference

        # attrs
        attrs: dict[str, Any] = {
            ATTRS_PLATFORM: self.platform,
            ATTRS_RAW_TRANSCRIPTS_KEY: KEY_RAW_TRANSCRIPTS,
            ATTRS_MAIN_TRANSCRIPTS_KEY: KEY_RAW_TRANSCRIPTS,
            ATTRS_CELL_ID_EXISTS: has_cell_id,
            ATTRS_CELL_ID_COLUMN: COL_CELL_ID if has_cell_id else None,
        }

        if KEY_PROVIDED_BOUNDARIES in shapes_dict:
            attrs[ATTRS_MAIN_BOUNDARIES_KEY] = KEY_PROVIDED_BOUNDARIES
        else:
            attrs[ATTRS_MAIN_BOUNDARIES_KEY] = None

        if KEY_MORPHOLOGY_IMAGE in images:
            attrs[ATTRS_CELL_SEGMENTATION_IMAGE] = KEY_MORPHOLOGY_IMAGE
        elif KEY_HE_IMAGE in images:
            attrs[ATTRS_CELL_SEGMENTATION_IMAGE] = KEY_HE_IMAGE
        else:
            attrs[ATTRS_CELL_SEGMENTATION_IMAGE] = None

        attrs[ATTRS_INGESTION_SUMMARY] = {
            "n_transcripts": summary.n_transcripts,
            "n_cells": summary.n_cells,
            "n_genes": summary.n_genes,
            "n_fovs": summary.n_fovs,
            **summary.extra,
        }

        sdata = SpatialData(
            points=points_dict,
            shapes=shapes_dict if shapes_dict else None,
            images=images if images else None,
            tables=tables_dict if tables_dict else None,
        )

        for key, value in attrs.items():
            sdata.attrs[key] = value

        return sdata


# ── Ingestor registry ────────────────────────────────────────────────

_INGESTOR_REGISTRY: dict[str, type[BaseIngestor]] = {}


def register_ingestor(platform: str) -> Any:
    """Decorator to register a platform ingestor class."""
    def decorator(cls: type[BaseIngestor]) -> type[BaseIngestor]:
        cls.platform = platform
        _INGESTOR_REGISTRY[platform] = cls
        return cls
    return decorator


def get_ingestor(platform: str) -> BaseIngestor:
    """Return a singleton ingestor instance for *platform*."""
    cls = _INGESTOR_REGISTRY.get(platform)
    if cls is None:
        raise DataLoadError(
            f"Unknown platform '{platform}'. Available: {sorted(_INGESTOR_REGISTRY)}",
            platform=platform,
        )
    return cls()


def get_available_platforms() -> list[str]:
    """Return sorted list of registered platform names."""
    return sorted(_INGESTOR_REGISTRY)
