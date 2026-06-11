#!/usr/bin/env python3
"""从 outs.zip/RAW.tar 恢复被误删的 .zarr.zip 文件。"""
import os, sys, zipfile, shutil

def restore_from_outszip(gsm_dir, gsm, zip_path):
    """从 *_outs.zip 提取 zarr.zip 到 GSM 目录。"""
    zf = zipfile.ZipFile(zip_path)
    count = 0
    for name in zf.namelist():
        if not name.endswith(".zarr.zip"):
            continue
        if "analysis" in name:
            continue
        fname = name.split("/")[-1]
        dest = os.path.join(gsm_dir, f"{gsm}_{fname}")
        if os.path.exists(dest):
            print(f"  skip (exists): {fname}")
            continue
        with zf.open(name) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)
        print(f"  -> {gsm}_{fname}")
        count += 1
    return count

# GSE243168: from *_outs.zip
base = "/data3/yangxr002/Xenium_GEO/GSE243168"
print("=== GSE243168 ===")
for gsm in os.listdir(base):
    gsm_dir = os.path.join(base, gsm)
    if not os.path.isdir(gsm_dir):
        continue
    for f in os.listdir(gsm_dir):
        if f.endswith("_outs.zip"):
            n = restore_from_outszip(gsm_dir, gsm, os.path.join(gsm_dir, f))
            print(f"  {gsm}: {n} zarr files restored")
            break
