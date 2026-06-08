#!/usr/bin/env python3
"""Detail check of gsm_other and other categories."""

import subprocess, os

base = "/data3/yangxr002/Xenium/"

result = subprocess.run(["find", base, "-maxdepth", "2", "-type", "d", "-name", "D*"],
                       capture_output=True, text=True, timeout=30)
d_dirs = sorted(result.stdout.strip().split("\n")) if result.stdout.strip() else []

print("=== gsm_other 示例 ===")
shown = 0
for dd in d_dirs:
    result = subprocess.run(["find", dd, "-maxdepth", "1", "-type", "f"],
                           capture_output=True, text=True, timeout=10)
    fnames = [os.path.basename(f) for f in result.stdout.strip().split("\n") if f]
    gsm_files = [f for f in fnames if f.startswith("GSM")]
    has_standard = any(f in ("transcripts.csv.gz", "transcripts.csv") for f in fnames)
    has_outs_zip = any(f.endswith("_outs.zip") for f in fnames)
    has_gsm_parquet_gz = any(f.startswith("GSM") and f.endswith("_transcripts.parquet.gz") for f in fnames)
    has_gsm_csv_gz = any(f.startswith("GSM") and f.endswith("_transcripts.csv.gz") for f in fnames)
    
    if gsm_files and not has_outs_zip and not has_gsm_parquet_gz and not has_gsm_csv_gz:
        shown += 1
        if shown <= 5:
            print(f"\n  {dd}:")
            for fn in sorted(fnames)[:10]:
                print(f"    {fn}")
            # Check naming pattern
            has_dash = any("-transcripts" in f for f in gsm_files)
            print(f"    [pattern: dash={has_dash}, gsm_count={len(gsm_files)}]")

print("\n=== 'other' 示例 ===")
shown = 0
for dd in d_dirs:
    result = subprocess.run(["find", dd, "-maxdepth", "1", "-type", "f"],
                           capture_output=True, text=True, timeout=10)
    fnames = [os.path.basename(f) for f in result.stdout.strip().split("\n") if f]
    gsm_files = [f for f in fnames if f.startswith("GSM")]
    has_standard = any(f in ("transcripts.csv.gz", "transcripts.csv") for f in fnames)
    
    if not gsm_files and not has_standard and len(fnames) > 0:
        shown += 1
        if shown <= 5:
            print(f"\n  {dd}:")
            for fn in sorted(fnames)[:10]:
                print(f"    {fn}")
