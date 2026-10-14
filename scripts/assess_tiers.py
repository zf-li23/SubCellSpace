"""对清单里的每个样本做快速数据分级（只看文件列表和转录本前若干行），输出 TSV。

    python scripts/assess_tiers.py lists/all_ready.tsv -o tiers.tsv     # 清单由 make_sample_list.py 生成
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tiers import quick_tier  # noqa: E402

FIELDS = ["GSE", "GSM", "platform", "data_tier", "has_transcripts", "has_cell_id", "has_boundaries",
          "has_matrix", "has_cell_table", "has_images", "error", "sample_dir"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample_list", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()
    lines = [line.rstrip("\n").split("\t") for line in args.sample_list.read_text().splitlines() if line.strip()]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        w.writeheader()
        for i, (plat, sample_dir, gse, gsm, *_rest) in enumerate(lines, 1):
            try:
                row = quick_tier(sample_dir, platform=plat)
            except Exception as exc:  # record and continue
                row = {"platform": plat, "data_tier": "D", "error": f"{type(exc).__name__}: {exc}"[:200]}
            w.writerow({**{k: row.get(k, "") for k in FIELDS}, "GSE": gse, "GSM": gsm, "sample_dir": sample_dir})
            f.flush()
            if i % 50 == 0:
                print(f"{i}/{len(lines)}", flush=True)


if __name__ == "__main__":
    main()
