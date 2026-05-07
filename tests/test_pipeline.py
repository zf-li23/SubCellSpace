from __future__ import annotations

import json

import pytest

from src.io import ingest
from src.models import PipelineResult
from src.pipeline_engine import run_pipeline


@pytest.fixture
def sample_sdata(sample_transcripts_csv, tmp_path):
    """Ingest sample CosMx data → SpatialData for pipeline tests."""
    return ingest("cosmx", sample_transcripts_csv)


class TestRunPipeline:
    def test_run_with_sdata(self, sample_sdata, tmp_path):
        output_dir = tmp_path / "run_output"
        result = run_pipeline(
            sdata=sample_sdata,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
            denoise_backend="intracellular",
        )
        assert isinstance(result, PipelineResult)
        assert result.adata is not None
        assert result.summary is not None
        assert result.adata_path.exists()
        assert result.report_path.exists()

    def test_report_is_valid_json(self, sample_sdata, tmp_path):
        output_dir = tmp_path / "report_test"
        result = run_pipeline(
            sdata=sample_sdata,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
            denoise_backend="intracellular",
        )
        report = json.loads(result.report_path.read_text())
        assert "outputs" in report
        assert "summary" in report
        assert "layer_evaluation" in report
        assert "step_summary" in report

    def test_outputs_h5ad_and_json(self, sample_sdata, tmp_path):
        output_dir = tmp_path / "outputs_test"
        result = run_pipeline(
            sdata=sample_sdata,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
            denoise_backend="intracellular",
        )
        assert result.adata_path.suffix == ".h5ad"
        assert result.report_path.suffix == ".json"

    def test_min_transcripts_threshold(self, sample_sdata, tmp_path):
        output_dir = tmp_path / "threshold_test"
        result = run_pipeline(
            sdata=sample_sdata,
            output_dir=output_dir,
            min_transcripts=1,
            min_genes=0,
        )
        assert result.adata.n_obs > 0

    def test_backend_strings_accepted(self, sample_sdata, tmp_path):
        output_dir = tmp_path / "backend_test"
        result = run_pipeline(
            sdata=sample_sdata,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
            denoise_backend="intracellular",
            segmentation_backend="provided_cells",
            clustering_backend="leiden",
            annotation_backend="rank_marker",
            spatial_domain_backend="spatial_leiden",
            subcellular_spatial_domain_backend="none",
        )
        assert result is not None

    def test_cli_alias_backends_accepted(self, sample_sdata, tmp_path):
        """Verify all CLI alias names (e.g. clustering_backend, subcellular_domain_backend) are properly mapped."""
        output_dir = tmp_path / "alias_test"
        result = run_pipeline(
            sdata=sample_sdata,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
            denoise_backend="intracellular",
            segmentation_backend="provided_cells",
            clustering_backend="kmeans",
            annotation_backend="cluster_label",  # avoids rank_marker crash on singleton clusters
            spatial_domain_backend="spatial_kmeans",
            subcellular_domain_backend="none",
            spatial_analysis_backend="squidpy",
        )
        assert result is not None
        assert result.adata is not None
        assert result.adata_path.exists()
        assert result.report_path.exists()
