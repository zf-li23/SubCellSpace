from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

import numpy as np
import pandas as pd
import pytest

from src.models import StepResult
from src.steps.segmentation import _CELLPOSE_AVAILABLE, assign_cells

# ═══════════════════════════════════════════════════════════════════════
# Existing tests (preserved and extended)
# ═══════════════════════════════════════════════════════════════════════


class TestAssignCells:
    def test_backend_provided_cells(self, sample_transcripts_df):
        result = assign_cells(sample_transcripts_df, "provided_cells")
        assigned = result.output
        summary = result.summary
        assert len(assigned) > 0
        assert summary["segmentation_backend"] == "provided_cells"
        assert summary["n_transcripts_assigned"] == len(assigned)
        assert summary["n_cells_assigned"] > 0

    def test_backend_fov_cell_id(self, sample_transcripts_df):
        # Create df without a cell column to test fov_cell_id backend
        # resolve_col_strict will find cell_ID via legacy alias
        df_no_cell = sample_transcripts_df.drop(columns=["cell"])
        result = assign_cells(df_no_cell, "fov_cell_id")
        assigned = result.output
        summary = result.summary
        assert summary["segmentation_backend"] == "fov_cell_id"
        # Column name is the resolved column (cell_ID via alias)
        from src.constants import resolve_col_strict, COL_CELL_ID
        cell_col = resolve_col_strict(df_no_cell.columns, COL_CELL_ID)
        assert cell_col in assigned.columns
        expected_cell = f"{df_no_cell['fov'].iloc[0]}_{df_no_cell[cell_col].iloc[0]}"
        assert assigned[cell_col].iloc[0] == expected_cell

    def test_unknown_backend_raises(self, sample_transcripts_df):
        with pytest.raises(ValueError, match="Unknown segmentation backend"):
            assign_cells(sample_transcripts_df, "imaginary_backend")

    def test_provided_cells_filters_empty(self):
        df = pd.DataFrame(
            {
                "fov": [1, 1, 2],
                "cell_ID": [1, 2, 3],
                "x_global_px": [1.0, 2.0, 3.0],
                "y_global_px": [1.0, 2.0, 3.0],
                "x_local_px": [1.0, 2.0, 3.0],
                "y_local_px": [1.0, 2.0, 3.0],
                "z": [0, 0, 0],
                "target": ["GeneA", "GeneB", "GeneC"],
                "CellComp": ["Nuclear", "Cytoplasm", "Membrane"],
                "cell": ["1_1", "", None],
            }
        )
        result = assign_cells(df, "provided_cells")
        assigned = result.output
        assert len(assigned) == 1
        assert assigned["cell"].iloc[0] == "1_1"


