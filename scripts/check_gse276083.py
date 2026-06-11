#!/usr/bin/env python3
"""检查 GSE276083 解压后的文件完整性。"""
import os, json

BASE = "/data3/yangxr002/CosMx_GEO/GSE276083"

required_patterns = ["*tx_file.csv*"]
optional_patterns = ["*[_-]polygons.csv*", "*_exprMat_file*", 
                     "*_metadata_file*", "*_fov_position*"]

import fnmatch

def check_gsm(gsm_dir):
    files = os.listdir(gsm_dir)
    req_ok = 0
    opt_ok = 0
    opt_found = []
    for f in files:
        for pat in required_patterns:
            if fnmatch.fnmatch(f, pat):
                req_ok += 1
        for pat in optional_patterns:
            if fnmatch.fnmatch(f, pat):
                opt_ok += 1
                opt_found.append(f.split(".csv")[0][-40:] + ".csv...")
    return req_ok, opt_ok, opt_found, len(files)

results = {}
total_req = 0
total_opt = 0
for gsm in sorted(os.listdir(BASE)):
    gsm_dir = os.path.join(BASE, gsm)
    if not os.path.isdir(gsm_dir):
        continue
    req, opt, opts, nf = check_gsm(gsm_dir)
    results[gsm] = {"required": req, "optional": opt, "total_files": nf}
    total_req += req
    total_opt += opt
    status = "✅" if req >= 1 else "❌"
    print(f"  {status} {gsm}: req={req}, opt={opt}, total_files={nf}")
    if req == 0:
        print(f"      Files: {os.listdir(gsm_dir)}")

print(f"\nTotal: {total_req}/{len(results)} required=1, avg optional={total_opt/max(len(results),1):.1f}")
print(f"All GSM count: {len(results)}")
print(json.dumps({"total_gsm": len(results), "req_ok": total_req, "opt_total": total_opt}, indent=2))
