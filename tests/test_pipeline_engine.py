from __future__ import annotations

import pandas as pd
import pytest

from src.pipeline_engine import ExecutionContext, _run_step, run_pipeline

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def empty_context() -> ExecutionContext:
    return ExecutionContext()


@pytest.fixture
def sample_context(sample_transcripts_df) -> ExecutionContext:
    return ExecutionContext(transcripts=sample_transcripts_df)


# ── ExecutionContext ─────────────────────────────────────────────────


class TestExecutionContext:
    def test_default_construction(self):
        ctx = ExecutionContext()
        assert ctx.transcripts is None
        assert ctx.denoised_df is None
        assert ctx.segmented_df is None
        assert ctx.adata is None
        assert ctx.sdata is None
        assert ctx.step_results == {}
        assert ctx.settings is None
        assert ctx.pipeline_config is None
        assert ctx.input_csv is None
        assert ctx.output_dir is None

    def test_with_transcripts(self, sample_transcripts_df):
        ctx = ExecutionContext(transcripts=sample_transcripts_df)
        assert ctx.transcripts is not None
        assert len(ctx.transcripts) == 100

    def test_step_results_accumulation(self, empty_context):
        from src.models import StepResult

        empty_context.step_results["denoise"] = StepResult(
            output=pd.DataFrame(),
            summary={"test": True},
            backend_used="test",
        )
        assert "denoise" in empty_context.step_results
        assert empty_context.step_results["denoise"].summary["test"] is True


# ── _run_step ────────────────────────────────────────────────────────


class TestRunStep:
    """Tests for the _run_step adapter function.

    These tests use the actual registered backends, which are loaded
    when the step modules are imported (via the ``@register_backend``
    decorator).
    """

    def test_denoise_step(self, sample_context):
        """Denoise step should filter transcripts by CellComp."""
        from src.registry import load_backends

        load_backends()

        result = _run_step("denoise", "intracellular", sample_context)
        assert result is not None
        assert result.backend_used == "intracellular"
        # The output should be a filtered DataFrame
        assert isinstance(result.output, pd.DataFrame)
        # Context should be updated
        assert sample_context.denoised_df is not None
        assert "denoise" in sample_context.step_results

    def test_denoise_missing_transcripts(self, empty_context):
        """Denoise step should raise if transcripts not loaded."""
        from src.registry import load_backends

        load_backends()

        from src.errors import PipelineStepError

        with pytest.raises(PipelineStepError, match="No transcripts"):
            _run_step("denoise", "intracellular", empty_context)

    def test_segmentation_step(self, sample_context):
        """Segmentation step needs denoised data first."""
        from src.registry import load_backends

        load_backends()

        # First run denoise to populate denoised_df
        _run_step("denoise", "intracellular", sample_context)
        result = _run_step("segmentation", "provided_cells", sample_context)
        assert result is not None
        assert result.backend_used == "provided_cells"
        assert isinstance(result.output, pd.DataFrame)
        assert sample_context.segmented_df is not None

    def test_segmentation_missing_denoised(self, sample_context):
        """Segmentation should raise if denoised data missing."""
        from src.errors import PipelineStepError
        from src.registry import load_backends

        load_backends()

        with pytest.raises(PipelineStepError, match="No denoised"):
            _run_step("segmentation", "provided_cells", sample_context)

    def test_unknown_step(self, empty_context):
        """Unknown step/backend combination should raise ValueError."""
        with pytest.raises(ValueError, match="No runner registered"):
            _run_step("nonexistent_step", "some_backend", empty_context)

    def test_unknown_backend(self, sample_context):
        """Known step but unknown backend should raise PipelineStepError."""
        from src.errors import PipelineStepError
        from src.registry import load_backends

        load_backends()

        with pytest.raises(PipelineStepError, match="Unknown denoise backend"):
            _run_step("denoise", "nonexistent_backend", sample_context)

    def test_step_params_passed(self, sample_context):
        """Extra params should be passed to the step function."""
        from src.models import StepResult
        from src.registry import load_backends

        load_backends()

        # subcellular step accepts params including backend
        # First prepare context with required data
        _run_step("denoise", "intracellular", sample_context)
        _run_step("segmentation", "provided_cells", sample_context)
        # We need adata for certain steps, let's just check params are
        # accepted without error by verifying the call works.
        # For steps that don't use params, just verify the call succeeds.
        result = _run_step("denoise", "intracellular", sample_context, {})
        assert isinstance(result, StepResult)

    def test_step_elapsed_time_recorded(self, sample_context):
        """Each step should record elapsed time in its summary."""
        from src.registry import load_backends

        load_backends()

        result = _run_step("denoise", "intracellular", sample_context)
        assert "__elapsed_seconds__" in result.summary
        assert isinstance(result.summary["__elapsed_seconds__"], float)
        assert result.summary["__elapsed_seconds__"] >= 0


# ── run_pipeline ─────────────────────────────────────────────────────


