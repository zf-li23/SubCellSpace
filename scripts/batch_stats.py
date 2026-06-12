"""
批量流式统计 — 对 GEO 数据集逐条目计算 stats（输出到独立文件）
===============================================================
读取 GEO CSV，对每个 status=ready 的条目执行流式统计，
结果保存到独立的输出 CSV（如 outputs/stats_results/stats_cosmx.csv），
不修改原始 GEO CSV。

用法:
    python3 scripts/batch_stats.py                                # 所有平台
    python3 scripts/batch_stats.py --cosmx-only                    # 只跑 CosMx
    python3 scripts/batch_stats.py --xenium-only --dry-run         # 只预览
    python3 scripts/batch_stats.py --max-datasets 5                # 只跑前 5 个
    python3 scripts/batch_stats.py --output-dir outputs/stats_results
"""

import argparse, csv, logging, os, sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.stats import stat_data_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_stats")

# ── 路径配置 ─────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GEO_CSVS = {
    "cosmx":  DATA_DIR / "cosmx_geo.csv",
    "xenium": DATA_DIR / "xenium_geo.csv",
    "merfish": DATA_DIR / "merfish_geo.csv",
}
CLUSTER_ROOT = "/data3/yangxr002/"

# 输出表格的列
OUTPUT_COLUMNS = [
    "GSE", "sample_name", "platform",
    "n_transcripts", "n_cells", "n_genes",
    "n_fovs", "gene_panel_size",
    "median_transcripts", "median_genes",
    "transcript_file", "status", "error_message",
]


def _build_cluster_path(platform: str, gse: str, sample_name: str) -> str:
    """按集群约定构建数据目录路径。"""
    platform_dir = {
        "cosmx":  "CosMx_GEO",
        "xenium": "Xenium_GEO",
        "merfish": "MERFISH_GEO",
    }.get(platform.lower())
    if not platform_dir:
        return ""
    return f"{CLUSTER_ROOT}{platform_dir}/{gse}/{sample_name}/"


def _load_existing_results(output_path: Path) -> dict:
    """加载已存在的输出结果，返回 {(gse, sample): row} 字典用于增量跳过。"""
    existing = {}
    if not output_path.exists():
        return existing
    with open(output_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row.get("GSE", ""), row.get("sample_name", ""))
            existing[key] = row
    logger.info(f"  Loaded {len(existing)} existing results from {output_path.name}")
    return existing


def _save_checkpoint(output_path: Path, rows: list, fieldnames: list) -> None:
    """增量保存结果到输出文件（直接覆盖，不备份）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_batch(platform: str, output_dir: Path, dry_run: bool = False,
              max_datasets: Optional[int] = None) -> None:
    """对给定平台的所有 ready 数据集执行流式统计。"""
    csv_path = GEO_CSVS.get(platform)
    if not csv_path or not csv_path.exists():
        logger.error(f"GEO CSV not found: {csv_path}")
        return

    output_path = output_dir / f"stats_{platform}.csv"
    existing = {} if dry_run else _load_existing_results(output_path)

    # ── 读取 GEO CSV ──
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    # 筛选 ready 且未处理的条目
    sample_col = "sample_name" if platform == "cosmx" else "GSM"
    todo = []
    for row in all_rows:
        if row.get("status", "").strip().lower() != "ready":
            continue
        gse = row.get("GSE", "").strip()
        sample = row.get(sample_col, "").strip()
        key = (gse, sample)
        if key in existing:
            continue  # 增量 resume：跳过已处理的
        todo.append((gse, sample))

    if not todo:
        logger.info(f"  [{platform}] Nothing new to process")
        return

    if max_datasets:
        todo = todo[:max_datasets]

    logger.info(f"  [{platform}] {len(todo)} new datasets to process" +
                (" (DRY RUN)" if dry_run else ""))

    # ── 逐条统计 ──
    results = []
    n_ok = 0
    n_err = 0
    errors = []

    for i, (gse, sample) in enumerate(todo):
        path = _build_cluster_path(platform, gse, sample)

        row = {
            "GSE": gse,
            "sample_name": sample,
            "platform": platform,
            "n_transcripts": "",
            "n_cells": "",
            "n_genes": "",
            "n_fovs": "",
            "gene_panel_size": "",
            "median_transcripts": "",
            "median_genes": "",
            "transcript_file": "",
            "status": "",
            "error_message": "",
        }

        if not path or not os.path.isdir(path):
            logger.warning(f"  [{i+1}/{len(todo)}] Directory not found: {path}")
            row["status"] = "no_data"
            row["error_message"] = "directory not found"
            results.append(row)
            errors.append(f"{gse}/{sample}: directory not found")
            n_err += 1
            continue

        logger.info(f"  [{i+1}/{len(todo)}] {gse}/{sample}")

        if dry_run:
            row["status"] = "pending"
            results.append(row)
            continue

        result = stat_data_dir(Path(path), platform=platform)

        if result.error:
            logger.warning(f"  ERROR: {result.error}")
            row["status"] = "error"
            row["error_message"] = result.error
            errors.append(f"{gse}/{sample}: {result.error}")
            n_err += 1
        else:
            row["n_transcripts"] = str(result.n_transcripts)
            row["n_cells"] = str(result.n_cells)
            row["n_genes"] = str(result.n_genes)
            row["n_fovs"] = str(result.n_fovs or "")
            row["gene_panel_size"] = str(result.gene_panel_size or "")
            row["median_transcripts"] = f"{result.median_transcripts:.1f}" if result.median_transcripts is not None else ""
            row["median_genes"] = f"{result.median_genes:.1f}" if result.median_genes is not None else ""
            row["transcript_file"] = result.transcript_file or ""
            row["status"] = "ok"
            n_ok += 1
            logger.info(f"    → {result.n_transcripts:,} tx, {result.n_cells:,} cells, "
                        f"{result.n_genes:,} genes")

        results.append(row)

        # 每 10 条增量保存
        if (i + 1) % 10 == 0 and not dry_run:
            all_out = list(existing.values()) + results
            _save_checkpoint(output_path, all_out, OUTPUT_COLUMNS)
            logger.info(f"    [checkpoint: {i+1}/{len(todo)} saved]")

    # ── 最终保存 ──
    if not dry_run:
        all_out = list(existing.values()) + results
        _save_checkpoint(output_path, all_out, OUTPUT_COLUMNS)
        logger.info(f"  Written {len(all_out)} rows to {output_path}")

    # ── 汇总 ──
    total_ok = len(existing) + n_ok
    logger.info(f"  [{platform}] Done: +{n_ok} new OK, {n_err} errors (total OK: {total_ok})")
    if errors:
        for e in errors[:10]:
            logger.warning(f"    {e}")
        if len(errors) > 10:
            logger.warning(f"    ... and {len(errors)-10} more")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch streaming stats for GEO datasets")
    parser.add_argument("--cosmx-only", action="store_true", help="CosMx only")
    parser.add_argument("--xenium-only", action="store_true", help="Xenium only")
    parser.add_argument("--merfish-only", action="store_true", help="MERFISH only")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--max-datasets", type=int, default=None,
                        help="Max datasets to process (for testing)")
    parser.add_argument("--output-dir", type=str, default="outputs/stats_results",
                        help="Output directory for result CSVs (default: outputs/stats_results)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

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
        run_batch(plat, output_dir, dry_run=args.dry_run, max_datasets=args.max_datasets)


if __name__ == "__main__":
    main()
