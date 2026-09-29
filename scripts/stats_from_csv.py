"""
从 GEO CSV 统计 touch 结果 — stats_from_csv.py
================================================
基于已填入 available_files / file_names 的 GEO CSV，
生成文件完整性统计报告（相当于 touch 的全局汇总）。

用法:
    python3 scripts/stats_from_csv.py
    python3 scripts/stats_from_csv.py --cosmx-only
    python3 scripts/stats_from_csv.py --json
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

PLATFORM_CONFIG = {
    "cosmx": {
        "csv": DATA_DIR / "cosmx_geo.csv",
        "key_col": "sample_name",
        "label": "CosMx",
        "all_optionals": ["polygons", "expr_matrix", "cell_metadata", "fov_positions"],
    },
    "xenium": {
        "csv": DATA_DIR / "xenium_geo.csv",
        "key_col": "GSM",
        "label": "Xenium",
        "all_optionals": ["cell_boundaries", "nucleus_boundaries", "expr_matrix", "cell_metadata", "gene_panel"],
    },
    "merfish": {
        "csv": DATA_DIR / "merfish_geo.csv",
        "key_col": "GSM",
        "label": "MERFISH",
        "all_optionals": ["expr_matrix", "cell_metadata"],
    },
}


def analyze_platform(platform: str) -> dict:
    cfg = PLATFORM_CONFIG[platform]
    with open(cfg["csv"], encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    status_counts = Counter()
    opt_counts = Counter()
    opt_dist = defaultdict(int)  # opt_count → n_datasets
    data_sizes = []
    no_report_ready = 0  # status=ready 但没有 file_names 的异常
    all_ok = 0           # transcripts + 全部可选文件都齐
    missing_required = 0 # status=ready 但没有 transcripts
    pending_but_has_data = 0  # status≠ready 但有 file_names

    for row in rows:
        status = row.get("status", "").strip()
        status_counts[status] += 1

        file_names_str = row.get("file_names", "").strip()
        available = row.get("available_files", "").strip()

        # 解析 file_names JSON
        has_transcripts = False
        if file_names_str:
            try:
                fn = json.loads(file_names_str)
                has_transcripts = "transcripts" in fn
            except json.JSONDecodeError:
                fn = {}

        # 解析 available_files
        found_opts = [o.strip() for o in available.split(",") if o.strip()] if available else []
        n_opt = len(found_opts)

        # 统计
        if status == "ready":
            if has_transcripts:
                all_optionals = cfg["all_optionals"]
                n_total_opts = len(all_optionals)
                if n_opt == n_total_opts and all(o in found_opts for o in all_optionals):
                    all_ok += 1
                opt_dist[n_opt] += 1
                for o in found_opts:
                    opt_counts[o] += 1
            else:
                missing_required += 1

            if not file_names_str:
                no_report_ready += 1

        if status != "ready" and file_names_str:
            pending_but_has_data += 1

        # data_size
        ds = row.get("data_size", "").strip()
        if ds:
            data_sizes.append(ds)

    return {
        "platform": cfg["label"],
        "total": total,
        "status": dict(status_counts),
        "ready_with_transcripts": status_counts.get("ready", 0) - missing_required,
        "missing_required": missing_required,  # ready 但无 transcripts
        "no_report_ready": no_report_ready,
        "pending_but_has_data": pending_but_has_data,
        "all_optionals_present": all_ok,
        "optional_distribution": {str(k): v for k, v in sorted(opt_dist.items())},
        "optional_counts": dict(opt_counts.most_common()),
        "data_size_samples": data_sizes[:5] if data_sizes else [],
    }


def print_report(results: list) -> None:
    print("=" * 60)
    print("  GEO CSV 文件完整性统计报告")
    print("=" * 60)
    print()

    for r in results:
        print(f"  ── {r['platform']} ──────────────────────────────")
        print(f"    总数据集:          {r['total']}")
        print("    status:            ", end="")
        parts = [f"{k}={v}" for k, v in sorted(r['status'].items())]
        print(", ".join(parts))
        print(f"    ready 且有 transcripts: {r['ready_with_transcripts']}")
        print(f"    ready 但缺 transcripts:  {r['missing_required']}")
        if r['no_report_ready']:
            print(f"    ⚠️  ready 但无 touch 数据: {r['no_report_ready']}")
        if r['pending_but_has_data']:
            print(f"    ⚠️  pending 却有 touch 数据: {r['pending_but_has_data']}")
        print(f"    所有可选文件齐全:  {r['all_optionals_present']}")
        print()
        print("    可选文件分布 (按数据集拥有数):")
        for n_opt, count in sorted(r['optional_distribution'].items(), key=lambda x: int(x[0])):
            bar = "█" * count if count < 50 else "█" * 50
            print(f"      {n_opt} 个可选文件: {count:4d} 数据集 {bar}")
        print()
        print("    各可选文件出现次数:")
        for name, count in sorted(r['optional_counts'].items(), key=lambda x: -x[1]):
            pct = count / max(r['ready_with_transcripts'], 1) * 100
            bar = "█" * int(pct / 2)
            print(f"      {name:20s} {count:4d}/{r['ready_with_transcripts']:d} ({pct:5.1f}%) {bar}")
        print()


def print_json(results: list) -> None:
    print(json.dumps(results, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="统计 GEO CSV 中的 touch 文件信息")
    parser.add_argument("--cosmx-only", action="store_true")
    parser.add_argument("--xenium-only", action="store_true")
    parser.add_argument("--merfish-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    platforms = []
    if args.cosmx_only:
        platforms.append("cosmx")
    if args.xenium_only:
        platforms.append("xenium")
    if args.merfish_only:
        platforms.append("merfish")
    if not platforms:
        platforms = ["cosmx", "xenium", "merfish"]

    results = [analyze_platform(p) for p in platforms]

    if args.json:
        print_json(results)
    else:
        print_report(results)


if __name__ == "__main__":
    main()
