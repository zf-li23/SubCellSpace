"""Transcript → cell assignment and aggregation.

``assign_to_boundaries`` follows SOPA's ``sopa.spatial.join._get_cell_id`` (geopandas point-in-polygon join,
first matching cell kept, processed in partitions). Unlike ``sopa.aggregate``, which counts a transcript once per
polygon containing it, each transcript is counted for the single cell it is assigned to, so the matrix and the
transcripts' ``cell_id`` always agree. Cells without transcripts are kept as all-zero rows, as in SOPA.
"""

from __future__ import annotations

import anndata as ad
import geopandas as gpd
import numpy as np
import pandas as pd
import scipy.sparse as sp

PARTITION_ROWS = 2_000_000  # transcripts per spatial-join partition (bounds memory, like SOPA's dask partitions)


def count_by_cell_id(tx: pd.DataFrame) -> ad.AnnData:
    """Cells × genes counts from transcripts that carry a cell_id (a groupby, no spatial step)."""
    tx = tx[tx["cell_id"].notna()]
    cells = pd.Categorical(tx["cell_id"]).remove_unused_categories()
    genes = pd.Categorical(tx["gene"]).remove_unused_categories()
    X = sp.csr_matrix(
        (np.ones(len(tx), dtype=np.float32), (cells.codes, genes.codes)),
        shape=(len(cells.categories), len(genes.categories)),
    )
    X.sum_duplicates()
    adata = ad.AnnData(X)
    adata.obs_names = cells.categories.astype(str)
    adata.var_names = genes.categories.astype(str)
    return adata


def assign_to_boundaries(x: np.ndarray, y: np.ndarray, boundaries: gpd.GeoDataFrame,
                         partition_rows: int = PARTITION_ROWS) -> np.ndarray:
    """Cell id (index of ``boundaries``) for each point, ``None`` outside every cell; first match wins."""
    cells = gpd.GeoDataFrame({"cell_id": boundaries.index.astype(str)}, geometry=boundaries.geometry.to_numpy())
    out = np.full(len(x), None, dtype=object)
    for start in range(0, len(x), partition_rows):
        stop = min(start + partition_rows, len(x))
        points = gpd.GeoDataFrame(geometry=gpd.points_from_xy(x[start:stop], y[start:stop]))
        joined = points.sjoin(cells, how="left")
        joined = joined[~joined.index.duplicated(keep="first")]
        ids = joined["cell_id"].to_numpy(dtype=object)
        out[start:stop] = np.where(pd.isna(ids), None, ids)
    return out


def count_with_boundaries(tx: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> tuple[ad.AnnData, pd.Series]:
    """Assign transcripts to vendor boundaries, then count per cell (all boundary cells kept as rows)."""
    assigned = pd.Series(assign_to_boundaries(tx["x"].to_numpy(float), tx["y"].to_numpy(float), boundaries),
                         index=tx.index)
    counted = count_by_cell_id(tx.assign(cell_id=assigned))
    all_cells = pd.Index(boundaries.index.astype(str))
    rows = pd.Index(counted.obs_names).get_indexer(all_cells)
    X = sp.vstack([counted.X, sp.csr_matrix((1, counted.n_vars), dtype=np.float32)]).tocsr()[np.where(rows < 0, counted.n_obs, rows)]
    adata = ad.AnnData(X, var=pd.DataFrame(index=counted.var_names))
    adata.obs_names = all_cells
    return adata, assigned
