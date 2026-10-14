"""Transcript → cell aggregation.

``count_by_cell_id`` covers what SOPA has no entry point for: transcripts that already carry a vendor cell_id but
no boundaries (``sopa.aggregate`` always needs shapes). ``count_with_boundaries`` uses SOPA as-is.
"""

from __future__ import annotations

import anndata as ad
import geopandas as gpd
import numpy as np
import pandas as pd
import scipy.sparse as sp

from .sdata import to_sopa_sdata


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


def count_with_boundaries(tx: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> tuple[ad.AnnData, pd.Series]:
    """Assign transcripts to vendor boundaries and count them with SOPA (dask point-in-polygon join)."""
    import sopa

    shapes = boundaries.reset_index()
    sdata = to_sopa_sdata(transcripts=tx, boundaries=shapes)

    sopa.spatial.assign_transcript_to_cell(sdata, "transcripts", "cell_boundaries", key_added="cell_index")
    index = sdata["transcripts"]["cell_index"].compute().to_numpy()
    assigned = pd.Series(
        np.where(pd.notna(index), shapes["cell_id"].to_numpy()[np.nan_to_num(index, nan=0).astype(int)], None),
        index=tx.index,
    )

    sopa.aggregate(sdata, aggregate_channels=False, points_key="transcripts", shapes_key="cell_boundaries", gene_column="gene")
    table = sdata["table"]
    adata = ad.AnnData(sp.csr_matrix(table.X), var=pd.DataFrame(index=table.var_names.astype(str)))
    # SOPA renames cells positionally (row i of the table == row i of the shapes); nothing is filtered here
    assert table.n_obs == len(shapes), "sopa.aggregate dropped cells unexpectedly"
    adata.obs_names = shapes["cell_id"].astype(str).to_numpy()
    return adata, assigned
