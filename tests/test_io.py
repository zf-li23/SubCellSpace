from __future__ import annotations

import pytest

from src.io.base import DataValidationError
from src.io.cosmx import (
    REQUIRED_COLUMNS,
    build_cell_level_adata,
    build_spatialdata,
    load_cosmx_transcripts,
    summarize_cosmx_transcripts,
)
from src.models import DatasetSummary


class TestLoadCosmxTranscripts:
    def test_load_valid_csv(self, sample_transcripts_csv):
        df = load_cosmx_transcripts(sample_transcripts_csv)
        assert len(df) > 0
        for col in REQUIRED_COLUMNS:
            assert col in df.columns

    def test_missing_columns_raises_error(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("x,y,z\n1,2,3\n")
        with pytest.raises(DataValidationError, match="Missing required columns"):
            load_cosmx_transcripts(str(bad_csv))

    def test_strips_unnamed_column(self, sample_transcripts_df, tmp_path):
        csv_path = tmp_path / "with_unnamed.csv"
        sample_transcripts_df.to_csv(csv_path)
        # Write with Unnamed: 0 column by using a saved CSV that includes the default index
        df = load_cosmx_transcripts(str(csv_path))
        assert "Unnamed: 0" not in df.columns

    def test_unnamed_0_dropped(self, tmp_path, sample_transcripts_df):
        # Create a file that has "Unnamed: 0" as a column header
        csv_path = tmp_path / "unnamed_test.csv"
        sample_transcripts_df.to_csv(csv_path)
        # The pandas default to_csv may already include index. Let's just test that load handles it.
        df = load_cosmx_transcripts(str(csv_path))
        assert "Unnamed: 0" not in df.columns


class TestSummarizeCosmxTranscripts:
    def test_returns_dataset_summary(self, sample_transcripts_csv):
        summary = summarize_cosmx_transcripts(load_cosmx_transcripts(sample_transcripts_csv), sample_transcripts_csv)
        assert isinstance(summary, DatasetSummary)
        assert summary.n_transcripts > 0
        assert summary.n_cells > 0
        assert summary.n_genes > 0
        assert summary.n_fovs > 0

    def test_extra_fields(self, sample_transcripts_df, tmp_path):
        csv_path = tmp_path / "extra_test.csv"
        sample_transcripts_df.to_csv(csv_path, index=False)
        summary = summarize_cosmx_transcripts(sample_transcripts_df, csv_path)
        assert "cell_id_unique" in summary.extra
        assert "nuclear_fraction" in summary.extra


class TestBuildCellLevelAdata:
    def test_build_from_transcripts(self, sample_transcripts_df):
        adata = build_cell_level_adata(sample_transcripts_df)
        assert adata.n_obs > 0
        assert adata.n_vars > 0
        assert "spatial" in adata.obsm
        assert adata.obsm["spatial"].shape[1] == 2
        assert "counts" in adata.layers
        assert "cosmx" in adata.uns

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
        sdata = build_spatialdata(sample_anndata)
        assert "cells" in sdata.points
        assert "cosmx_table" in sdata.tables
