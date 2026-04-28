from __future__ import annotations

import pandas as pd
import numpy as np
from src.steps.denoise import apply_transcript_denoise
from src.registry import get_available_backends


class TestApplyTranscriptDenoise:
    def test_backend_intracellular_filters_non_cellcomp(self, sample_transcripts_df):
        result = apply_transcript_denoise(sample_transcripts_df, "intracellular")
        filtered = result.output
        summary = result.summary
        assert len(filtered) <= len(sample_transcripts_df)
        # Only Nuclear and Cytoplasm should remain
        assert filtered["CellComp"].isin(["Nuclear", "Cytoplasm"]).all()
        assert summary["denoise_backend"] == "intracellular"
        assert summary["before_transcripts"] == len(sample_transcripts_df)
        assert summary["after_transcripts"] == len(filtered)

    def test_backend_none_passes_through(self, sample_transcripts_df):
        result = apply_transcript_denoise(sample_transcripts_df, "none")
        filtered = result.output
        summary = result.summary
        assert len(filtered) == len(sample_transcripts_df)
        assert summary["denoise_backend"] == "none"
        assert summary["dropped_transcripts"] == 0

    def test_backend_nuclear_only(self, sample_transcripts_df):
        result = apply_transcript_denoise(sample_transcripts_df, "nuclear_only")
        filtered = result.output
        summary = result.summary
        # Only Nuclear should remain
        assert (filtered["CellComp"] == "Nuclear").all()
        assert summary["denoise_backend"] == "nuclear_only"

    def test_unknown_backend_raises(self, sample_transcripts_df):
        with __import__("pytest").raises(ValueError, match="Unknown denoise backend"):
            apply_transcript_denoise(sample_transcripts_df, "bad_backend")

    def test_drop_ratio_computed(self, sample_transcripts_df):
        result = apply_transcript_denoise(sample_transcripts_df, "nuclear_only")
        assert "drop_ratio" in result.summary
        assert 0.0 <= result.summary["drop_ratio"] <= 1.0

    def test_empty_dataframe(self):
        df_empty = pd.DataFrame(columns=["CellComp", "fov", "cell_ID", "x_global_px", "y_global_px", "x_local_px", "y_local_px", "z", "target"])
        result = apply_transcript_denoise(df_empty, "intracellular")
        assert len(result.output) == 0
        assert result.summary["drop_ratio"] == 0.0

    def test_available_backends(self):
        backends = get_available_backends("denoise")
        assert "none" in backends
        assert "intracellular" in backends
        assert "nuclear_only" in backends
