from __future__ import annotations

from fastapi.testclient import TestClient

from src.api_server import _parse_allowed_origins, app, sample_id, search_registries

client = TestClient(app)


def _write_registries(tmp_path):
    (tmp_path / "cosmx_geo.csv").write_text(
        "GSE,name,sample_name,status,n_cells\nGSE1,Colon IBD,GSM11,ready,1200\n", encoding="utf-8"
    )
    (tmp_path / "xenium_geo.csv").write_text(
        "GSE,name,GSM,status,n_cells\nGSE2,Breast tumour,GSM21,ready,3.0\nGSE2,Breast tumour,GSM22,pending,\n",
        encoding="utf-8",
    )
    return tmp_path


class TestHealth:
    def test_health(self):
        assert client.get("/api/health").json() == {"status": "ok"}


class TestSearchRegistries:
    def test_gsm_lookup_works_for_xenium_column_name(self, tmp_path):
        # Regression: lookup used to read only ``sample_name`` (CosMx), so Xenium/MERFISH GSMs never matched.
        rows = search_registries("gsm21", _write_registries(tmp_path))
        assert [r["GSM"] for r in rows] == ["GSM21"]
        assert rows[0]["platform"] == "xenium"

    def test_gsm_lookup_cosmx_sample_name(self, tmp_path):
        rows = search_registries("GSM11", _write_registries(tmp_path))
        assert rows[0]["GSM"] == "GSM11"
        assert rows[0]["n_cells"] == 1200

    def test_gse_returns_all_samples(self, tmp_path):
        rows = search_registries("GSE2", _write_registries(tmp_path))
        assert {r["GSM"] for r in rows} == {"GSM21", "GSM22"}

    def test_numeric_float_strings_are_converted(self, tmp_path):
        rows = search_registries("GSM21", _write_registries(tmp_path))
        assert rows[0]["n_cells"] == 3

    def test_keyword_match_on_name(self, tmp_path):
        rows = search_registries("colon", _write_registries(tmp_path))
        assert len(rows) == 1

    def test_sample_id_prefers_gsm(self):
        assert sample_id({"GSM": "GSM1", "sample_name": ""}) == "GSM1"
        assert sample_id({"sample_name": "GSM2-GSM4"}) == "GSM2-GSM4"


class TestAllowedOrigins:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("SUBCELLSPACE_ALLOWED_ORIGINS", raising=False)
        assert "http://localhost:5173" in _parse_allowed_origins()

    def test_custom_and_empty_filtered(self, monkeypatch):
        monkeypatch.setenv("SUBCELLSPACE_ALLOWED_ORIGINS", "https://a.example, ,https://b.example")
        assert _parse_allowed_origins() == ["https://a.example", "https://b.example"]