# ═══════════════════════════════════════════════════════════════════════
# Cellpose backend tests
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not _CELLPOSE_AVAILABLE, reason="cellpose not installed")
class TestCellposeBackend:
    """Tests for the Cellpose segmentation backend.

    These tests mock the Cellpose model evaluation to avoid needing
    actual images or GPU.  We test:
      - Successful segmentation with mock masks
      - Error when image_path is missing
      - Error when image file does not exist
      - Transcripts outside mask boundaries are correctly dropped
    """

    def _make_transcript_df(self, n: int = 20) -> pd.DataFrame:
        """Create a simple transcript DataFrame with known coordinates."""
        rng = np.random.default_rng(42)
        return pd.DataFrame({
            "fov": [1] * n,
            "cell": list(range(1, n + 1)),
            "x_global_px": rng.uniform(10, 90, size=n),
            "y_global_px": rng.uniform(10, 90, size=n),
            "x_local_px": rng.uniform(10, 90, size=n),
            "y_local_px": rng.uniform(10, 90, size=n),
            "z": [0] * n,
            "target": rng.choice(["GeneA", "GeneB"], size=n),
            "CellComp": rng.choice(["Nuclear", "Cytoplasm"], size=n),
        })

    @patch("cellpose.models.CellposeModel")
    @patch("cellpose.io.imread")
    def test_cellpose_success(self, mock_imread, mock_cp_model, tmp_path):
        """Cellpose returns masks, transcripts are assigned correctly."""
        # Create a dummy image (100x100 grayscale)
        dummy_img = np.zeros((100, 100, 1), dtype=np.uint8)
        mock_imread.return_value = dummy_img

        # Mock Cellpose model: return a mask with 3 cells
        mock_model_instance = MagicMock()
        mock_cp_model.return_value = mock_model_instance

        # Mask: shape (100,100), cell IDs 1,2,3
        masks = np.zeros((100, 100), dtype=np.int32)
        masks[20:40, 20:40] = 1   # Cell 1
        masks[50:70, 50:70] = 2   # Cell 2
        masks[10:30, 70:90] = 3   # Cell 3

        mock_model_instance.eval.return_value = (masks, None, None)

        df = self._make_transcript_df(50)

        # Save a dummy image path
        img_path = tmp_path / "dapi.png"
        img_path.write_bytes(b"dummy")

        result = assign_cells(df, "cellpose", image_path=str(img_path))

        assert isinstance(result, StepResult)
        assert result.backend_used == "cellpose"
        assert result.summary["segmentation_backend"] == "cellpose"
        assert result.summary["n_cellpose_masks"] == 3
        assert result.summary["n_cells_assigned"] > 0
        # All assigned cells should have the 'cellpose_' prefix
        assert all(c.startswith("cellpose_") for c in result.output["cell"].unique())
        assert "n_transcripts_assigned" in result.summary

    @patch("cellpose.models.CellposeModel")
    @patch("cellpose.io.imread")
    def test_cellpose_drops_outside_transcripts(self, mock_imread, mock_cp_model, tmp_path):
        """Transcripts whose (x,y) falls outside any mask are dropped."""
        dummy_img = np.zeros((100, 100, 1), dtype=np.uint8)
        mock_imread.return_value = dummy_img

        mock_model_instance = MagicMock()
        mock_cp_model.return_value = mock_model_instance

        # Only one small mask at corner
        masks = np.zeros((100, 100), dtype=np.int32)
        masks[5:15, 5:15] = 1

        mock_model_instance.eval.return_value = (masks, None, None)

        # Create transcripts, many outside the mask
        df = pd.DataFrame({
            "fov": [1] * 10,
            "cell": list(range(1, 11)),
            "x_global_px": [10.0, 50.0, 80.0, 10.0, 90.0, 5.0, 95.0, 10.0, 99.0, 10.0],
            "y_global_px": [10.0, 50.0, 80.0, 80.0, 10.0, 5.0, 95.0, 10.0, 99.0, 10.0],
            "x_local_px": [10.0] * 10,
            "y_local_px": [10.0] * 10,
            "z": [0] * 10,
            "target": ["GeneA"] * 10,
            "CellComp": ["Nuclear"] * 10,
        })

        img_path = tmp_path / "dapi.png"
        img_path.write_bytes(b"dummy")

        result = assign_cells(df, "cellpose", image_path=str(img_path))

        # Only transcripts at (10,10) should be kept (inside mask 1)
        assert len(result.output) < 10
        assert all(result.output["cell"] == "cellpose_1")

    def test_cellpose_no_image_path_raises(self, sample_transcripts_df):
        """Cellpose backend raises ValueError when image_path is not provided."""
        with pytest.raises(ValueError, match="image_path"):
            assign_cells(sample_transcripts_df, "cellpose")

    def test_cellpose_image_not_found_raises(self, sample_transcripts_df, tmp_path):
        """Cellpose backend raises FileNotFoundError when image does not exist."""
        fake_path = tmp_path / "nonexistent.png"
        with pytest.raises(FileNotFoundError, match="not found"):
            assign_cells(sample_transcripts_df, "cellpose", image_path=str(fake_path))


# ═══════════════════════════════════════════════════════════════════════
# Baysor backend tests
# ═══════════════════════════════════════════════════════════════════════

