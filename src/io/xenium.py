# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Xenium Data Ingestor
#
# Implements ``BaseIngestor`` for 10x Genomics Xenium data.
# Reads the full Xenium output directory and integrates companion files:
#   - cell_boundaries.parquet → cell polygon boundaries (ShapesModel)
#   - nucleus_boundaries.parquet → nucleus boundaries
#   - cell_feature_matrix.h5 → pre-computed expression matrix
#   - cells.csv.gz → cell metadata
#   - gene_panel.json → gene panel information
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from ..constants import (
    COL_CELL_ID,
    COL_FOV,
    COL_GENE,
    COL_QV,
    COL_X,
    COL_Y,
    COL_Z,
    KEY_PROVIDED_BOUNDARIES,
    PLATFORM_XENIUM,
)
from .base import BaseIngestor, DataLoadError, register_ingestor

logger = logging.getLogger(__name__)


def _find_in_dir(directory: Path, *patterns: str) -> Path | None:
    """Find a file in *directory* matching any of *patterns*."""
    for pattern in patterns:
        candidates = sorted(directory.glob(pattern))
        if candidates:
            return candidates[0]
    return None


@register_ingestor(PLATFORM_XENIUM)
class XeniumIngestor(BaseIngestor):
    """Ingestor for 10x Genomics Xenium data.

    Accepts either:
    - A Xenium output directory (auto-detects all files)
    - A specific ``transcripts.csv(.gz)`` or ``transcripts.parquet`` file
    - A ``transcripts.zarr.zip`` file (auto-extracted to temp dir)
    """

    platform: str = PLATFORM_XENIUM

    def ingest(self, input_path: str | Path) -> Any:
        input_path = Path(input_path)

        # Resolve tx_path (directory or single file)
        if input_path.is_dir():
            tx_path = _find_in_dir(input_path, "transcripts.csv.gz", "transcripts.csv",
                                   "transcripts.parquet", "transcripts.zarr.zip")
            if tx_path is None:
                raise DataLoadError(f"No transcript file found in Xenium directory {input_path}", platform=self.platform, path=input_path)
            data_dir = input_path
        else:
            tx_path = self._resolve_path(input_path)
            data_dir = tx_path.parent

        # Parse transcripts
        logger.info("[%s] Parsing transcripts from %s …", self.platform, tx_path)
        df_raw = self._parse_transcripts(tx_path)
        logger.info("[%s] Standardising columns to canonical schema …", self.platform)
        df = self._standardise_columns(df_raw)
        self._validate_canonical(df)

        # Load companion files
        cell_boundaries = self._load_cell_boundaries(data_dir)
        nucleus_boundaries = self._load_nucleus_boundaries(data_dir)
        expr_matrix = self._load_expression_matrix(data_dir)
        cell_metadata = self._load_cell_metadata(data_dir)
        gene_panel = self._load_gene_panel(data_dir)

        # Build summary
        summary = self._build_summary(df, input_path)

        # Build transcript points
        logger.info("[%s] Building point layer …", self.platform)
        points_df = self._build_points_dataframe(df)

        # Build shapes
        shapes: dict[str, Any] = {}
        if cell_boundaries is not None:
            logger.info("[%s] Using Xenium cell_boundaries (parquet) …", self.platform)
            shapes[KEY_PROVIDED_BOUNDARIES] = cell_boundaries
        elif self._has_valid_cell_id(df):
            logger.info("[%s] Building provided_boundaries from cell_id convex hull …", self.platform)
            b = self._build_provided_boundaries(df)
            if b is not None:
                shapes[KEY_PROVIDED_BOUNDARIES] = b

        # Store extra attrs
        attrs_extra: dict[str, Any] = {}
        if expr_matrix is not None:
            attrs_extra["xenium_expr_matrix"] = expr_matrix
        if cell_metadata is not None:
            attrs_extra["xenium_cell_metadata"] = cell_metadata
        if gene_panel is not None:
            attrs_extra["xenium_gene_panel"] = gene_panel
        if nucleus_boundaries is not None:
            attrs_extra["xenium_nucleus_boundaries"] = nucleus_boundaries

        # Assemble SpatialData
        logger.info("[%s] Assembling SpatialData …", self.platform)
        sdata = self._assemble_sdata(
            points_df, shapes, images={}, reference=None,
            summary=summary,
            has_cell_id=bool(cell_boundaries is not None or self._has_valid_cell_id(df)),
        )
        sdata.attrs.update(attrs_extra)
        sdata.attrs["companion_files"] = {
            "cell_boundaries": cell_boundaries is not None,
            "nucleus_boundaries": nucleus_boundaries is not None,
            "expr_matrix": expr_matrix is not None,
            "cell_metadata": cell_metadata is not None,
            "gene_panel": gene_panel is not None,
        }

        logger.info(
            "[%s] Ingestion complete: %d transcripts, %d cells, %d genes%s",
            self.platform, summary.n_transcripts, summary.n_cells, summary.n_genes,
            f" (+{sum(1 for v in sdata.attrs['companion_files'].values() if v)} companion files)"
            if any(sdata.attrs['companion_files'].values()) else "",
        )
        return sdata

    # ── Companion file loaders ──────────────────────────────────────

    def _load_cell_boundaries(self, data_dir: Path) -> Any:
        path = _find_in_dir(data_dir, "cell_boundaries.parquet", "cell_boundaries.parquet.gz",
                            "cell_boundaries.csv.gz")
        if path is None:
            return None
        logger.info("[%s] Loading cell boundaries from %s …", self.platform, path.name)
        try:
            df = (pd.read_parquet(path) if path.suffix in (".parquet", ".gz")
                  and ".parquet" in path.name else pd.read_csv(path))
            gdf = self._vertices_to_polygons(df)
            if gdf is not None:
                from spatialdata.models import ShapesModel
                return ShapesModel.parse(gdf)
            return None
        except Exception as exc:
            logger.warning("[%s] Failed to load cell boundaries: %s", self.platform, exc)
            return None

    def _load_nucleus_boundaries(self, data_dir: Path) -> Any:
        path = _find_in_dir(data_dir, "nucleus_boundaries.parquet", "nucleus_boundaries.parquet.gz",
                            "nucleus_boundaries.csv.gz")
        if path is None:
            return None
        logger.info("[%s] Loading nucleus boundaries from %s …", self.platform, path.name)
        try:
            df = (pd.read_parquet(path) if path.suffix in (".parquet", ".gz")
                  and ".parquet" in path.name else pd.read_csv(path))
            gdf = self._vertices_to_polygons(df)
            return gdf
        except Exception as exc:
            logger.warning("[%s] Failed to load nucleus boundaries: %s", self.platform, exc)
            return None

    @staticmethod
    def _vertices_to_polygons(df: pd.DataFrame) -> Any:
        """Convert Xenium vertex-based boundaries to GeoDataFrame of Polygons."""
        import geopandas as gpd
        from shapely import geometry as geom

        # Identify cell_id column
        cell_col = None
        for c in ("cell_id", "cell_ID"):
            if c in df.columns:
                cell_col = c
                break
        if cell_col is None:
            return None

        # Identify x, y columns
        x_col, y_col = None, None
        for c in ("vertex_x", "x", "x_global_px"):
            if c in df.columns:
                x_col = c
                break
        for c in ("vertex_y", "y", "y_global_px"):
            if c in df.columns:
                y_col = c
                break
        if x_col is None or y_col is None:
            return None

        records = []
        for cell_id, group in df.groupby(cell_col):
            pts = group[[x_col, y_col]].dropna().to_numpy()
            if len(pts) < 3:
                continue
            try:
                poly = geom.Polygon(pts)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                records.append({"cell_id": str(cell_id), "geometry": poly})
            except Exception:
                continue

        if not records:
            return None
        return gpd.GeoDataFrame(records, crs=None)

    def _load_expression_matrix(self, data_dir: Path) -> pd.DataFrame | None:
        path = _find_in_dir(data_dir, "cell_feature_matrix.h5", "cell_feature_matrix.zarr.zip")
        if path is None:
            return None
        logger.info("[%s] Loading expression matrix from %s …", self.platform, path.name)
        try:
            if ".zarr.zip" in path.name:
                return self._read_zarr_matrix(path)
            import scanpy as sc
            adata = sc.read_10x_h5(path)
            return pd.DataFrame(
                adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X,
                index=adata.obs_names, columns=adata.var_names,
            ).astype("float32")
        except Exception as exc:
            logger.warning("[%s] Failed to load expression matrix: %s", self.platform, exc)
            return None

    @staticmethod
    def _read_zarr_matrix(path: Path) -> pd.DataFrame | None:
        """读取 Xenium cell_feature_matrix.zarr.zip 到 DataFrame。"""
        import tempfile, shutil, zipfile
        tmp = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp)
            # Find the zarr root
            import zarr
            import numpy as np
            zarr_dirs = [d for d in Path(tmp).iterdir() if d.is_dir()]
            if not zarr_dirs:
                return None
            z = zarr.open(str(zarr_dirs[0]), mode="r")
            # Xenium zarr format: barcodes, data, indices, indptr, shape, features
            barcodes = [b.decode() if isinstance(b, bytes) else b
                        for b in z["barcodes"][:]]
            feature_names = [f.decode() if isinstance(f, bytes) else f
                             for f in z["features"]["name"][:]]
            data = z["data"][:]
            indices = z["indices"][:]
            indptr = z["indptr"][:]
            shape = tuple(z["shape"][:])
            # Build sparse matrix
            from scipy.sparse import csr_matrix
            mat = csr_matrix((data, indices, indptr), shape=shape)
            return pd.DataFrame(
                mat.toarray().astype("float32"),
                index=barcodes, columns=feature_names,
            )
        except Exception:
            return None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _load_cell_metadata(self, data_dir: Path) -> pd.DataFrame | None:
        path = _find_in_dir(data_dir, "cells.csv.gz", "cells.csv", "cells.parquet",
                            "cells.parquet.gz", "cells.zarr.zip")
        if path is None:
            return None
        logger.info("[%s] Loading cell metadata from %s …", self.platform, path.name)
        try:
            if ".zarr.zip" in path.name:
                return self._read_zarr_cells(path)
            if ".parquet" in path.name:
                return pd.read_parquet(path)
            return pd.read_csv(path, compression="gzip" if path.suffix == ".gz" else None)
        except Exception as exc:
            logger.warning("[%s] Failed to load cell metadata: %s", self.platform, exc)
            return None

    @staticmethod
    def _read_zarr_cells(path: Path) -> pd.DataFrame | None:
        """读取 Xenium cells.zarr.zip 到 DataFrame。"""
        import tempfile, shutil, zipfile
        tmp = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp)
            import zarr
            zarr_dirs = [d for d in Path(tmp).iterdir() if d.is_dir()]
            if not zarr_dirs:
                return None
            z = zarr.open(str(zarr_dirs[0]), mode="r")
            arrays = {k: v[:] for k, v in z.arrays()}
            df = pd.DataFrame(dict(arrays))
            # Decode bytes
            for col in df.columns:
                if df[col].dtype == "O":
                    try:
                        df[col] = df[col].apply(lambda x: x.decode() if isinstance(x, bytes) else x)
                    except Exception:
                        pass
            return df
        except Exception:
            return None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _load_gene_panel(self, data_dir: Path) -> dict | None:
        path = _find_in_dir(data_dir, "gene_panel.json")
        if path is None:
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("[%s] Failed to load gene panel: %s", self.platform, exc)
            return None

    # ── Original methods ───────────────────────────────────────────

    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        resolved = self._resolve_path(input_path)
        if resolved.suffix == ".parquet":
            df = pd.read_parquet(resolved)
        elif ".zarr.zip" in resolved.name:
            import tempfile, shutil, zipfile
            tmp = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(resolved, "r") as zf:
                    zf.extractall(tmp)
                import zarr
                import numpy as np
                zarr_dirs = [d for d in Path(tmp).iterdir() if d.is_dir()]
                if not zarr_dirs:
                    raise DataLoadError("Empty zarr archive", platform=self.platform, path=resolved)
                z = zarr.open(str(zarr_dirs[0]), mode="r")
                data = {}
                for k in z.array_keys():
                    arr = z[k][:]
                    if arr.dtype.kind == "S" or arr.dtype.kind == "O":
                        arr = np.array([x.decode() if isinstance(x, bytes) else x for x in arr])
                    data[k] = arr
                df = pd.DataFrame(data)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        elif resolved.suffix == ".gz" and resolved.suffixes[-2:] == [".csv", ".gz"]:
            import gzip
            with gzip.open(resolved, "rt") as f:
                df = pd.read_csv(f)
        elif resolved.suffix == ".gz":
            df = pd.read_csv(resolved, compression="gzip")
        else:
            df = pd.read_csv(resolved)
        self._validate_raw_columns(df, {"x_location", "y_location", "feature_name", "cell_id"})
        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        return [
            ("x_location", COL_X),
            ("y_location", COL_Y),
            ("z_location", COL_Z),
            ("feature_name", COL_GENE),
            ("cell_id", COL_CELL_ID),
            ("fov_name", COL_FOV),
            ("qv", COL_QV),
        ]

