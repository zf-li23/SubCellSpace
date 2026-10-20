from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "collect_web_bundles", Path(__file__).resolve().parent.parent / "scripts" / "collect_web_bundles.py"
)
collect_web_bundles = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collect_web_bundles)


def test_collects_only_listed_samples_and_prunes_stale(tmp_path):
    public, source = tmp_path / "public", tmp_path / "src"
    public.mkdir()
    for plat, rows in (("cosmx", [{"GSE": "GSE1", "GSM": "GSM1-GSM3"}]), ("xenium", [{"GSE": "GSE2", "GSM": "GSM5"}]),
                       ("merfish", [])):
        (public / f"{plat}.json").write_text(json.dumps({"rows": rows}))
    for gse, gsm in (("GSE1", "GSM1-GSM3"), ("GSE276273", "GSM8494455")):
        (source / gse / gsm).mkdir(parents=True)
        (source / gse / gsm / "subcellspace_web.json").write_text("{}")
    (public / "samples" / "GSE9").mkdir(parents=True)
    (public / "samples" / "GSE9" / "GSM9.json").write_text("{}")  # stale
    r = collect_web_bundles.collect(source, public)
    assert r["copied"] == 1 and r["missing"] == ["GSE2/GSM5"] and r["removed"] == 1
    assert (public / "samples" / "GSE1" / "GSM1-GSM3.json").exists()
    assert not (public / "samples" / "GSE276273").exists()