class TestBaysorBackend:
    """Tests for the Baysor segmentation backend.

    These tests mock the subprocess call to avoid needing Baysor CLI.
    We test:
      - Successful segmentation with mocked Baysor output
      - Error when Baysor CLI is not found
      - Error when Baysor fails (non-zero exit code)
      - Handling of noise cell assignment (cell == 0)
    """

    def _make_transcript_df(self, n: int = 20) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        return pd.DataFrame({
            "fov": [1] * n,
            "cell": list(range(1, n + 1)),
            "x_global_px": rng.uniform(0, 100, size=n),
            "y_global_px": rng.uniform(0, 100, size=n),
            "x_local_px": rng.uniform(0, 100, size=n),
            "y_local_px": rng.uniform(0, 100, size=n),
            "z": [0] * n,
            "target": rng.choice(["GeneA", "GeneB", "GeneC"], size=n),
            "CellComp": rng.choice(["Nuclear", "Cytoplasm"], size=n),
        })

    @patch("src.steps.segmentation.subprocess.run")
    def test_baysor_success(self, mock_run):
        """Baysor assigns transcripts to cells successfully."""
        df = self._make_transcript_df(30)

        # Prepare a fake Baysor segments output
        n_rows = len(df)
        segments_csv_lines = "x,y,gene,cell\n"
        for i in range(n_rows):
            # Assign cell IDs 1, 2, 3 cycling
            cell_id = (i % 3) + 1
            segments_csv_lines += f"{df['x_global_px'].iloc[i]},{df['y_global_px'].iloc[i]},{df['target'].iloc[i]},{cell_id}\n"

        # Mock subprocess.run to return the segments CSV on disk
        def _mock_run(cmd, **kwargs):
            import tempfile
            # Write the segments CSV to the output directory
            # The command is: baysor run <input_csv> <output_dir> ...
            output_dir = Path(cmd[3])  # output_dir is the 4th arg
            output_dir.mkdir(parents=True, exist_ok=True)
            seg_path = output_dir / "segments.csv"
            seg_path.write_text(segments_csv_lines)

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result

        mock_run.side_effect = _mock_run

        result = assign_cells(df, "baysor")

        assert isinstance(result, StepResult)
        assert result.backend_used == "baysor"
        assert result.summary["segmentation_backend"] == "baysor"
        assert result.summary["n_cells_assigned"] == 3
        assert result.summary["n_baysor_cells"] == 3
        assert all(c.startswith("baysor_") for c in result.output["cell"].unique())

    @patch("src.steps.segmentation.subprocess.run")
    def test_baysor_filters_noise(self, mock_run):
        """Baysor cell '0' is treated as noise and filtered out."""
        df = self._make_transcript_df(20)

        # Some cells are assigned to noise (cell=0)
        segments_csv_lines = "x,y,gene,cell\n"
        for i in range(len(df)):
            if i < 15:
                cell_id = (i % 3) + 1
            else:
                cell_id = 0  # noise
            segments_csv_lines += f"{df['x_global_px'].iloc[i]},{df['y_global_px'].iloc[i]},{df['target'].iloc[i]},{cell_id}\n"

        def _mock_run(cmd, **kwargs):
            output_dir = Path(cmd[3])
            output_dir.mkdir(parents=True, exist_ok=True)
            seg_path = output_dir / "segments.csv"
            seg_path.write_text(segments_csv_lines)
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result

        mock_run.side_effect = _mock_run

        result = assign_cells(df, "baysor")

        # The last 5 (noise) and potentially baysor_0 filtered out
        assert not any(result.output["cell"] == "baysor_0")
        assert result.summary["n_transcripts_assigned"] <= 15
        assert result.summary["n_cells_assigned"] == 3

    @patch("src.steps.segmentation.subprocess.run")
    def test_baysor_cli_not_found_raises(self, mock_run):
        """When Baysor CLI is not installed, a RuntimeError should be raised."""
        df = self._make_transcript_df(10)
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError, match="Baysor CLI.*not found"):
            assign_cells(df, "baysor")

    @patch("src.steps.segmentation.subprocess.run")
    def test_baysor_failure_raises(self, mock_run):
        """When Baysor returns non-zero exit code, a RuntimeError should be raised."""
        df = self._make_transcript_df(10)

        def _mock_fail(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Some Baysor error"
            return mock_result

        mock_run.side_effect = _mock_fail

        with pytest.raises(RuntimeError, match="Baysor failed"):
            assign_cells(df, "baysor")


# ═══════════════════════════════════════════════════════════════════════
# Registry integration tests
# ═══════════════════════════════════════════════════════════════════════

class TestSegmentationRegistry:
    """Verify that backends are properly registered for the pipeline engine."""

    def test_backends_are_registered(self):
        from src.registry import get_available_backends

        backends = get_available_backends("segmentation")
        assert "provided_cells" in backends
        assert "fov_cell_id" in backends
        if _CELLPOSE_AVAILABLE:
            assert "cellpose" in backends, f"cellpose not in {backends}"
        assert "baysor" in backends

    def test_runner_is_registered(self):
        from src.registry import get_runner

        runner = get_runner("segmentation")
        assert callable(runner)

    def test_runner_needs_denoised_data(self, sample_transcripts_df):
        """The runner should raise if ctx.denoised_df is None."""
        from src.pipeline_engine import ExecutionContext
        from src.registry import get_runner

        ctx = ExecutionContext()
        runner = get_runner("segmentation")

        with pytest.raises(ValueError, match="No denoised data"):
            runner(ctx, "provided_cells", {})

    def test_runner_with_denoised_data(self, sample_transcripts_df):
        """The runner should produce segmented_df when given denoised data."""
        from src.pipeline_engine import ExecutionContext
        from src.registry import get_runner

        ctx = ExecutionContext(denoised_df=sample_transcripts_df)
        runner = get_runner("segmentation")

        result = runner(ctx, "provided_cells", {})

        assert ctx.segmented_df is not None
        assert result.backend_used == "provided_cells"
        assert result.summary["n_cells_assigned"] > 0

    def test_backend_list_includes_new(self):
        from src.registry import get_available_backends

        backends = get_available_backends("segmentation")
        if _CELLPOSE_AVAILABLE:
            assert "cellpose" in backends, f"cellpose not in {backends}"
        assert "baysor" in backends, f"baysor not in {backends}"
