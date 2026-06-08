"""
Extract individual GSM files from CosMx merged directories (GSE253474).

Merged dirs like GSM8021238-GSM8021269/ contain 164 files from 32 GSMs.
Each file has a GSM prefix (e.g., GSM8021238_TMA_A_8_*).
This script extracts them into individual GSM dirs.
"""
import os, re, shutil, sys

BASE = "/data3/yangxr002/CosMx_GEO/GSE253474"

merged_dirs = [
    "GSM8021238-GSM8021269",
    "GSM8021270-GSM8021301",
    "GSM8021302-GSM8021327",
    "GSM8021328-GSM8021353",
]

total_moved = 0

for merged_name in merged_dirs:
    merged_path = os.path.join(BASE, merged_name)
    if not os.path.isdir(merged_path):
        print(f"[SKIP] {merged_name} not found")
        continue

    print(f"\n=== {merged_name} ===")
    
    # Group files by GSM prefix
    gsm_files = {}  # gsm -> [files]
    for fname in os.listdir(merged_path):
        fpath = os.path.join(merged_path, fname)
        if not os.path.isfile(fpath):
            continue
        m = re.match(r"(GSM\d+)", fname)
        if m:
            gsm = m.group(1)
            gsm_files.setdefault(gsm, []).append(fname)
    
    print(f"  Found {len(gsm_files)} unique GSMs, {sum(len(v) for v in gsm_files.values())} files")
    
    # For each GSM, create dir and move files
    for gsm in sorted(gsm_files.keys()):
        gsm_dir = os.path.join(BASE, gsm)
        os.makedirs(gsm_dir, exist_ok=True)
        
        for fname in gsm_files[gsm]:
            src = os.path.join(merged_path, fname)
            dst = os.path.join(gsm_dir, fname)
            shutil.move(src, dst)
            total_moved += 1
        
        n = len(gsm_files[gsm])
        print(f"    {gsm}: {n} files -> {gsm_dir}")

print(f"\n✅ Total moved: {total_moved} files")

# Verify: check merged dirs are now empty
print("\n=== Verification ===")
for merged_name in merged_dirs:
    merged_path = os.path.join(BASE, merged_name)
    remaining = [f for f in os.listdir(merged_path) if os.path.isfile(os.path.join(merged_path, f))]
    print(f"  {merged_name}: {len(remaining)} files remaining (should be 0)")
