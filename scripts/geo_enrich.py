#!/usr/bin/env python3
"""
GEO 批量元数据填充入口脚本
===========================
读取三平台 CSV，对每个唯一 GSE 调用 GEO API，补充元数据列。

用法:
    python3 scripts/geo_enrich.py                    # 处理全部
    python3 scripts/geo_enrich.py --dry-run           # 仅预览
    python3 scripts/geo_enrich.py --delay 1.0         # 更慢的 API 频率
    python3 scripts/geo_enrich.py --cosmx-only        # 只处理 CosMx
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.geo.enrich import enrich_all, PLATFORM_CSVS


def main():
    parser = argparse.ArgumentParser(description="GEO 批量元数据填充")
    parser.add_argument("--delay", type=float, default=0.35,
                        help="API 调用间隔秒数（默认 0.35）")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览不实际写入")
    parser.add_argument("--cosmx-only", action="store_true",
                        help="只处理 CosMx")
    parser.add_argument("--xenium-only", action="store_true",
                        help="只处理 Xenium")
    parser.add_argument("--merfish-only", action="store_true",
                        help="只处理 MERFISH")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="详细输出")
    
    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")
    logger = logging.getLogger(__name__)
    
    # 筛选平台
    platforms = list(PLATFORM_CSVS)
    if args.cosmx_only:
        platforms = [p for p in platforms if "cosmx" in p[0]]
    if args.xenium_only:
        platforms = [p for p in platforms if "xenium" in p[0]]
    if args.merfish_only:
        platforms = [p for p in platforms if "merfish" in p[0]]
    
    csv_dir = Path(__file__).resolve().parent.parent / "data"
    
    logger.info("=" * 50)
    logger.info("GEO 元数据填充")
    logger.info(f"CSV 目录: {csv_dir}")
    logger.info(f"API 延迟: {args.delay}s")
    if args.dry_run:
        logger.info("【干跑模式】不会写入文件")
    logger.info("=" * 50)
    
    # 预览
    from src.geo.enrich import get_unique_gses
    for fname, gsm_col, _ in platforms:
        csv_path = csv_dir / fname
        if not csv_path.exists():
            continue
        gses = get_unique_gses(csv_path, gsm_col)
        logger.info(f"\n{fname}: {len(gses)} 个唯一 GSE")
        for gse in gses:
            logger.info(f"  {gse}")
    
    if args.dry_run:
        logger.info("\n干跑结束，未写入任何文件。")
        return
    
    # 执行
    results = enrich_all(delay=args.delay, csv_dir=csv_dir, platforms=platforms)
    
    logger.info("\n" + "=" * 50)
    logger.info("完成！")
    for fname, total in results.items():
        logger.info(f"  {fname}: {total} 行已更新")


if __name__ == "__main__":
    main()
