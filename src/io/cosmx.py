from __future__ import annotations

from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from spatialdata import SpatialData, sanitize_table
from spatialdata.models import PointsModel

from ..models import DatasetSummary

REQUIRED_COLUMNS = ["fov", "cell_ID", "x_global_px", "y_global_px", "target", "CellComp", "cell"]


def load_cosmx_transcripts(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    return df


def summarize_cosmx_transcripts(df: pd.DataFrame, source_path: str | Path) -> DatasetSummary:
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


def build_cell_level_adata(df: pd.DataFrame) -> ad.AnnData:
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


def build_spatialdata(adata: ad.AnnData) -> SpatialData:
    points_frame = pd.DataFrame(
        {
            "x": adata.obs["x_global_px"].to_numpy(),
            "y": adata.obs["y_global_px"].to_numpy(),
            "cell": adata.obs_names.to_numpy(),
        },
        index=adata.obs_names,
    )
    points = PointsModel.parse(points_frame)

    table = adata.copy()
    sanitize_table(table)

    return SpatialData(points={"cells": points}, tables={"cosmx_table": table})
