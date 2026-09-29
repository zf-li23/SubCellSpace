from __future__ import annotations

import pytest

from src.database import resolver


@pytest.fixture
def registries(tmp_path, monkeypatch):
    (tmp_path / "cosmx_geo.csv").write_text(
        "GSE,name,sample_name,status,tissue,disease_state\n"
        "GSE1,Colon,GSM100,ready,colon,IBD\n"
        "GSE1,Colon,GSM101-GSM103,ready,colon,IBD\n",
        encoding="utf-8",
    )
    (tmp_path / "xenium_geo.csv").write_text(
        "GSE,name,GSM,status,tissue,disease_state\nGSE2,Breast,GSM200,pending,breast,\n", encoding="utf-8"
    )
    (tmp_path / "merfish_geo.csv").write_text("GSE,name,GSM,status\n", encoding="utf-8")
    monkeypatch.setattr(resolver, "COSMX_GEO_CSV", tmp_path / "cosmx_geo.csv")
    monkeypatch.setattr(resolver, "XENIUM_GEO_CSV", tmp_path / "xenium_geo.csv")
    monkeypatch.setattr(resolver, "MERFISH_GEO_CSV", tmp_path / "merfish_geo.csv")
    monkeypatch.setattr(resolver, "_CLUSTER_DATA_ROOT", "/data/")


def test_lookup_gse_spans_rows(registries):
    rows = resolver.lookup("GSE1")
    assert [r.gsm for r in rows] == ["GSM100", "GSM101-GSM103"]
    assert rows[0].local_path == "/data/CosMx_GEO/GSE1/GSM100/"
    assert rows[0].tissue == "colon"


def test_lookup_gsm_uses_platform_column(registries):
    (row,) = resolver.lookup("GSM200")
    assert row.platform == "Xenium"
    assert row.disease_state is None


def test_lookup_gsm_range_matches_merged_sample(registries):
    rows = resolver.lookup("GSE1/GSM101-GSM103")
    assert [r.gsm for r in rows] == ["GSM101-GSM103"]


def test_legacy_vendor_ids_no_longer_resolve(registries):
    assert resolver.lookup("D0059") == []


def test_resolve_path_requires_ready(registries):
    assert resolver.resolve_path("GSE1/GSM100") == "/data/CosMx_GEO/GSE1/GSM100/"
    assert resolver.resolve_path("GSE2/GSM200") is None


def test_count_by_status(registries):
    counts = resolver.count_by_status()
    assert counts["ready"] == 2 and counts["pending"] == 1 and counts["total"] == 3
