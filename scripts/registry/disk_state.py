"""登记表 status 与集群磁盘的对照（只读）：每行的样本目录是否存在、有没有数据文件。

    python scripts/registry/disk_state.py OUT.tsv          # 在集群上运行（需要能看到数据根目录）

输出每行一条：platform, GSE, sample, status, disk（dir:data / dir:tiny / dir:empty / nodir:gse / nodir），
n_files, bytes。用来核对 pending / error 的实际含义（AGENTS.md Next 1）。
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"
ROOT = Path(os.environ.get("SUBCELLSPACE_DATA_ROOT", "/data3/yangxr002"))
REGISTRIES = (("cosmx", "CosMx", "cosmx_geo.csv", "sample_name"), ("xenium", "Xenium", "xenium_geo.csv", "GSM"),
              ("merfish", "MERFISH", "merfish_geo.csv", "GSM"))


def disk_state(sample_dir: Path) -> tuple[str, int, int]:
    if not sample_dir.is_dir():
        return ("nodir:gse" if sample_dir.parent.is_dir() else "nodir"), 0, 0
    files = [p for p in sample_dir.rglob("*") if p.is_file() and not p.name.startswith("subcellspace_")]
    size = sum(p.stat().st_size for p in files)
    return ("dir:empty" if not files else "dir:data" if size > 1_000_000 else "dir:tiny"), len(files), size


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["platform", "GSE", "sample", "status", "disk", "n_files", "bytes"])
        for plat, folder, fname, key in REGISTRIES:
            with open(DATA / fname, encoding="utf-8") as g:
                for r in csv.DictReader(g):
                    state, n, size = disk_state(ROOT / f"{folder}_GEO" / r["GSE"] / r[key])
                    w.writerow([plat, r["GSE"], r[key], r["status"], state, n, size])


if __name__ == "__main__":
    main()
