"""
合并分片统计结果 — merge_stats_chunks.py
========================================
将 --chunk 分片输出的 stats_{platform}.{N}.csv 合并为一个统一的
stats_{platform}.csv，不修改原始 GEO CSV。

用法:
    python3 scripts/merge_stats_chunks.py --platform cosmx --total-chunks 3
    python3 scripts/merge_stats_chunks.py --all
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("merge_chunks")

OUTPUT_COLUMNS = [
    "GSE", "sample_name", "platform",
    "n_transcripts", "n_cells", "n_genes",
    "n_fovs", "gene_panel_size",
    "median_transcripts", "median_genes",
    "transcript_file", "status", "error_message",
]


def merge_platform(platform: str, result_dir: Path, total_chunks: int) -> None:
    merged = {}
    for i in range(total_chunks):
        chunk_path = result_dir / f"stats_{platform}.{i}.csv"
        if not chunk_path.exists():
            logger.warning(f"  Chunk file not found: {chunk_path}")
            continue
        with open(chunk_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                key = (row.get("GSE", ""), row.get("sample_name", ""))
                if key not in merged:
                    merged[key] = row
                    count += 1
        logger.info(f"  Loaded {count} unique rows from {chunk_path.name}")

    if not merged:
        logger.warning(f"  No data for {platform}")
        return

    out_path = result_dir / f"stats_{platform}.csv"
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(merged.values())
    logger.info(f"  Written {len(merged)} rows to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge chunked stats results")
    parser.add_argument("--platform", choices=["cosmx", "xenium", "merfish"])
    parser.add_argument("--all", action="store_true", help="Merge all three platforms")
    parser.add_argument("--result-dir", type=str, default="outputs/stats_results")
    parser.add_argument("--total-chunks", type=int, default=2,
                        help="Number of chunks used (default: 2)")
    args = parser.parse_args()

    result_dir = Path(args.result_dir)

    if args.all:
        for plat in ["cosmx", "xenium", "merfish"]:
            merge_platform(plat, result_dir, args.total_chunks)
    elif args.platform:
        merge_platform(args.platform, result_dir, args.total_chunks)
    else:
        print("Specify --platform or --all")
        sys.exit(1)


if __name__ == "__main__":
    main()
