from __future__ import annotations

import pytest

from src.constants import REQUIRED_CANONICAL_COLUMNS
from src.io.base import DataValidationError
from src.io.cosmx import (
    build_cell_level_adata,
    build_spatialdata_from_adata,
)
from src.io import ingest, detect_platform


class TestDetectPlatform:
    def test_detect_cosmx_csv(self, sample_transcripts_csv):
        platform = detect_platform(sample_transcripts_csv)
        assert platform == "cosmx"


class TestIngest:
    def test_ingest_cosmx_csv(self, sample_transcripts_csv):
        sdata = ingest("cosmx", sample_transcripts_csv)
        assert "raw_transcripts" in sdata.points
        pts = sdata.points["raw_transcripts"].compute()
        for col in REQUIRED_CANONICAL_COLUMNS:
            assert col in pts.columns

    def test_ingest_summary_attrs(self, sample_transcripts_csv):
        sdata = ingest("cosmx", sample_transcripts_csv)
        summary = sdata.attrs.get("ingestion_summary", {})
        assert summary.get("n_transcripts", 0) > 0
        assert summary.get("n_cells", 0) > 0
        assert summary.get("n_genes", 0) > 0


class TestBuildCellLevelAdata:
    def test_build_from_transcripts(self, sample_transcripts_df):
        adata = build_cell_level_adata(sample_transcripts_df)
        assert adata.n_obs > 0
        assert adata.n_vars > 0
        assert "spatial" in adata.obsm
        assert adata.obsm["spatial"].shape[1] == 2
        assert "counts" in adata.layers

    def test_all_cells_in_obs(self, sample_transcripts_df):
        adata = build_cell_level_adata(sample_transcripts_df)
        unique_cells = sample_transcripts_df["cell"].astype(str).unique()
        assert set(adata.obs_names) == set(unique_cells)

    def test_counts_match(self, sample_transcripts_df):
        """Verify that the count matrix correctly tallies transcript counts."""
        adata = build_cell_level_adata(sample_transcripts_df)
        for cell in adata.obs_names[:5]:
            expected = (sample_transcripts_df["cell"].astype(str) == cell).sum()
            total = adata[cell, :].X.sum()
            assert total == expected


class TestBuildSpatialdata:
    def test_build_from_anndata(self, sample_anndata):
        sdata = build_spatialdata_from_adata(sample_anndata)
        assert "cell_centroids" in sdata.points
        assert "table" in sdata.tables
