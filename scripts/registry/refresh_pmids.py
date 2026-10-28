"""给登记表里 pubmedids 为空的行重新查一次 GEO（论文常在数据公开之后才关联到 GEO）。只填空值，不改已有值。

    python scripts/registry/refresh_pmids.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.geo.api import get_gse_enrichment  # noqa: E402

REGISTRIES = ("cosmx_geo.csv", "xenium_geo.csv", "merfish_geo.csv")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()
    tables = {}
    for fname in REGISTRIES:
        with open(ROOT / "data" / fname, encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            tables[fname] = (list(r.fieldnames or []), list(r))
    todo = sorted({row["GSE"] for _, rows in tables.values() for row in rows if not (row.get("pubmedids") or "").strip()})
    print(f"{len(todo)} GSEs without PMID")
    found: dict[str, str] = {}
    for gse in todo:
        try:
            data = get_gse_enrichment(gse, delay=args.delay)
        except Exception as exc:  # one failed request must not stop the refresh
            print(f"  {gse}: {type(exc).__name__}: {exc}")
            continue
        pmids = (data or {}).get("pubmedids", "").strip()
        if pmids:
            found[gse] = pmids
            print(f"  {gse}: {pmids}")
    print(f"{len(found)} GSEs now have a PMID")
    if args.dry_run or not found:
        return
    for fname, (fields, rows) in tables.items():
        n = 0
        for row in rows:
            if not (row.get("pubmedids") or "").strip() and row["GSE"] in found:
                row["pubmedids"] = found[row["GSE"]]
                n += 1
        with open(ROOT / "data" / fname, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"{fname}: {n} rows filled")


if __name__ == "__main__":
    main()
