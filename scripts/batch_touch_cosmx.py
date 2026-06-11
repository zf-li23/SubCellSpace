#!/usr/bin/env python3
"""CosMx GEO touch scan — 扫描所有 GSE/GSM 目录并报告可选文件分布。"""
import os, sys, json

sys.path.insert(0, os.path.expanduser("~/zf-li23/subcellspace"))
from src.touch import touch

BASE = "/data3/yangxr002/CosMx_GEO"
GSEs = sorted([d for d in os.listdir(BASE) if d.startswith("GSE")])

results = {"total": 0, "ok": 0, "no_data": 0, "errors": 0,
           "opt_dist": {}, "error_details": []}

for gse in GSEs:
    gse_path = os.path.join(BASE, gse)
    for gsm in sorted(os.listdir(gse_path)):
        gsm_path = os.path.join(gse_path, gsm)
        if not os.path.isdir(gsm_path):
            continue
        results["total"] += 1
        try:
            r = touch(gsm_path, platform_override="cosmx")
            s = r.to_dict()["summary"]
            if s["required_found"] >= 1:
                results["ok"] += 1
                opt = s["optional_found"]
                key = str(opt)
                results["opt_dist"][key] = results["opt_dist"].get(key, 0) + 1
            else:
                results["no_data"] += 1
        except Exception as e:
            results["errors"] += 1
            results["error_details"].append("%s/%s: %s" % (gse, gsm, str(e)))

print("CosMx Touch Scan Results")
print("=" * 50)
print("Total:     %d" % results["total"])
print("OK:        %d" % results["ok"])
print("No data:   %d" % results["no_data"])
print("Errors:    %d" % results["errors"])
print()
print("Optional file distribution:")
for k in sorted(results["opt_dist"].keys(), key=int):
    print("  opt=%s: %d" % (k, results["opt_dist"][k]))
if results["error_details"]:
    print("\nErrors:")
    for e in results["error_details"]:
        print("  " + e)

out_path = os.path.expanduser("~/zf-li23/subcellspace/touch_summary_cosmx.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print("\nSummary saved to: %s" % out_path)
