"""只读扫描：找出同一样本目录里"压缩版 + 解压版"并存的文件对（第 1 步，候选）。

依据 gzip 尾部 ISIZE（解压后大小 mod 2^32）匹配同目录、同类型的未压缩文件。
输出 TSV：dir, gz_name, gz_size, partner_name, partner_size, kind, keep
  keep = 按约定保留的一方：二进制格式（parquet/h5/tif/zarr）保留解压版，文本（csv/tsv）保留 .gz
用法：python scan_gz_pairs.py <根目录>... > pairs.tsv
"""

from __future__ import annotations

import os
import struct
import sys

BINARY = (".parquet", ".h5", ".tif", ".tiff", ".zarr.zip", ".mtx", ".rds", ".h5ad")
TEXT = (".csv", ".tsv", ".txt")


def kind_of(name: str) -> str | None:
    base = name[:-3] if name.endswith(".gz") else name
    low = base.lower()
    if low.endswith(BINARY):
        return "binary"
    if low.endswith(TEXT):
        return "text"
    return None


def isize(path: str) -> int:
    with open(path, "rb") as f:
        f.seek(-4, os.SEEK_END)
        return struct.unpack("<I", f.read(4))[0]


def main(roots: list[str]) -> None:
    for root in roots:
        for d, _, files in os.walk(root):
            plain = {}
            for n in files:
                if not n.endswith(".gz") and kind_of(n):
                    try:
                        size = os.path.getsize(os.path.join(d, n))
                    except OSError as exc:  # broken symlink / permission: report, don't stop the scan
                        print(f"skip\t{os.path.join(d, n)}\t{exc}", file=sys.stderr)
                        continue
                    plain.setdefault(size % 2**32, []).append(n)
            for n in files:
                k = kind_of(n)
                if not n.endswith(".gz") or not k:
                    continue
                p = os.path.join(d, n)
                try:
                    target = isize(p)
                except OSError as exc:
                    print(f"skip\t{p}\t{exc}", file=sys.stderr)
                    continue
                ext = n[:-3].lower().rsplit(".", 1)[-1]
                for m in plain.get(target, []):
                    if m.lower().endswith(ext):
                        keep = "plain" if k == "binary" else "gz"
                        try:
                            sz = os.path.getsize(os.path.join(d, m))
                        except OSError:
                            continue
                        print(f"{d}\t{n}\t{os.path.getsize(p)}\t{m}\t{sz}\t{k}\t{keep}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
