"""第 3 步：删除"压缩版 + 解压版"内容完全相同的文件对中多余的一份（默认 dry-run）。

约定（沿用 touch normalize 与 Phase 5 的 Xenium 预处理）：
  二进制（parquet / h5 / ome.tif …）保留解压版 —— 读取需要随机访问，.gz 必须整体解压才能读；
  文本（csv / tsv）保留 .gz —— 可流式读取，效率相同、体积更小。
只处理 verify_pairs.sh 判为 SAME 的对；删除前再次核对两个文件的大小未变。
每删一个文件，都在该样本目录的 subcellspace_dedup_manifest.json 里记录原文件名、大小、md5 和保留的文件，
因此 GEO 原始文件名与校验信息不会丢失（解压版常被改过名）。

    python apply_dedup.py dedup/part_*.verified            # 只打印计划
    python apply_dedup.py dedup/part_*.verified --apply    # 执行
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime

MANIFEST = "subcellspace_dedup_manifest.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("verified", nargs="+")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rows = []
    for path in args.verified:
        with open(path, encoding="utf-8") as f:
            rows += [line.rstrip("\n").split("\t") for line in f if line.strip()]

    freed = n_ok = n_skip = 0
    for d, gz, gz_size, plain, plain_size, _kind, keep, result, md5 in rows:
        drop, kept = (gz, plain) if keep == "plain" else (plain, gz)
        drop_size = int(gz_size if keep == "plain" else plain_size)
        if result != "SAME":
            n_skip += 1
            print(f"SKIP {result}\t{d}/{drop}")
            continue
        try:
            unchanged = os.path.getsize(f"{d}/{gz}") == int(gz_size) and os.path.getsize(f"{d}/{plain}") == int(plain_size)
        except OSError:
            unchanged = False
        if not unchanged:
            n_skip += 1
            print(f"SKIP changed/missing\t{d}/{drop}")
            continue
        print(f"{'DELETE' if args.apply else 'WOULD DELETE'}\t{d}/{drop}\t(keep {kept})")
        if args.apply:
            mpath = os.path.join(d, MANIFEST)
            entries = []
            if os.path.exists(mpath):
                with open(mpath, encoding="utf-8") as f:
                    entries = json.load(f)
            entries.append({
                "deleted": drop, "deleted_size": drop_size, "kept": kept, "content_md5": md5,
                "reason": "same content as the kept file (gzip -dc md5 match)",
                "date": datetime.now(UTC).isoformat(timespec="seconds"),
            })
            with open(mpath, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
            os.remove(os.path.join(d, drop))
        freed += drop_size
        n_ok += 1
    verb = "freed" if args.apply else "would free"
    print(f"\n{n_ok} files {verb} {freed / 1e9:.1f} GB; {n_skip} skipped")


if __name__ == "__main__":
    main()
