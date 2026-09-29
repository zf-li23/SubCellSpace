from __future__ import annotations

from src.constants import REQUIRED_CANONICAL_COLUMNS
from src.io import detect_platform, ingest


class TestDetectPlatform:
    def test_detect_cosmx_csv(self, sample_transcripts_csv):
        platform = detect_platform(sample_transcripts_csv)
        assert platform == "cosmx"


class TestIngest:
    def test_ingest_cosmx_csv(self, sample_transcripts_csv):
        sdata = ingest("cosmx", sample_transcripts_csv)
        assert "raw_transcripts" in sdata.points
        pts = sdata.points["raw_transcripts"].compute()
        for col in REQUIRED_CANONICAL_COLUMNS:
            assert col in pts.columns

    def test_ingest_summary_attrs(self, sample_transcripts_csv):
        sdata = ingest("cosmx", sample_transcripts_csv)
        summary = sdata.attrs.get("ingestion_summary", {})
        assert summary.get("n_transcripts", 0) > 0
        assert summary.get("n_cells", 0) > 0
        assert summary.get("n_genes", 0) > 0
