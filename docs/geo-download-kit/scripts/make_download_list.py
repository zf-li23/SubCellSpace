#!/usr/bin/env python3
"""从 GEO 登记表（CSV）生成下载清单。

用途：把「要下载什么」从硬编码的 GSE 数组里解放出来。
旧脚本（download_cosmx_geo.sh / download_missing_tars.sh）把 40+ 个 GSE
写死在 shell 里，改一次要动代码，而且容易和登记表脱节。这里改为从 CSV 派生。

输入 CSV 至少需要两列：GSE、status
  （本项目的 data/{platform}_geo.csv 就是这种格式，21 列）

输出 TSV，三列：GSE<TAB>GSM数<TAB>备注
  可直接喂给 pull_from_jumpbox.sh / extract_array_template.slurm

用法：
    python3 make_download_list.py data/xenium_geo.csv \
        --status pending --exclude-status error \
        -o xenium_pending.tsv

    # 只看 GSM 数 >= 2 的（过滤掉单样本 GSE）
    python3 make_download_list.py data/cosmx_geo.csv --min-gsms 2
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path", help="GEO 登记表 CSV（需含 GSE、status 列）")
    ap.add_argument("-o", "--out", default="-", help="输出 TSV 路径（默认 stdout）")
    ap.add_argument("--status", default="pending", help="只保留该 status（默认 pending；传 all 表示不过滤）")
    ap.add_argument("--exclude-status", default="", help="排除该 status（逗号分隔）")
    ap.add_argument("--min-gsms", type=int, default=1, help="GSE 内最少的 GSM 行数（默认 1）")
    ap.add_argument("--sample-col", default="", help="样本列名（CosMx 是 sample_name，其余是 GSM；留空则自动探测）")
    args = ap.parse_args()

    with open(args.csv_path, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("GSE", "").strip()]

    if not rows:
        print("错误：CSV 为空或没有 GSE 列", file=sys.stderr)
        return 1

    sample_col = args.sample_col
    if not sample_col:
        sample_col = "sample_name" if "sample_name" in rows[0] else "GSM"

    gse_status: dict[str, Counter] = {}
    for r in rows:
        gse = r["GSE"].strip()
        gse_status.setdefault(gse, Counter())[r.get("status", "").strip()] += 1

    excl = {s.strip() for s in args.exclude_status.split(",") if s.strip()}

    lines = []
    for gse, cnt in sorted(gse_status.items()):
        total = sum(cnt.values())
        # 一个 GSE 内的状态取多数票，用于过滤
        dominant = cnt.most_common(1)[0][0]
        if args.status != "all" and dominant != args.status:
            continue
        if excl & set(cnt.keys()):
            # 只有在「该 GSE 的所有行都落在被排除状态」时才整条排除
            if set(cnt.keys()) <= excl:
                continue
        if total < args.min_gsms:
            continue
        note = ",".join(f"{k}:{v}" for k, v in sorted(cnt.items()))
        lines.append(f"{gse}\t{total}\t{note}")

    out = sys.stdout if args.out == "-" else open(args.out, "w", encoding="utf-8")
    try:
        out.write(f"# source={args.csv_path} status={args.status} min_gsms={args.min_gsms}\n")
        for line in lines:
            out.write(line + "\n")
    finally:
        if out is not sys.stdout:
            out.close()

    print(f"[make_download_list] {len(lines)} 个 GSE → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
