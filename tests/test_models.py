from __future__ import annotations

from pathlib import Path

from src.models import DatasetSummary, PipelineResult


class TestDatasetSummary:
    def test_basic_construction(self):
        summary = DatasetSummary(
            source_path=Path("/data/sample.csv"),
            n_transcripts=1000,
            n_cells=50,
            n_genes=20,
            n_fovs=4,
        )
        assert summary.n_transcripts == 1000
        assert summary.n_cells == 50
        assert summary.n_genes == 20
        assert summary.n_fovs == 4
        assert summary.source_path == Path("/data/sample.csv")
        assert summary.extra == {}

    def test_extra_fields(self):
        summary = DatasetSummary(
            source_path=Path("/data/sample.csv"),
            n_transcripts=100,
            n_cells=10,
            n_genes=5,
            n_fovs=1,
            extra={"nuclear_fraction": 0.45, "platform": "CosMx"},
        )
        assert summary.extra["nuclear_fraction"] == 0.45
        assert summary.extra["platform"] == "CosMx"

    def test_to_text(self):
        summary = DatasetSummary(
            source_path=Path("/data/sample.csv"),
            n_transcripts=500,
            n_cells=25,
            n_genes=12,
            n_fovs=2,
        )
        text = summary.to_text()
        assert "source_path" in text
        assert "n_transcripts: 500" in text
        assert "n_cells: 25" in text
        assert "n_genes: 12" in text
        assert "n_fovs: 2" in text

    def test_slots_prevent_new_attributes(self, sample_anndata):
        """Exercise that slots=True prevents ad-hoc attribute assignment."""
        from src.models import PipelineResult

        result = PipelineResult(
            adata=sample_anndata,
            summary=DatasetSummary(
                source_path=Path("/tmp/test.csv"),
                n_transcripts=100,
                n_cells=10,
                n_genes=5,
                n_fovs=1,
            ),
            sdata=None,  # type: ignore[arg-type]
            adata_path=Path("/tmp/test.h5ad"),
            report_path=Path("/tmp/test_report.json"),
        )
        # Should not be able to assign a random new attribute
        try:
            result._extra = 42  # type: ignore[attr-defined]
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass