# ─────────────────────────────────────────────────────────────────────
# SubCellSpace CosMx Data Ingestor
#
# Implements ``BaseIngestor`` for NanoString CosMx SMI data.
# CosMx CSV input → canonical transcript table → SpatialData.
#
# Also provides helper functions for building AnnData and SpatialData
# from transcript-level DataFrames that use the canonical column schema.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from spatialdata import SpatialData, sanitize_table
from spatialdata.models import PointsModel

from ..constants import (
    COL_CELL_ID,
    COL_CELLCOMP,
    COL_FOV,
    COL_GENE,
    COL_X,
    COL_Y,
    KEY_MAIN_TABLE,
    PLATFORM_COSMX,
)
from ..models import DatasetSummary
from .base import BaseIngestor, register_ingestor


# ── Helper: build cell-level AnnData from canonical transcripts ──────


def build_cell_level_adata(
    df: pd.DataFrame,
    min_transcripts: int = 0,
    min_genes: int = 0,
) -> ad.AnnData:
    """Build a cell-level AnnData from a transcript DataFrame.

    Works with BOTH canonical columns (gene, cell_id, x, y) and legacy
    CosMx-native columns (target, cell, x_global_px, y_global_px).

    Parameters
    ----------
    df : pd.DataFrame
        Transcript-level DataFrame.
    min_transcripts : int
        Minimum transcripts per cell (QC filter).
    min_genes : int
        Minimum genes per cell (QC filter).

    Returns
    -------
    AnnData
    """
    from ..constants import COL_CELL_ID, COL_GENE, COL_X, COL_Y, COL_FOV, resolve_col_strict, resolve_col

    gene_col = resolve_col_strict(df.columns, COL_GENE)
    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)
    x_col = resolve_col_strict(df.columns, COL_X)
    y_col = resolve_col_strict(df.columns, COL_Y)
    fov_col = resolve_col(df.columns, COL_FOV)

    cell_index = df[cell_col].astype(str)
    gene_index = df[gene_col].astype(str)

    counts = pd.crosstab(cell_index, gene_index)
    counts = counts.sort_index(axis=0).sort_index(axis=1)

    grouped = df.groupby(cell_col, sort=True)
    obs = grouped.agg(
        n_transcripts=(gene_col, "size"),
        n_genes=(gene_col, "nunique"),
        x=(x_col, "mean"),
        y=(y_col, "mean"),
    )

    if fov_col and fov_col in df.columns:
        obs[fov_col] = grouped[fov_col].first()

    adata = ad.AnnData(
        X=counts.to_numpy(dtype=np.float32),
        obs=obs.loc[counts.index],
        var=pd.DataFrame(index=counts.columns),
    )
    adata.obs_names = counts.index.astype(str)
    adata.var_names = counts.columns.astype(str)
    adata.obsm["spatial"] = obs[["x", "y"]].to_numpy(dtype=np.float32)
    adata.layers["counts"] = adata.X.copy()
    adata.uns["cosmx"] = {"pipeline": "cosmx_minimal", "version": "0.1.0"}

    if min_transcripts > 0 or min_genes > 0:
        adata = adata[
            (adata.obs["n_transcripts"] >= min_transcripts)
            & (adata.obs["n_genes"] >= min_genes)
        ].copy()

    return adata


def build_spatialdata_from_adata(adata: ad.AnnData) -> SpatialData:
    """Build a SpatialData from a cell-level AnnData."""
    if "spatial" not in adata.obsm:
        raise KeyError("No 'spatial' in adata.obsm")
    coords = adata.obsm["spatial"]

    points_frame = pd.DataFrame(
        {"x": coords[:, 0], "y": coords[:, 1], "cell_id": adata.obs_names.to_numpy()},
        index=adata.obs_names,
    )
    points = PointsModel.parse(points_frame)
    table = adata.copy()
    sanitize_table(table)

    sdata = SpatialData(
        points={"cell_centroids": points},
        tables={KEY_MAIN_TABLE: table},
    )
    sdata.attrs["main_table_key"] = KEY_MAIN_TABLE
    return sdata


# ── Legacy backward-compat functions ─────────────────────────────────
# These preserve the OLD CosMx-native column names (target, cell,
# x_global_px, y_global_px) for backward compatibility with existing
# step modules.  Phase 1 will migrate all steps to canonical names.


def load_cosmx_transcripts(path: str | Path) -> pd.DataFrame:
    """Legacy: load CosMx CSV, return CANONICAL column names."""
    resolved = Path(path)
    df = pd.read_csv(resolved)
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    # Map to canonical columns
    ingestor = CosMxIngestor()
    df = ingestor._standardise_columns(df)
    return df


def summarize_cosmx_transcripts(df: pd.DataFrame, source_path: str | Path) -> DatasetSummary:
    """Legacy: summarize a transcript DataFrame (any column scheme)."""
    from ..constants import COL_CELL_ID, COL_GENE, COL_FOV, COL_CELLCOMP, resolve_col, resolve_col_strict
    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)
    gene_col = resolve_col_strict(df.columns, COL_GENE)
    fov_col = resolve_col(df.columns, COL_FOV)
    cc_col = resolve_col(df.columns, COL_CELLCOMP)
    n_cells_unique = df[cell_col].dropna().nunique()
    extra: dict[str, Any] = {"cell_id_unique": n_cells_unique}
    if cc_col:
        comp_counts = df[cc_col].value_counts(dropna=False)
        total = int(comp_counts.sum())
        if total:
            extra["nuclear_fraction"] = round(float(comp_counts.get("Nuclear", 0)) / total, 4)
            extra["cytoplasm_fraction"] = round(float(comp_counts.get("Cytoplasm", 0)) / total, 4)
    return DatasetSummary(
        source_path=Path(source_path),
        n_transcripts=len(df),
        n_cells=df[cell_col].dropna().nunique(),
        n_genes=df[gene_col].nunique(),
        n_fovs=df[fov_col].nunique() if fov_col else 1,
        extra=extra,
    )


# ── Ingestor ─────────────────────────────────────────────────────────


@register_ingestor(PLATFORM_COSMX)
class CosMxIngestor(BaseIngestor):
    """Ingestor for NanoString CosMx Spatial Molecular Imager data.

    Expected input: CSV with columns ``fov, cell_ID, x_global_px,
    y_global_px, target, CellComp, cell``.
    """

    platform: str = PLATFORM_COSMX

    def _parse_transcripts(self, input_path: str | Path) -> pd.DataFrame:
        resolved = self._resolve_path(input_path)
        df = pd.read_csv(resolved)
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])
        self._validate_raw_columns(df, {"x_global_px", "y_global_px", "target"})
        return df

    def _column_mapping(self) -> list[tuple[str, str]]:
        return [
            ("x_global_px", COL_X),
            ("y_global_px", COL_Y),
            ("target", COL_GENE),
            ("cell", COL_CELL_ID),
            ("fov", COL_FOV),
            ("CellComp", COL_CELLCOMP),
        ]

