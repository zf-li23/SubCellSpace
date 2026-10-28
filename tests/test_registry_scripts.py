from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "mark_ready", Path(__file__).resolve().parent.parent / "scripts" / "registry" / "mark_ready.py"
)
mark_ready = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mark_ready)


def test_only_processed_rows_become_ready():
    rows = [{"GSE": "G1", "status": "pending", "stats_source": "subcellspace abc 2026-10-29"},
            {"GSE": "G2", "status": "error", "stats_source": "subcellspace abc 2026-10-29"},
            {"GSE": "G3", "status": "pending", "stats_source": ""},   # not downloaded / failed
            {"GSE": "G4", "status": "ready", "stats_source": "subcellspace abc"}]
    changed = mark_ready.mark(rows)
    assert changed == [("pending", "G1"), ("error", "G2")]
    assert [r["status"] for r in rows] == ["ready", "ready", "pending", "ready"]


_spec2 = importlib.util.spec_from_file_location(
    "apply_label_overrides", Path(__file__).resolve().parent.parent / "scripts" / "registry" / "apply_label_overrides.py"
)
overrides_mod = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(overrides_mod)


def test_label_overrides_apply_once_and_only_to_label_columns(tmp_path):
    p = tmp_path / "o.tsv"
    p.write_text("GSE\tsample\tcolumn\tvalue\treason\nGSE1\tGSM1\ttissue\tLiver (dissociated cells)\tfile name\n")
    o = overrides_mod.load_overrides(p)
    rows = [{"GSE": "GSE1", "GSM": "GSM1", "tissue": "Unknown"}, {"GSE": "GSE1", "GSM": "GSM2", "tissue": "Unknown"}]
    assert overrides_mod.apply(rows, "GSM", o) == 1 and overrides_mod.apply(rows, "GSM", o) == 0
    assert [r["tissue"] for r in rows] == ["Liver (dissociated cells)", "Unknown"]
    p.write_text("GSE\tsample\tcolumn\tvalue\treason\nGSE1\tGSM1\tstatus\tready\tx\n")
    import pytest

    with pytest.raises(SystemExit):
        overrides_mod.load_overrides(p)