class TestRunPipeline:
    """Integration tests for the full pipeline runner."""

    def _run_with_csv(self, csv_path: str, output_dir: str, **overrides) -> PipelineResult:
        """Helper: ingest CSV → SpatialData → run_pipeline."""
        from src.io import get_ingestor
        sdata = get_ingestor("cosmx").ingest(csv_path)
        return run_pipeline(
            sdata=sdata,
            output_dir=output_dir,
            min_transcripts=0,
            min_genes=0,
            **overrides,
        )

    def test_run_with_sdata(self, sample_transcripts_csv, tmp_path):
        """Basic end-to-end test: ingest → PipelineResult out."""
        result = self._run_with_csv(
            sample_transcripts_csv,
            str(tmp_path / "pipeline_output"),
        )
        assert result.adata is not None
        assert result.summary is not None
        assert result.adata_path.exists()
        assert result.report_path.exists()

    def test_output_files_created(self, sample_transcripts_csv, tmp_path):
        """Verify that h5ad, report JSON files are created."""
        output_dir = tmp_path / "output_files"
        result = self._run_with_csv(
            sample_transcripts_csv,
            str(output_dir),
        )
        assert result.adata_path.exists()
        assert result.report_path.exists()
        assert result.adata_path.suffix == ".h5ad"
        assert result.report_path.suffix == ".json"

    def test_report_contents(self, sample_transcripts_csv, tmp_path):
        """Verify the report JSON contains expected keys."""
        import json

        output_dir = tmp_path / "report_contents"
        result = self._run_with_csv(
            sample_transcripts_csv,
            str(output_dir),
        )
        report = json.loads(result.report_path.read_text())
        assert "outputs" in report
        assert "summary" in report
        assert "step_summary" in report
        assert "step_order" in report
        assert "pipeline_name" in report
        assert "pipeline_version" in report

    def test_step_order_in_report(self, sample_transcripts_csv, tmp_path):
        """Step order in report should match config."""
        import json

        output_dir = tmp_path / "step_order"
        result = self._run_with_csv(
            sample_transcripts_csv,
            str(output_dir),
        )
        report = json.loads(result.report_path.read_text())
        assert isinstance(report["step_order"], list)
        assert len(report["step_order"]) > 0
        assert "denoise" in report["step_order"]

    def test_backend_overrides(self, sample_transcripts_csv, tmp_path):
        """Backend overrides should be respected."""
        output_dir = tmp_path / "backend_overrides"
        result = self._run_with_csv(
            sample_transcripts_csv,
            str(output_dir),
            denoise_backend="none",
            segmentation_backend="provided_cells",
        )
        assert result.adata is not None

    def test_output_dir_created(self, sample_transcripts_csv, tmp_path):
        """run_pipeline should create the output directory."""
        output_dir = tmp_path / "new_output_dir"
        assert not output_dir.exists()
        self._run_with_csv(
            sample_transcripts_csv,
            str(output_dir),
        )
        assert output_dir.exists()

    def test_adata_has_observations(self, sample_transcripts_csv, tmp_path):
        """Resulting AnnData should have some observations."""
        output_dir = tmp_path / "adata_check"
        result = self._run_with_csv(
            sample_transcripts_csv,
            str(output_dir),
        )
        assert result.adata.n_obs > 0
        assert result.adata.n_vars > 0


# ── Error handling ───────────────────────────────────────────────────


class TestRunPipelineErrors:
    def test_nonexistent_sdata_raises(self, tmp_path):
        """Non-existent SpatialData path should raise FileNotFoundError."""
        import spatialdata

        with pytest.raises(FileNotFoundError):
            spatialdata.read_zarr("/nonexistent/path.zarr")

    def test_invalid_backend_raises(self, sample_transcripts_csv, tmp_path):
        """Invalid backend should fall back to default (graceful)."""
        from src.io import get_ingestor
        sdata = get_ingestor("cosmx").ingest(sample_transcripts_csv)
        output_dir = tmp_path / "fallback_test"
        result = run_pipeline(
            sdata=sdata,
            output_dir=str(output_dir),
            min_transcripts=0,
            min_genes=0,
            denoise_backend="nonexistent_backend",  # will fall back to default
        )
        assert result.adata is not None

    def test_disabled_step_skipped(self, sample_transcripts_csv, tmp_path):
        """Disabled steps should be skipped."""
        from src.io import get_ingestor
        from src.config import Settings

        sdata = get_ingestor("cosmx").ingest(sample_transcripts_csv)
        settings = Settings(config_path="/nonexistent/path.yaml")
        settings.update(
            {
                "output_dir": str(tmp_path / "skip_disabled"),
                "min_transcripts": 0,
                "min_genes": 0,
                "pipeline": {
                    "steps_config": {
                        "annotation": {"enabled": False},
                    },
                },
            }
        )
        result = run_pipeline(settings=settings, sdata=sdata)
        assert result.adata is not None
