#!/usr/bin/env python3
"""Check uncertain Xenium categories: needs_extraction and no_transcript_found."""
import subprocess, os
from pathlib import Path
from collections import Counter

base = "/data3/yangxr002/Xenium/"

result = subprocess.run(["find", base, "-maxdepth", "2", "-type", "d", "-name", "D*"],
                       capture_output=True, text=True, timeout=30)
d_dirs = sorted(result.stdout.strip().split("\n")) if result.stdout.strip() else []

no_tx = []
need_extract = []

for dd in d_dirs:
    directory = Path(dd)
    files = list(directory.iterdir())
    fnames = [f.name for f in files if f.is_file()]
    
    has_tx = any(f in ("transcripts.csv.gz", "transcripts.csv", "transcripts.parquet") for f in fnames)
    has_gsm_tx = any("transcripts" in f and (f.endswith(".csv.gz") or f.endswith(".parquet.gz") or f.endswith(".parquet")) for f in fnames)
    
    if not has_tx and not has_gsm_tx:
        no_tx.append((directory.parent.name, directory.name, fnames[:8]))
    
    has_zip = any(f.endswith(".zip") and not f.endswith(".zarr.zip") for f in fnames)
    has_tar = any(f.endswith(".tar.gz") for f in fnames)
    if has_zip or has_tar:
        zip_files = [f for f in fnames if f.endswith(".zip") and not f.endswith(".zarr.zip")]
        tar_files = [f for f in fnames if f.endswith(".tar.gz")]
        need_extract.append((directory.parent.name, directory.name, zip_files + tar_files, bool(has_gsm_tx)))

print("=== needs_extraction 详情 ===")
print(f"总数: {len(need_extract)}")
for proj, did, archives, also_has_tx in need_extract[:15]:
    has_str = " [ALSO has transcript]" if also_has_tx else ""
    print(f"  {proj}/{did}: {archives}{has_str}")

# Count
extract_only = sum(1 for _, _, a, tx in need_extract if not tx)
extract_and_tx = sum(1 for _, _, a, tx in need_extract if tx)
print(f"\n  只有 zip/tar (无 transcripts): {extract_only}")
print(f"  有 zip/tar 同时有 transcripts: {extract_and_tx}")

print(f"\n=== no_transcript_found 详情 (前20) ===")
print(f"总数: {len(no_tx)}")
for proj, did, fnames in no_tx[:20]:
    print(f"  {proj}/{did}:")
    for fn in fnames:
        print(f"    - {fn}")

# Show project distribution for no_tx
proj_cnt = Counter(p for p, _, _ in no_tx)
print(f"\nno_transcript_found 按项目分布 (前10):")
for p, c in proj_cnt.most_common(10):
    print(f"  {p}: {c}")
