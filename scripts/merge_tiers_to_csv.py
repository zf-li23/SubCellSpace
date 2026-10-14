"""把 assess_tiers.py 的结果写回登记表的 data_tier 列（只新增列，不改已有列）。

    python scripts/merge_tiers_to_csv.py tiers.tsv [--dry-run]
未评估的行（非 ready）data_tier 留空。
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
REGISTRIES = {"cosmx": ("cosmx_geo.csv", "sample_name"), "xenium": ("xenium_geo.csv", "GSM"),
              "merfish": ("merfish_geo.csv", "GSM")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tiers", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(args.tiers, encoding="utf-8") as f:
        tiers = {(r["GSE"], r["GSM"]): r["data_tier"] for r in csv.DictReader(f, delimiter="\t")}

    for plat, (fname, sample_col) in REGISTRIES.items():
        path = DATA / fname
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
        if "data_tier" not in fields:
            fields.append("data_tier")
        n = 0
        for r in rows:
            tier = tiers.get((r["GSE"], r[sample_col]))
            r["data_tier"] = tier or r.get("data_tier", "")
            n += tier is not None
        print(f"{plat}: {n}/{len(rows)} rows tiered")
        if not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
