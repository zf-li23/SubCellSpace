# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Xenium Data Loader (stub)
#
# Implements ``BaseDataLoader`` for the 10x Genomics Xenium platform.
# Replace placeholder logic with real parsing once Xenium data format
# specifications are available.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from spatialdata import SpatialData

from ..models import DatasetSummary
from .base import BaseDataLoader

# Typical Xenium output columns (may vary by version).
# See https://www.10xgenomics.com/support/software/xenium-onboard-analysis
XENIUM_REQUIRED_COLUMNS = {"cell_id", "x_location", "y_location", "feature_name"}


class XeniumDataLoader(BaseDataLoader):
    """Data loader for 10x Genomics Xenium data.

    .. note::
        This is a **stub** implementation.  Real parsing logic should
        be added once the exact input data format is determined.
    """

    platform: str = "xenium"
    required_columns: set[str] = XENIUM_REQUIRED_COLUMNS

    def load(self, path: str | Path) -> pd.DataFrame:
        resolved = self._validate_file_exists(path)
        df = pd.read_csv(resolved)
        self._validate_columns(df, path)
        # Map Xenium column names to the canonical internal schema
        df = df.rename(
            columns={
                "cell_id": "cell",
                "x_location": "x_global_px",
                "y_location": "y_global_px",
                "feature_name": "target",
            }
        )
        # Ensure a CellComp column with a default value
        if "CellComp" not in df.columns:
            df["CellComp"] = "Cytoplasm"
        if "cell_ID" not in df.columns:
            df["cell_ID"] = df["cell"].astype(str)
        if "fov" not in df.columns:
            df["fov"] = 0
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
                "platform": "xenium",
            },
        )

    def build_adata(self, df: pd.DataFrame) -> ad.AnnData:
        # Reuse the CosMx-like aggregation logic
        cell_index = df["cell"].astype(str)
        gene_index = df["target"].astype(str)
        counts = pd.crosstab(cell_index, gene_index)
        counts = counts.sort_index(axis=0).sort_index(axis=1)

        grouped = df.groupby("cell", sort=True)
        obs = grouped.agg(
            n_transcripts=("target", "size"),
            n_genes=("target", "nunique"),
            x_global_px=("x_global_px", "mean"),
            y_global_px=("y_global_px", "mean"),
        )

        adata = ad.AnnData(X=counts.to_numpy(dtype=np.int32), obs=obs, var=pd.DataFrame(index=counts.columns))
        adata.obs_names = counts.index.astype(str)
        adata.var_names = counts.columns.astype(str)
        adata.obsm["spatial"] = obs[["x_global_px", "y_global_px"]].to_numpy(dtype=np.float32)
        adata.layers["counts"] = adata.X.copy()
        adata.uns["xenium"] = {"cell_level_source": "transcript aggregation"}
        return adata

    def build_spatialdata(self, adata: ad.AnnData) -> SpatialData:
        from spatialdata import SpatialData, sanitize_table
        from spatialdata.models import PointsModel

        if "spatial" in adata.obsm:
            coords = adata.obsm["spatial"]
        else:
            raise KeyError("No spatial coordinates in adata.obsm['spatial']")

        points_frame = pd.DataFrame(
            {"x": coords[:, 0], "y": coords[:, 1], "cell": adata.obs_names.to_numpy()},
            index=adata.obs_names,
        )
        points = PointsModel.parse(points_frame)
        table = adata.copy()
        sanitize_table(table)
        return SpatialData(points={"cells": points}, tables={"xenium_table": table})
