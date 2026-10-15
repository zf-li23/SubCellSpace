"""把 `subcellspace process` 的 summary 写回登记表的统计列（覆盖旧值；只新增 stats_source 列）。

    rsync -am --include '*/' --include subcellspace_summary.json --exclude '*' \
        a-cluster:zf-li23/subcellspace/outputs/all/ summaries/
    python scripts/fill_registry_stats.py summaries/ [--dry-run]

旧的统计值不可靠（AGENTS.md §6 Next 3），所以有 summary 的行七个统计列全部重写；summary 里没有的量
（例如只有矩阵、没有转录本时的 n_transcripts）写空，而不是保留旧值。没有 summary 的行不动，
stats_source 为空即表示仍是旧值。data_tier 改为处理时实际判定的级别。
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
REGISTRIES = {"cosmx": ("cosmx_geo.csv", "sample_name"), "xenium": ("xenium_geo.csv", "GSM"),
              "merfish": ("merfish_geo.csv", "GSM")}
STATS = ("n_transcripts", "n_cells", "n_genes", "n_fovs", "gene_panel_size", "median_transcripts", "median_genes")


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.1f}"
    return str(value)


def load_summaries(root: Path) -> dict[tuple[str, str], dict]:
    out = {}
    for f in root.glob("GSE*/*/subcellspace_summary.json"):
        out[(f.parent.parent.name, f.parent.name)] = json.loads(f.read_text(encoding="utf-8"))
    return out


def fill(rows: list[dict], sample_col: str, summaries: dict[tuple[str, str], dict]) -> int:
    n = 0
    for r in rows:
        s = summaries.get((r["GSE"], r[sample_col]))
        if s is None:
            r.setdefault("stats_source", "")
            continue
        for col in STATS:
            r[col] = _fmt(s.get(col))
        r["data_tier"] = s.get("data_tier", r.get("data_tier", ""))
        r["stats_source"] = f"subcellspace {s.get('software', {}).get('subcellspace', '?')} {s.get('generated', '')[:10]}"
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("summaries", type=Path, help="outputs root: GSE*/GSM*/subcellspace_summary.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    summaries = load_summaries(args.summaries)
    print(f"{len(summaries)} summaries")
    for plat, (fname, sample_col) in REGISTRIES.items():
        path = DATA / fname
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
        if "stats_source" not in fields:
            fields.append("stats_source")
        n = fill(rows, sample_col, summaries)
        print(f"{plat}: {n}/{len(rows)} rows filled")
        if not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
