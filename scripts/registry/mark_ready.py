"""已成功处理（stats_source 非空）但 status 不是 ready 的行 → ready（owner, 2026-10-28：选项 A）。

    python scripts/fill_registry_stats.py <summaries>     # 先回填统计
    python scripts/registry/mark_ready.py [--dry-run]

只改 status 这一列的值；不动列名，不动其他行。OmniSTP 读这一列：ready = 数据已下载且可读。
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"
REGISTRIES = ("cosmx_geo.csv", "xenium_geo.csv", "merfish_geo.csv")


def mark(rows: list[dict]) -> list[tuple[str, str]]:
    changed = []
    for r in rows:
        if (r.get("stats_source") or "").strip() and r.get("status") != "ready":
            changed.append((r["status"], r["GSE"]))
            r["status"] = "ready"
    return changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for fname in REGISTRIES:
        path = DATA / fname
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields, rows = list(reader.fieldnames or []), list(reader)
        changed = mark(rows)
        by = {}
        for old, gse in changed:
            by[(old, gse)] = by.get((old, gse), 0) + 1
        print(f"{fname}: {len(changed)} rows → ready", dict(sorted(by.items())))
        if changed and not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
