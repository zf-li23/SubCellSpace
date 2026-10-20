from __future__ import annotations

import gzip
import importlib.util
import zipfile
import zlib
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "scan_archives", Path(__file__).resolve().parent.parent / "scripts" / "integrity" / "scan_archives.py"
)
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)


def test_classifies_ok_corrupt_and_headerless(tmp_path):
    data = b"cell_id,x\n" + b"aaaa-1,1.0\n" * 50_000
    good = gzip.compress(data)
    (tmp_path / "ok.csv.gz").write_bytes(good)
    (tmp_path / "trunc.csv.gz").write_bytes(good[: len(good) // 2])  # truncated download (GSE276273-like)
    flipped = bytearray(good)
    flipped[len(good) // 2] ^= 0xFF
    (tmp_path / "flip.csv.gz").write_bytes(bytes(flipped))
    c = zlib.compressobj(wbits=-15)
    (tmp_path / "raw.tsv.gz").write_bytes(c.compress(data) + c.flush())  # GSE301112-like
    with zipfile.ZipFile(tmp_path / "x.zarr.zip", "w") as z:
        z.writestr("a/.zarray", "{}")
    got = {p.name: scan.check(p)[0] for p in scan.archives(tmp_path)}
    assert got == {"ok.csv.gz": "ok", "trunc.csv.gz": "corrupt", "flip.csv.gz": "corrupt",
                   "raw.tsv.gz": "no_gzip_header", "x.zarr.zip": "ok"}
