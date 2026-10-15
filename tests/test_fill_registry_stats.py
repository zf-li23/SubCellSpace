from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "fill_registry_stats", Path(__file__).resolve().parent.parent / "scripts" / "fill_registry_stats.py"
)
fill_registry_stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fill_registry_stats)


def test_summary_overwrites_stale_stats(tmp_path):
    d = tmp_path / "GSE1" / "GSM1-GSM3"
    d.mkdir(parents=True)
    (d / "subcellspace_summary.json").write_text(json.dumps({
        "n_transcripts": None, "n_cells": 283682, "n_genes": 960, "gene_panel_size": 1000,
        "median_transcripts": 210.0, "median_genes": 120.5, "data_tier": "B",
        "software": {"subcellspace": "abc123"}, "generated": "2026-10-15T08:00:00+00:00",
    }))
    rows = [{"GSE": "GSE1", "sample_name": "GSM1-GSM3", "n_transcripts": "5", "n_cells": "2100", "n_fovs": "9",
             "data_tier": "A"},
            {"GSE": "GSE2", "sample_name": "GSM9", "n_cells": "7"}]
    n = fill_registry_stats.fill(rows, "sample_name", fill_registry_stats.load_summaries(tmp_path))
    assert n == 1
    r = rows[0]
    assert (r["n_cells"], r["n_transcripts"], r["n_fovs"], r["median_transcripts"], r["median_genes"]) == \
        ("283682", "", "", "210", "120.5")
    assert r["data_tier"] == "B" and r["stats_source"] == "subcellspace abc123 2026-10-15"
    assert rows[1]["n_cells"] == "7" and rows[1]["stats_source"] == ""
