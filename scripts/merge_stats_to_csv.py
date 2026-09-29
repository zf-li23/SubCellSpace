"""
将 stats 结果合并回 GEO CSV — merge_stats_to_csv.py
====================================================
读取 outputs/stats_results/stats_{platform}.csv，将统计结果
合并回 data/{platform}_geo.csv（新增 7 列），不修改已有列。

用法:
    python3 scripts/merge_stats_to_csv.py                          # 全部平台
    python3 scripts/merge_stats_to_csv.py --cosmx-only             # 只 CosMx
    python3 scripts/merge_stats_to_csv.py --xenium-only --dry-run  # 预览
"""

import argparse
import csv
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("merge_stats")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "outputs" / "stats_results"

STATS_COLUMNS = [
    "n_transcripts",
    "n_cells",
    "n_genes",
    "n_fovs",
    "gene_panel_size",
    "median_transcripts",
    "median_genes",
]

PLATFORM_CONFIG = {
    "cosmx": {
        "geo_csv": DATA_DIR / "cosmx_geo.csv",
        "stats_csv": RESULTS_DIR / "stats_cosmx.csv",
        "key": "sample_name",
    },
    "xenium": {
        "geo_csv": DATA_DIR / "xenium_geo.csv",
        "stats_csv": RESULTS_DIR / "stats_xenium.csv",
        "key": "GSM",
    },
    "merfish": {
        "geo_csv": DATA_DIR / "merfish_geo.csv",
        "stats_csv": RESULTS_DIR / "stats_merfish.csv",
        "key": "GSM",
    },
}


def merge_platform(platform: str, dry_run: bool = False) -> None:
    cfg = PLATFORM_CONFIG[platform]
    stats_path = cfg["stats_csv"]
    geo_path = cfg["geo_csv"]

    if not stats_path.exists():
        logger.warning(f"  Stats file not found: {stats_path}")
        return
    if not geo_path.exists():
        logger.error(f"  GEO CSV not found: {geo_path}")
        return

    # ── 读取 stats 结果 ──
    stats_map = {}  # {gse+key: row}
    with open(stats_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gse = row.get("GSE", "").strip()
            key = row.get("sample_name", "").strip()
            if gse and key:
                stats_map[(gse, key)] = row

    logger.info(f"  Loaded {len(stats_map)} stats results from {stats_path.name}")

    # ── 读取 GEO CSV ──
    with open(geo_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    # 确保 stats 列存在
    for col in STATS_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)

    # ── 逐行匹配并填入 ──
    n_matched = 0
    n_skipped = 0
    n_ok_status = 0
    key_col = cfg["key"]

    for row in rows:
        gse = row.get("GSE", "").strip()
        key = row.get(key_col, "").strip()
        stats_row = stats_map.get((gse, key))

        if stats_row is None:
            n_skipped += 1
            continue

        status = stats_row.get("status", "").strip()
        if status == "ok":
            for col in STATS_COLUMNS:
                row[col] = stats_row.get(col, "")
            n_matched += 1
            n_ok_status += 1
        elif status == "no_data":
            # Dataset dir not found - leave blank
            n_skipped += 1
        else:
            # error status - leave blank
            n_skipped += 1

    logger.info(f"  Matched: {n_matched} OK, {n_skipped} skipped (no data / not found)")

    if dry_run:
        logger.info(f"  [DRY RUN] Would write {len(rows)} rows to {geo_path.name}")
        return

    # ── 写回 ──
    with open(geo_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"  Written {len(rows)} rows to {geo_path.name}")
    logger.info(f"  Stats columns added: {STATS_COLUMNS}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge stats results back into GEO CSVs")
    parser.add_argument("--cosmx-only", action="store_true")
    parser.add_argument("--xenium-only", action="store_true")
    parser.add_argument("--merfish-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
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

    for plat in platforms:
        merge_platform(plat, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
