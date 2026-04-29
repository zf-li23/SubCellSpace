from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.validation import (
    ANALYSIS_REQUIRED_OBSM,
    ANNOTATION_REQUIRED_OBS,
    DENOISE_REQUIRED_COLUMNS,
    validate_analysis_input,
    validate_anndata_obs,
    validate_anndata_obsm,
    validate_annotation_input,
    validate_dataframe,
    validate_denoise_input,
    validate_file_exists,
    validate_non_empty,
    validate_run_input,
    validate_segmentation_input,
    validate_subcellular_input,
)


class TestValidateDataFrame:
    def test_valid_dataframe(self):
        df = pd.DataFrame({"CellComp": ["Nuclear"], "extra_col": [1]})
        msgs = validate_dataframe(df, DENOISE_REQUIRED_COLUMNS, "test")
        assert len(msgs) == 0

    def test_missing_columns(self):
        df = pd.DataFrame({"wrong_col": [1]})
        msgs = validate_dataframe(df, DENOISE_REQUIRED_COLUMNS, "test")
        assert len(msgs) == 1
        assert "missing required columns" in msgs[0]
        assert "CellComp" in msgs[0]


class TestValidateAnnDataObs:
    def test_valid_obs(self, sample_anndata):
        msgs = validate_anndata_obs(sample_anndata, ANNOTATION_REQUIRED_OBS, "test")
        assert len(msgs) == 0

    def test_missing_obs(self, sample_anndata):
        df = sample_anndata.obs.drop(columns=["cluster"])
        sample_anndata.obs = df
        msgs = validate_anndata_obs(sample_anndata, ANNOTATION_REQUIRED_OBS, "test")
        assert len(msgs) == 1
        assert "cluster" in msgs[0]


class TestValidateAnnDataObsm:
    def test_valid_obsm(self, sample_anndata):
        msgs = validate_anndata_obsm(sample_anndata, ANALYSIS_REQUIRED_OBSM, "test")
        assert len(msgs) == 0

    def test_missing_obsm(self, sample_anndata):
        del sample_anndata.obsm["X_pca"]
        msgs = validate_anndata_obsm(sample_anndata, ANALYSIS_REQUIRED_OBSM, "test")
        assert len(msgs) == 1
        assert "X_pca" in msgs[0]


class TestValidateNonEmpty:
    def test_non_empty(self):
        df = pd.DataFrame({"a": [1]})
        assert validate_non_empty(df) == []

    def test_empty(self):
        df = pd.DataFrame()
        msgs = validate_non_empty(df)
        assert len(msgs) == 1
        assert "empty" in msgs[0]


class TestValidateFileExists:
    def test_exists(self, tmp_path):
        p = tmp_path / "test.csv"
        p.write_text("a,b\n1,2")
        assert validate_file_exists(p) == []

    def test_not_exists(self):
        msgs = validate_file_exists(Path("/nonexistent/file.csv"))
        assert len(msgs) == 1
        assert "not found" in msgs[0]


class TestValidateDenoiseInput:
    def test_valid(self):
        df = pd.DataFrame({"CellComp": ["Nuclear"], "x": [1]})
        assert validate_denoise_input(df) == []

    def test_missing_column(self):
        df = pd.DataFrame({"x": [1]})
        msgs = validate_denoise_input(df)
        assert len(msgs) == 1

    def test_empty(self):
        df = pd.DataFrame({"CellComp": []})
        msgs = validate_denoise_input(df)
        assert len(msgs) >= 1


class TestValidateSegmentationInput:
    def test_valid(self):
        df = pd.DataFrame({"cell": ["a"], "fov": [1], "cell_ID": [1]})
        assert validate_segmentation_input(df) == []

    def test_missing_columns(self):
        df = pd.DataFrame({"cell": ["a"]})
        msgs = validate_segmentation_input(df)
        assert len(msgs) == 1
        assert "fov" in msgs[0] or "cell_ID" in msgs[0]


class TestValidateSubcellularInput:
    def test_valid(self):
        df = pd.DataFrame({"cell": ["a"], "x_global_px": [1.0], "y_global_px": [2.0]})
        assert validate_subcellular_input(df) == []

    def test_missing_columns(self):
        df = pd.DataFrame({"cell": ["a"]})
        msgs = validate_subcellular_input(df)
        assert len(msgs) == 1


class TestValidateAnalysisInput:
    def test_valid(self, sample_anndata):
        assert validate_analysis_input(sample_anndata) == []

    def test_missing_obsm(self, sample_anndata):
        del sample_anndata.obsm["X_pca"]
        msgs = validate_analysis_input(sample_anndata)
        assert len(msgs) > 0


class TestValidateAnnotationInput:
    def test_valid(self, sample_anndata):
        assert validate_annotation_input(sample_anndata) == []

    def test_missing_obs(self, sample_anndata):
        del sample_anndata.obs["cluster"]
        msgs = validate_annotation_input(sample_anndata)
        assert len(msgs) > 0


class TestValidateRunInput:
    def test_valid(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("a,b\n1,2")
        msgs = validate_run_input(
            input_csv=str(csv_path),
            output_dir=str(tmp_path),
            min_transcripts=10,
            min_genes=5,
        )
        assert len(msgs) == 0

    def test_file_not_found(self):
        msgs = validate_run_input(
            input_csv="/nonexistent.csv",
            output_dir="/tmp",
            min_transcripts=10,
            min_genes=5,
        )
        assert len(msgs) >= 1
        assert any("not found" in m for m in msgs)

    def test_negative_values(self):
        msgs = validate_run_input(
            input_csv="/tmp/test.csv",
            output_dir="/tmp",
            min_transcripts=-1,
            min_genes=-2,
        )
        # file not found + negative values (2 or 3 messages depending on order)
        assert len(msgs) >= 2
