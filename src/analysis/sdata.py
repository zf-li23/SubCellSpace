"""Image-free SpatialData for SOPA.

SOPA treats an image as mandatory (``sopa.io.standardize.sanity_check``). For imaging data the cell × gene matrix
and transcripts already carry the information the analysis needs, so GEO uploads without images are built here
into SpatialData objects that SOPA's transcript/shape functions (aggregate, assign_transcript_to_cell,
transcript-based segmentation) accept directly.
"""

from __future__ import annotations

import anndata as ad
import geopandas as gpd
import pandas as pd

TRANSCRIPTS_KEY = "transcripts"
BOUNDARIES_KEY = "cell_boundaries"
TABLE_KEY = "table"


def to_sopa_sdata(
    transcripts: pd.DataFrame | None = None,
    boundaries: gpd.GeoDataFrame | None = None,
    table: ad.AnnData | None = None,
    npartitions: int = 4,
):
    """Build a SpatialData with the element keys and ``attrs`` SOPA looks up (coordinates in µm, identity transform)."""
    import dask.dataframe as dd
    from sopa.constants import SopaAttrs
    from spatialdata import SpatialData
    from spatialdata.models import PointsModel, ShapesModel, TableModel

    points, shapes, tables = {}, {}, {}
    if transcripts is not None:
        pts = transcripts[["x", "y", "gene"]].reset_index(drop=True).astype({"gene": "category"})
        points[TRANSCRIPTS_KEY] = PointsModel.parse(dd.from_pandas(pts, npartitions=npartitions), feature_key="gene")
    if boundaries is not None:
        shapes[BOUNDARIES_KEY] = ShapesModel.parse(boundaries)
    if table is not None:
        tables[TABLE_KEY] = TableModel.parse(table)
    sdata = SpatialData(points=points, shapes=shapes, tables=tables)
    if points:
        sdata.attrs[SopaAttrs.TRANSCRIPTS] = TRANSCRIPTS_KEY
    if shapes:
        sdata.attrs[SopaAttrs.BOUNDARIES] = BOUNDARIES_KEY
    return sdata
