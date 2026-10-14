"""Standardised in-memory view of one GEO sample.

Every reader returns a :class:`Sample` with the same conventions, whatever the platform:

- coordinates in **µm**;
- ``cell_id`` is a string, ``None`` for transcripts outside any cell;
- control / blank / negative probes are flagged in ``transcripts["is_control"]`` and dropped from ``matrix``;
- ``sources`` records which raw file each element came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import anndata as ad
import geopandas as gpd
import pandas as pd
import sopa

TX_COLUMNS = ("x", "y", "gene", "cell_id")  # required transcript columns (``z``, ``qv`` optional)


@dataclass
class Sample:
    platform: str
    sample_dir: Path
    transcripts: pd.DataFrame | None = None   # x, y, [z], gene, cell_id, is_control, [qv, fov]
    matrix: ad.AnnData | None = None          # vendor cells × genes counts (obs_names = cell_id)
    cells: pd.DataFrame | None = None         # index cell_id; x, y [, area] in µm
    boundaries: gpd.GeoDataFrame | None = None  # index cell_id
    nuclei: gpd.GeoDataFrame | None = None
    annotations: pd.DataFrame | None = None   # author labels, index cell_id
    sources: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def has_cell_ids(self) -> bool:
        return self.transcripts is not None and self.transcripts["cell_id"].notna().any()


def is_control_name(names: pd.Series | pd.Index) -> pd.Series:
    """Same rule SOPA uses to drop control/blank/negative probes before counting."""
    return pd.Series(names, dtype="string").str.match(sopa.settings.gene_exclude_pattern, case=False, na=True).to_numpy()


def drop_control_genes(adata: ad.AnnData) -> ad.AnnData:
    keep = ~is_control_name(adata.var_names)
    return adata[:, keep].copy()
