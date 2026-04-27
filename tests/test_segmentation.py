from __future__ import annotations

import pytest
import pandas as pd
from src.steps.segmentation import assign_cells, AVAILABLE_SEGMENTATION_BACKENDS


class TestAssignCells:
    def test_backend_provided_cells(self, sample_transcripts_df):
        assigned, summary = assign_cells(sample_transcripts_df, "provided_cells")
        assert len(assigned) > 0
        assert summary["segmentation_backend"] == "provided_cells"
        assert summary["n_transcripts_assigned"] == len(assigned)
        assert summary["n_cells_assigned"] > 0

    def test_backend_fov_cell_id(self, sample_transcripts_df):
        # Create df without a cell column to test fov_cell_id backend
        df_no_cell = sample_transcripts_df.drop(columns=["cell"])
        assigned, summary = assign_cells(df_no_cell, "fov_cell_id")
        assert summary["segmentation_backend"] == "fov_cell_id"
        assert "cell" in assigned.columns
        expected_cell = f"{df_no_cell['fov'].iloc[0]}_{df_no_cell['cell_ID'].iloc[0]}"
        assert assigned["cell"].iloc[0] == expected_cell

    def test_unknown_backend_raises(self, sample_transcripts_df):
        with pytest.raises(ValueError, match="Unknown segmentation backend"):
            assign_cells(sample_transcripts_df, "imaginary_backend")

    def test_provided_cells_filters_empty(self, tmp_path):
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
        assigned, summary = assign_cells(df, "provided_cells")
        assert len(assigned) == 1
        assert assigned["cell"].iloc[0] == "1_1"