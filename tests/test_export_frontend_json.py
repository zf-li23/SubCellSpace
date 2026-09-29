from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "export_frontend_json", Path(__file__).resolve().parent.parent / "scripts" / "export_frontend_json.py"
)
export_frontend_json = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export_frontend_json)


def test_cosmx_sample_name_is_exported_as_gsm():
    # Regression: the browser read `sample_name`, so Xenium/MERFISH rows (column `GSM`) had no GSM link.
    cols = ["GSE", "sample_name", "n_cells"]
    meta = export_frontend_json.build_meta(export_frontend_json.output_columns(cols, "sample_name"))
    types = {c["name"]: c["type"] for c in meta["columns"]}
    rows = export_frontend_json.build_rows(
        [{"GSE": "GSE1", "sample_name": "GSM1-GSM3", "n_cells": "12.0"}], cols, "sample_name", types
    )
    assert rows == [{"GSE": "GSE1", "GSM": "GSM1-GSM3", "n_cells": 12}]
    assert "GSM" in meta["priority_columns"]


def test_xenium_gsm_column_unchanged():
    cols = ["GSE", "GSM"]
    assert export_frontend_json.output_columns(cols, "GSM") == ["GSE", "GSM"]
    rows = export_frontend_json.build_rows([{"GSE": "GSE2", "GSM": "GSM9"}], cols, "GSM", {})
    assert rows[0]["GSM"] == "GSM9"
