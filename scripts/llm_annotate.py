#!/usr/bin/env python3
"""
LLM 批量标注入口脚本 — tissue / disease_state
================================================
读取三平台 CSV（需先运行 geo_enrich.py 补充 GEO 列），
按 GSE 分组调用 DeepSeek API，逐 GSM 输出组织/疾病标注。

用法:
    python3 scripts/llm_annotate.py                           # 全部平台
    python3 scripts/llm_annotate.py --cosmx-only               # 只 CosMx
    python3 scripts/llm_annotate.py --dry-run                  # 预览
    python3 scripts/llm_annotate.py --delay 1.0 --model deepseek-chat
"""

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.geo.llm_annotate import PLATFORM_CSVS, annotate_all, read_gsm_titles


def main():
    p = argparse.ArgumentParser(description="LLM 批量标注 tissue / disease_state")
    p.add_argument("--delay", type=float, default=0.5,
                   help="API 调用间隔秒数（默认 0.5）")
    p.add_argument("--model", default="deepseek-v4-flash",
                   help="DeepSeek 模型名（默认 %(default)s）")
    p.add_argument("--base-url", default="https://api.deepseek.com",
                   help="API 地址（默认 %(default)s）")
    p.add_argument("--dry-run", action="store_true", help="仅预览不执行")
    p.add_argument("--cosmx-only", action="store_true")
    p.add_argument("--xenium-only", action="store_true")
    p.add_argument("--merfish-only", action="store_true")
    p.add_argument("--api-key", default=None,
                   help="DeepSeek API key，默认读取 DEEPSEEK_API_KEY 环境变量")
    p.add_argument("--verbose", "-v", action="store_true")

    args = p.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")
    logger = logging.getLogger(__name__)

    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key and not args.dry_run:
        logger.error("❌ API key required. Set --api-key or DEEPSEEK_API_KEY")
        sys.exit(1)

    platforms = list(PLATFORM_CSVS)
    if args.cosmx_only:
        platforms = [p for p in platforms if "cosmx" in p[0]]
    if args.xenium_only:
        platforms = [p for p in platforms if "xenium" in p[0]]
    if args.merfish_only:
        platforms = [p for p in platforms if "merfish" in p[0]]

    csv_dir = Path(__file__).resolve().parent.parent / "data"

    logger.info("=" * 50)
    logger.info("LLM 批量标注 — tissue / disease_state")
    logger.info(f"模型: {args.model}  |  API 延迟: {args.delay}s")
    logger.info("=" * 50)

    for fname, gsm_col in platforms:
        csv_path = csv_dir / fname
        if not csv_path.exists():
            continue
        groups = read_gsm_titles(csv_path, gsm_col)
        total_gsm = sum(len(v) for v in groups.values())
        logger.info(f"\n{fname}: {len(groups)} GSEs, {total_gsm} GSM")

        if args.dry_run:
            for gse, gsms in list(groups.items())[:5]:
                logger.info(f"  {gse} ({len(gsms)} GSM)")
            if len(groups) > 5:
                logger.info(f"  ... and {len(groups)-5} more")

    if args.dry_run:
        logger.info("\n干跑结束。使用 --api-key 或 DEEPSEEK_API_KEY 执行。")
        return

    if not api_key:
        logger.error("❌ API key required.")
        sys.exit(1)

    results = annotate_all(
        api_key=api_key,
        model=args.model,
        base_url=args.base_url,
        delay=args.delay,
        csv_dir=csv_dir,
        platforms=platforms,
    )

    logger.info("\n" + "=" * 50)
    logger.info("完成！")
    for fname, n in results.items():
        logger.info(f"  {fname}: {n} fields updated")


if __name__ == "__main__":
    main()
