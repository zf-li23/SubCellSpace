from __future__ import annotations

import numpy as np
import pandas as pd

from src.registry import get_available_backends
from src.steps.denoise import apply_transcript_denoise


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
        df_empty = pd.DataFrame(
            columns=[
                "CellComp",
                "fov",
                "cell_ID",
                "x_global_px",
                "y_global_px",
                "x_local_px",
                "y_local_px",
                "z",
                "target",
            ]
        )
        result = apply_transcript_denoise(df_empty, "intracellular")
        assert len(result.output) == 0
        assert result.summary["drop_ratio"] == 0.0

    def test_available_backends(self):
        backends = get_available_backends("denoise")
        assert "none" in backends
        assert "intracellular" in backends
        assert "nuclear_only" in backends
        assert "sparc" in backends

    # ── spARC (bug fix: crosstab str conversion, bool graph params) ──────────

    @staticmethod
    def _make_sparc_compatible_df(n_cells: int = 50) -> pd.DataFrame:
        """Build a DataFrame with enough cells for spARC's default knn=15 (needs ≥47)."""
        rows = []
        for c in range(n_cells):
            for g in range(5):
                rows.append(
                    {
                        "cell": f"Cell_{c}",
                        "target": f"Gene_{g}",
                        "CellComp": "Nuclear",
                        "x_global_px": float(c * 10),
                        "y_global_px": float(c * 10),
                    }
                )
        return pd.DataFrame(rows)

    def test_sparc_crosstab_str_conversion(self):
        """Verify that `target` values are cast to str before crosstab,
        preventing 'must have non-scalar value' errors from nested dtypes."""
        df = self._make_sparc_compatible_df(n_cells=50)
        # Add a row with non-string target to test str conversion
        df.loc[0, "target"] = 123  # non-string scalar
        result = apply_transcript_denoise(df, "sparc")
        assert result.summary["denoise_backend"] == "sparc"
        # spARC passes all transcripts through
        assert len(result.output) == 250
        # Denoised expression matrix should be stored in attrs
        assert "denoised_expression" in result.output.attrs
        assert "denoised_backend" in result.output.attrs
        assert result.output.attrs["denoised_backend"] == "sparc"

    def test_sparc_denoised_expression_shape(self):
        """spARC should produce a cell×gene expression matrix with correct shape."""
        df = self._make_sparc_compatible_df(n_cells=50)
        result = apply_transcript_denoise(df, "sparc")
        denoised = result.output.attrs["denoised_expression"]
        assert denoised.shape == (50, 5)  # 50 cells × 5 genes
