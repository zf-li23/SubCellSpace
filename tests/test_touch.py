from __future__ import annotations

import gzip

import pytest

from src.io.base import DataLoadError
from src.io.merfish import MERFISHIngestor
from src.touch import SUBCELLPREFIX, touch


def _write(path, text="a,b\n1,2\n"):
    path.write_text(text, encoding="utf-8")
    return path


def test_cosmx_required_and_optional_detected(tmp_path):
    _write(tmp_path / "GSM1_tx_file.csv")
    _write(tmp_path / "GSM1_exprMat_file.csv")
    _write(tmp_path / "GSM1_fov_position_file.csv")  # singular variant must match *_fov_position*
    report = touch(str(tmp_path), platform_override="cosmx")
    summary = report.to_dict()["summary"]
    assert report.platform == "cosmx"
    assert summary["required_found"] == 1
    assert summary["optional_found"] == 2
    assert report.missing_required == []


def test_missing_required_reported(tmp_path):
    _write(tmp_path / "GSM1_exprMat_file.csv")
    report = touch(str(tmp_path), platform_override="cosmx")
    assert report.missing_required


def test_own_outputs_are_ignored(tmp_path):
    _write(tmp_path / "GSM1_tx_file.csv")
    _write(tmp_path / f"{SUBCELLPREFIX}touch_report.json", "{}")
    report = touch(str(tmp_path), platform_override="cosmx")
    assert report.unexpected == []


def test_scan_does_not_modify_files(tmp_path):
    raw = _write(tmp_path / "tx_file.csv")
    before = sorted(p.name for p in tmp_path.iterdir())
    touch(str(tmp_path), platform_override="cosmx")  # normalize=False by default
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert raw.read_text(encoding="utf-8") == "a,b\n1,2\n"


def test_gz_variant_counts_as_found(tmp_path):
    with gzip.open(tmp_path / "GSM1_tx_file.csv.gz", "wt") as f:
        f.write("a,b\n1,2\n")
    report = touch(str(tmp_path), platform_override="cosmx")
    assert report.to_dict()["summary"]["required_found"] == 1


def test_merfish_empty_dir_raises_data_load_error(tmp_path):
    # Regression: merfish.py referenced DataLoadError without importing it (NameError instead).
    with pytest.raises(DataLoadError):
        MERFISHIngestor()._resolve_tx_path(tmp_path)
