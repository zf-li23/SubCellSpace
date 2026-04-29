from __future__ import annotations

import json

from src.models import PipelineResult
from src.pipeline import run_cosmx_minimal


class TestRunCosmxMinimal:
    def test_run_with_csv(self, sample_transcripts_csv, tmp_path):
        output_dir = tmp_path / "run_output"
        result = run_cosmx_minimal(
            input_csv=sample_transcripts_csv,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
        )
        assert isinstance(result, PipelineResult)
        assert result.adata is not None
        assert result.summary is not None
        assert result.adata_path.exists()
        assert result.report_path.exists()

    def test_report_is_valid_json(self, sample_transcripts_csv, tmp_path):
        output_dir = tmp_path / "report_test"
        result = run_cosmx_minimal(
            input_csv=sample_transcripts_csv,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
        )
        report = json.loads(result.report_path.read_text())
        assert "outputs" in report
        assert "summary" in report
        assert "layer_evaluation" in report
        assert "step_summary" in report

    def test_outputs_h5ad_and_json(self, sample_transcripts_csv, tmp_path):
        output_dir = tmp_path / "outputs_test"
        result = run_cosmx_minimal(
            input_csv=sample_transcripts_csv,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
        )
        assert result.adata_path.suffix == ".h5ad"
        assert result.report_path.suffix == ".json"

    def test_min_transcripts_threshold(self, sample_transcripts_df, tmp_path):
        # Write a small CSV
        csv_path = tmp_path / "small.csv"
        sample_transcripts_df.to_csv(csv_path, index=False)
        output_dir = tmp_path / "threshold_test"
        result = run_cosmx_minimal(
            input_csv=str(csv_path),
            output_dir=output_dir,
            min_transcripts=1,
            min_genes=0,
        )
        # Should still succeed since we have data
        assert result.adata.n_obs > 0

    def test_backend_strings_accepted(self, sample_transcripts_csv, tmp_path):
        output_dir = tmp_path / "backend_test"
        result = run_cosmx_minimal(
            input_csv=sample_transcripts_csv,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
            denoise_backend="intracellular",
            segmentation_backend="provided_cells",
            clustering_backend="leiden",
            annotation_backend="rank_marker",
            spatial_domain_backend="spatial_leiden",
        )
        assert result is not None
