"""
批量流式统计 — 对 GEO 数据集逐条目计算 stats
===============================================
读取 GEO CSV，对每个 status=ready 的条目执行流式统计，
然后将结果写回 CSV 的新列。

用法:
    python3 scripts/batch_stats.py                         # 所有平台
    python3 scripts/batch_stats.py --cosmx-only             # 只跑 CosMx
    python3 scripts/batch_stats.py --xenium-only --dry-run  # 只预览
    python3 scripts/batch_stats.py --max-datasets 5         # 只跑前 5 个
"""

import argparse, csv, json, logging, os, shutil, sys, time
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.stats import stat_data_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_stats")

# ── 平台配置 ─────────────────────────────────────────────────────────

# GEO CSV 路径
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GEO_CSVS = {
    "cosmx":  DATA_DIR / "cosmx_geo.csv",
    "xenium": DATA_DIR / "xenium_geo.csv",
    "merfish": DATA_DIR / "merfish_geo.csv",
}

# 集群根路径
CLUSTER_ROOT = "/data3/yangxr002/"

# 需要添加的 stats 列
STATS_COLUMNS = [
    "n_transcripts",
    "n_cells",
    "n_genes",
    "n_fovs",
    "gene_panel_size",
    "median_transcripts",
    "median_genes",
]


def _ensure_stats_columns(header: list) -> list:
    """确保 header 中包含所有 stats 列，缺少则追加。"""
    out = list(header)
    for col in STATS_COLUMNS:
        if col not in out:
            out.append(col)
    return out


def _build_cluster_path(platform: str, gse: str, sample_name: str) -> str:
    """按集群约定构建数据目录路径。

    CosMx_GEO:   /data3/yangxr002/CosMx_GEO/{GSE}/{sample_name}/
    Xenium_GEO:  /data3/yangxr002/Xenium_GEO/{GSE}/{sample_name}/
    MERFISH_GEO: /data3/yangxr002/MERFISH_GEO/{GSE}/{sample_name}/
    """
    platform_dir = {
        "cosmx":  "CosMx_GEO",
        "xenium": "Xenium_GEO",
        "merfish": "MERFISH_GEO",
    }.get(platform.lower())

    if not platform_dir:
        return ""

    return f"{CLUSTER_ROOT}{platform_dir}/{gse}/{sample_name}/"


def run_batch(platform: str, dry_run: bool = False,
              max_datasets: Optional[int] = None) -> None:
    """对给定平台的所有 ready 数据集执行流式统计。"""
    csv_path = GEO_CSVS.get(platform)
    if not csv_path or not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return

    # ── 读取 CSV ──
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = _ensure_stats_columns(reader.fieldnames or [])
        rows = list(reader)

    # 筛选 ready 且未统计过的条目
    sample_col = "sample_name" if platform == "cosmx" else "GSM"
    todo = []
    for row in rows:
        if row.get("status", "").strip().lower() != "ready":
            continue
        # 跳过已有 n_transcripts 的（增量 resume）
        if row.get("n_transcripts", "").strip():
            continue
        todo.append(row)

    if not todo:
        logger.info(f"  [{platform}] No pending ready datasets to process")
        return

    if max_datasets:
        todo = todo[:max_datasets]

    logger.info(f"  [{platform}] {len(todo)} datasets to process" +
                (" (DRY RUN)" if dry_run else ""))

    # ── 逐条统计 ──
    n_ok = 0
    n_err = 0
    errors = []

    for i, row in enumerate(todo):
        gse = row.get("GSE", "").strip()
        sample = row.get(sample_col, "").strip()
        path = _build_cluster_path(platform, gse, sample)

        if not path or not os.path.isdir(path):
            logger.warning(f"  [{i+1}/{len(todo)}] Directory not found: {path}")
            row["n_transcripts"] = ""
            for col in STATS_COLUMNS[1:]:
                row[col] = ""
            errors.append(f"{gse}/{sample}: directory not found")
            n_err += 1
            continue

        logger.info(f"  [{i+1}/{len(todo)}] {gse}/{sample}")

        if dry_run:
            continue

        result = stat_data_dir(Path(path), platform=platform)

        if result.error:
            logger.warning(f"  ERROR: {result.error}")
            row["n_transcripts"] = ""
            for col in STATS_COLUMNS[1:]:
                row[col] = ""
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
            n_ok += 1

            logger.info(f"    → {result.n_transcripts:,} tx, {result.n_cells:,} cells, "
                        f"{result.n_genes:,} genes")

        # 每 10 条增量保存一次
        if (i + 1) % 10 == 0 and not dry_run:
            _write_csv(csv_path, fieldnames, rows)
            logger.info(f"    [checkpoint saved at {i+1}/{len(todo)}]")

    # ── 最终保存 ──
    if not dry_run:
        _write_csv(csv_path, fieldnames, rows)

    # ── 统计汇总 ──
    logger.info(f"  [{platform}] Done: {n_ok} OK, {n_err} errors")
    if errors:
        for e in errors[:10]:
            logger.warning(f"    {e}")
        if len(errors) > 10:
            logger.warning(f"    ... and {len(errors)-10} more")


def _write_csv(path: Path, fieldnames: list, rows: list) -> None:
    """写 CSV，先备份。"""
    # 备份
    backup = path.parent / f"{path.stem}_copy{path.suffix}"
    if not backup.exists():
        shutil.copy2(path, backup)
        logger.info(f"  Backup created: {backup.name}")

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"  Written {len(rows)} rows to {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch streaming stats for GEO datasets")
    parser.add_argument("--cosmx-only", action="store_true", help="CosMx only")
    parser.add_argument("--xenium-only", action="store_true", help="Xenium only")
    parser.add_argument("--merfish-only", action="store_true", help="MERFISH only")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--max-datasets", type=int, default=None,
                        help="Max datasets to process (for testing)")
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
        run_batch(plat, dry_run=args.dry_run, max_datasets=args.max_datasets)


if __name__ == "__main__":
    main()
