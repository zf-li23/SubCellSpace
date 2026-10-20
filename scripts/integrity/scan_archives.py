"""压缩文件完整性扫描（只读）：每个 ready 样本目录里的 .gz / .tgz / .zip 完整解压校验一遍。

    python scripts/integrity/scan_archives.py lists/all_ready.tsv OUT.tsv [--shard I --n-shards N]
    python scripts/integrity/scan_archives.py --recheck PREV.tsv OUT.tsv   # 只复查上次不是 ok 的文件

输出 TSV：GSE, GSM, path, size, status, error。status：
  ok             完整（gzip CRC / 长度校验通过；zip 所有成员 CRC 通过）
  no_gzip_header .gz 没有 gzip 文件头但是完整的裸 deflate 流（读取器能处理，例如 GSE301112）
  uncompressed   名为 .tar.gz / .tgz 但其实是未压缩的 tar，且所有成员都能完整读出（例如 GSE310433）
  corrupt        解压出错 / CRC 不符 / 被截断 → 需要重新下载
只用标准库；符号链接跳过（目标文件本身会被扫到）。
"""

from __future__ import annotations

import argparse
import csv
import gzip
import os
import sys
import tarfile
import zipfile
import zlib
from pathlib import Path

CHUNK = 16 * 1024 * 1024
SUFFIXES = (".gz", ".tgz", ".zip")


def check_gzip(path: Path) -> tuple[str, str]:
    with open(path, "rb") as f:
        magic = f.read(2)
    if magic != b"\x1f\x8b":
        return check_tar(path) if is_plain_tar(path) else check_raw_deflate(path)
    try:
        with gzip.open(path, "rb") as f:
            while f.read(CHUNK):
                pass
    except (OSError, EOFError, zlib.error) as exc:
        return "corrupt", f"{type(exc).__name__}: {exc}"[:200]
    return "ok", ""


def is_plain_tar(path: Path) -> bool:
    with open(path, "rb") as f:
        f.seek(257)
        return f.read(5) == b"ustar"


def check_tar(path: Path) -> tuple[str, str]:
    """Read every member of an uncompressed tar to the end (a truncated archive raises)."""
    try:
        with tarfile.open(path, mode="r:") as tar:
            for m in tar:
                if m.isfile():
                    f = tar.extractfile(m)
                    while f.read(CHUNK):
                        pass
    except (OSError, EOFError, tarfile.TarError) as exc:
        return "corrupt", f"uncompressed tar, unreadable: {type(exc).__name__}: {exc}"[:200]
    return "uncompressed", "plain tar named .gz"


def check_raw_deflate(path: Path) -> tuple[str, str]:
    d = zlib.decompressobj(-15)
    try:
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK):
                d.decompress(chunk)
        d.flush()
    except zlib.error as exc:
        return "corrupt", f"not gzip, not raw deflate: {exc}"[:200]
    if not d.eof:
        return "corrupt", "raw deflate stream truncated"
    return "no_gzip_header", ""


def check_zip(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
    except (OSError, EOFError, zlib.error, zipfile.BadZipFile) as exc:
        return "corrupt", f"{type(exc).__name__}: {exc}"[:200]
    return ("corrupt", f"bad CRC in member {bad}") if bad else ("ok", "")


def check(path: Path) -> tuple[str, str]:
    return check_zip(path) if path.name.lower().endswith(".zip") else check_gzip(path)


def archives(sample_dir: Path):
    for root, _dirs, files in os.walk(sample_dir):
        for name in sorted(files):
            p = Path(root) / name
            if (name.lower().endswith(SUFFIXES) and not name.startswith(("subcellspace_", "._"))  # ._*: macOS AppleDouble
                    and not p.is_symlink()):
                yield p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample_list", type=Path, nargs="?", help="TSV: platform, sample_dir, GSE, GSM, size")
    ap.add_argument("out", type=Path)
    ap.add_argument("--recheck", type=Path, default=None, help="earlier scan TSV: re-check its non-ok rows only")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=1)
    args = ap.parse_args()
    if args.recheck:
        with args.recheck.open(encoding="utf-8") as f:
            prev = [r for r in csv.DictReader(f, delimiter="\t") if r["status"] != "ok"]
        write(args.out, ((r["GSE"], r["GSM"], Path(r["path"])) for r in prev))
        return
    rows = [line.rstrip("\n").split("\t") for line in args.sample_list.open(encoding="utf-8") if line.strip()]
    rows = rows[args.shard::args.n_shards]
    write(args.out, ((gse, gsm, p) for _plat, sample_dir, gse, gsm, *_ in rows for p in archives(Path(sample_dir))))


def write(out_path: Path, items) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as out:
        out.write("GSE\tGSM\tpath\tsize\tstatus\terror\n")
        for gse, gsm, p in items:
            status, err = check(p)
            out.write(f"{gse}\t{gsm}\t{p}\t{p.stat().st_size}\t{status}\t{err}\n")
            out.flush()
            if status != "ok":
                print(f"{status}: {p} {err}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
