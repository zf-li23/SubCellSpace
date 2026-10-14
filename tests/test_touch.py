from __future__ import annotations

import gzip

import pytest

from src.io import SampleReadError, read_sample
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


def test_empty_sample_dir_raises_sample_read_error(tmp_path):
    with pytest.raises(SampleReadError):
        read_sample(tmp_path, platform="merfish")


def test_author_annotation_is_discovered(tmp_path):
    _write(tmp_path / "GSM1_transcripts.csv.gz")
    _write(tmp_path / "GSM1_TLS_annotation.csv.gz")
    report = touch(str(tmp_path), platform_override="xenium")
    assert any(f.name == "author_annotation" and f.found for f in report.files)
    assert report.unexpected == []
