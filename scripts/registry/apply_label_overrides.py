"""把 data/label_overrides.tsv 里的人工更正写进登记表（tissue / disease_state 等 LLM 标签列）。

    python scripts/registry/apply_label_overrides.py [--dry-run]

每条更正：GSE, sample, column, value, reason。重复运行结果相同；被更正的列再跑 LLM 标注时应以此表为准。
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"
REGISTRIES = (("cosmx_geo.csv", "sample_name"), ("xenium_geo.csv", "GSM"), ("merfish_geo.csv", "GSM"))
EDITABLE = {"tissue", "disease_state"}


def load_overrides(path: Path = DATA / "label_overrides.tsv") -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["column"] not in EDITABLE:
                raise SystemExit(f"column {r['column']!r} is not an editable label column")
            out.setdefault((r["GSE"], r["sample"]), {})[r["column"]] = r["value"]
    return out


def apply(rows: list[dict], key: str, overrides: dict) -> int:
    n = 0
    for r in rows:
        for col, value in overrides.get((r["GSE"], r[key]), {}).items():
            if r.get(col) != value:
                r[col] = value
                n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    overrides = load_overrides()
    for fname, key in REGISTRIES:
        path = DATA / fname
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields, rows = list(reader.fieldnames or []), list(reader)
        n = apply(rows, key, overrides)
        print(f"{fname}: {n} values changed")
        if n and not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
