"""生成 Slurm 作业数组用的样本清单（TSV：platform, sample_dir, GSE, GSM, data_size）。

只选 status=ready 的 GEO 样本，按登记表里的 data_size 从小到大排序。
    python scripts/make_sample_list.py --platform xenium --limit 20 -o lists/xenium_20.tsv
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.resolver import list_datasets  # noqa: E402

_UNITS = {"": 1, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}


def parse_size(value: str | None) -> float:
    m = re.match(r"\s*([\d.]+)\s*([KMGT]?)", value or "")
    return float(m.group(1)) * _UNITS[m.group(2)] if m else float("inf")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--platform", choices=["cosmx", "xenium", "merfish"], action="append",
                    help="repeatable; default all")
    ap.add_argument("--limit", type=int, default=None, help="max samples per platform (smallest first)")
    ap.add_argument("--max-size", type=str, default=None, help="skip samples larger than this, e.g. 2G")
    ap.add_argument("--min-size", type=str, default=None, help="skip samples smaller than this, e.g. 500M")
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    names = {"cosmx": "CosMx", "xenium": "Xenium", "merfish": "MERFISH"}
    max_size = parse_size(args.max_size) if args.max_size else float("inf")
    min_size = parse_size(args.min_size) if args.min_size else 0.0
    rows = []
    for plat in args.platform or list(names):
        ds = [d for d in list_datasets(platform=names[plat], status="ready") if d.local_path]
        ds = [(parse_size(d._raw.get("data_size")), d) for d in ds]
        ds = sorted((x for x in ds if min_size <= x[0] <= max_size), key=lambda x: x[0])[: args.limit]
        rows += [(plat, d.local_path.rstrip("/"), d.gse, d.gsm, d._raw.get("data_size", "")) for _, d in ds]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} samples → {args.output}")


if __name__ == "__main__":
    main()
