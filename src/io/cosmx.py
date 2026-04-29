# ─────────────────────────────────────────────────────────────────────
# SubCellSpace CosMx Data Loader
#
# Implements ``BaseDataLoader`` for the NanoString CosMx platform.
# Also exposes legacy module-level functions for backward compatibility.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from spatialdata import SpatialData, sanitize_table
from spatialdata.models import PointsModel

from ..models import DatasetSummary
from .base import BaseDataLoader

REQUIRED_COLUMNS = {"fov", "cell_ID", "x_global_px", "y_global_px", "target", "CellComp", "cell"}


class CosMxDataLoader(BaseDataLoader):
    """Data loader for NanoString CosMx Spatial Molecular Imager data."""

    platform: str = "cosmx"
    required_columns: set[str] = REQUIRED_COLUMNS

    def load(self, path: str | Path) -> pd.DataFrame:
        resolved = self._validate_file_exists(path)
        df = pd.read_csv(resolved)
        self._validate_columns(df, path)
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])
        return df

    def summarize(self, df: pd.DataFrame, source_path: str | Path) -> DatasetSummary:
        source_path = Path(source_path)
        return DatasetSummary(
            source_path=source_path,
            n_transcripts=int(len(df)),
            n_cells=int(df["cell"].nunique()),
            n_genes=int(df["target"].nunique()),
            n_fovs=int(df["fov"].nunique()),
            extra={
                "cell_id_unique": int(df["cell_ID"].nunique()),
                "nuclear_fraction": float((df["CellComp"] == "Nuclear").mean()),
            },
        )

    def build_adata(self, df: pd.DataFrame) -> ad.AnnData:
        cell_index = df["cell"].astype(str)
        gene_index = df["target"].astype(str)

        counts = pd.crosstab(cell_index, gene_index)
        counts = counts.sort_index(axis=0).sort_index(axis=1)

        grouped = df.groupby("cell", sort=True)
        obs = grouped.agg(
            fov=("fov", "first"),
            cell_ID=("cell_ID", "first"),
            n_transcripts=("target", "size"),
            n_genes=("target", "nunique"),
            x_global_px=("x_global_px", "mean"),
            y_global_px=("y_global_px", "mean"),
            x_local_px=("x_local_px", "mean"),
            y_local_px=("y_local_px", "mean"),
            nuclear_fraction=("CellComp", lambda values: float((values == "Nuclear").mean())),
        )

        adata = ad.AnnData(X=counts.to_numpy(dtype=np.int32), obs=obs, var=pd.DataFrame(index=counts.columns))
        adata.obs_names = counts.index.astype(str)
        adata.var_names = counts.columns.astype(str)
        adata.obsm["spatial"] = obs[["x_global_px", "y_global_px"]].to_numpy(dtype=np.float32)
        adata.layers["counts"] = adata.X.copy()
        adata.uns["cosmx"] = {
            "cell_level_source": "transcript aggregation",
        }
        return adata

    def build_spatialdata(self, adata: ad.AnnData) -> SpatialData:
        # Use spatial coordinates from obsm["spatial"] as primary source;
        # fall back to x_global_px / y_global_px in obs for CosMx data.
        if "spatial" in adata.obsm:
            coords = adata.obsm["spatial"]
            x = coords[:, 0]
            y = coords[:, 1]
        elif "x_global_px" in adata.obs and "y_global_px" in adata.obs:
            x = adata.obs["x_global_px"].to_numpy()
            y = adata.obs["y_global_px"].to_numpy()
        else:
            raise KeyError("No spatial coordinates found in adata.obsm['spatial'] or adata.obs['x_global_px']")

        points_frame = pd.DataFrame(
            {
                "x": x,
                "y": y,
                "cell": adata.obs_names.to_numpy(),
            },
            index=adata.obs_names,
        )
        points = PointsModel.parse(points_frame)

        table = adata.copy()
        sanitize_table(table)

        return SpatialData(points={"cells": points}, tables={"cosmx_table": table})


# ── Module-level singleton loader ───────────────────────────────────
_singleton_loader: CosMxDataLoader | None = None


def _get_loader() -> CosMxDataLoader:
    global _singleton_loader
    if _singleton_loader is None:
        _singleton_loader = CosMxDataLoader()
    return _singleton_loader


# ── Legacy module-level functions (backward compat) ─────────────────


def load_cosmx_transcripts(path: str | Path) -> pd.DataFrame:
    """Legacy wrapper — delegates to CosMxDataLoader.load()."""
    return _get_loader().load(path)


def summarize_cosmx_transcripts(df: pd.DataFrame, source_path: str | Path) -> DatasetSummary:
    """Legacy wrapper — delegates to CosMxDataLoader.summarize()."""
    return _get_loader().summarize(df, source_path)


def build_cell_level_adata(df: pd.DataFrame) -> ad.AnnData:
    """Legacy wrapper — delegates to CosMxDataLoader.build_adata()."""
    return _get_loader().build_adata(df)


def build_spatialdata(adata: ad.AnnData) -> SpatialData:
    """Legacy wrapper — delegates to CosMxDataLoader.build_spatialdata()."""
    return _get_loader().build_spatialdata(adata)
