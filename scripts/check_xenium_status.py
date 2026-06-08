#!/usr/bin/env python3
"""Check Xenium dataset file status on cluster and categorize."""
import subprocess, os
from collections import Counter

base = "/data3/yangxr002/Xenium/"

result = subprocess.run(["find", base, "-maxdepth", "2", "-type", "d", "-name", "D*"],
                       capture_output=True, text=True, timeout=30)
d_dirs = sorted(result.stdout.strip().split("\n")) if result.stdout.strip() else []

cats = Counter()
examples = {}

for dd in d_dirs:
    result = subprocess.run(["find", dd, "-maxdepth", "1", "-type", "f"],
                           capture_output=True, text=True, timeout=10)
    fnames = [os.path.basename(f) for f in result.stdout.strip().split("\n") if f]
    
    has_transcripts_csv = any(f in ("transcripts.csv.gz", "transcripts.csv") for f in fnames)
    has_outs_zip = any(f.endswith("_outs.zip") for f in fnames)
    has_gsm_parquet_gz = any(f.startswith("GSM") and f.endswith("_transcripts.parquet.gz") for f in fnames)
    has_gsm_csv_gz = any(f.startswith("GSM") and f.endswith("_transcripts.csv.gz") for f in fnames)
    no_files = len(fnames) == 0
    
    if no_files:
        cat = "empty"
    elif has_transcripts_csv:
        cat = "standard_ready"
    elif has_outs_zip:
        cat = "has_outs_zip"
    elif has_gsm_parquet_gz:
        cat = "gsm_parquet_gz"
    elif has_gsm_csv_gz:
        has_h5 = any(f.startswith("GSM") and f.endswith(".h5") for f in fnames)
        has_h5gz = any(f.startswith("GSM") and f.endswith(".h5.gz") for f in fnames)
        if has_h5:
            cat = "gsm_csv_h5"
        elif has_h5gz:
            cat = "gsm_csv_h5gz"
        else:
            cat = "gsm_csv_only"
    else:
        gsm_files = [f for f in fnames if f.startswith("GSM")]
        if gsm_files:
            has_zip = any(f.endswith(".zip") for f in gsm_files)
            if has_zip:
                cat = "gsm_with_zip"
            else:
                cat = "gsm_other"
        else:
            cat = "other"
    
    cats[cat] += 1
    if cat not in examples:
        examples[cat] = (dd.split("/")[-2], dd.split("/")[-1], fnames[:10])

print("=" * 60)
print("Xenium 数据集文件状态分类")
print("=" * 60)
for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
    proj, did, fnames = examples.get(cat, ("", "", []))
    print(f"\n  [{count:4d}] {cat}")
    if fnames:
        print(f"         示例 ({proj}/{did}):")
        for fn in fnames:
            print(f"           - {fn}")

print("\n" + "=" * 60)
print("可以直接摄入 (有 transcripts.csv.gz):")
ready = sum(1 for dd in d_dirs 
    if os.path.exists(os.path.join(dd, "transcripts.csv.gz")) 
    or os.path.exists(os.path.join(dd, "transcripts.csv")))
print(f"  {ready} / {len(d_dirs)}")

print("\n需要处理的文件类型汇总:")
for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
    if cat != "standard_ready" and cat != "empty":
        print(f"  {cat}: {count}")
