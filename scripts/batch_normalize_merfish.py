#!/usr/bin/env python3
"""MERFISH GEO touch normalize — 扫描所有 GSE/GSM 目录并标准化。"""
import os, sys, json, time
sys.path.insert(0, os.path.expanduser("~/zf-li23/subcellspace"))
from src.touch import touch

base = "/data3/yangxr002/MERFISH_GEO"
gse_dirs = sorted([d for d in os.listdir(base) if d.startswith("GSE") and os.path.isdir(os.path.join(base, d))])

results = []
total = 0
ok = 0
no_data = 0
errors = 0

for gse in gse_dirs:
    gse_path = os.path.join(base, gse)
    gsms = sorted([d for d in os.listdir(gse_path) if d.startswith("GSM") and os.path.isdir(os.path.join(gse_path, d))])
    for gsm in gsms:
        gsm_path = os.path.join(gse_path, gsm)
        try:
            r = touch(gsm_path, normalize=True)
            d = r.to_dict()
            s = d["summary"]
            total += 1
            if s["required_found"] > 0:
                ok += 1
            else:
                no_data += 1
            results.append({
                "gse": gse, "gsm": gsm, "platform": r.platform,
                "required_found": s["required_found"],
                "optional_found": s["optional_found"],
                "ok": s["required_found"] > 0,
                "actions": r.actions_taken,
            })
        except Exception as e:
            errors += 1
            results.append({"gse": gse, "gsm": gsm, "error": str(e)})

        if total % 20 == 0:
            print("  Progress: %d..." % total)

out = os.path.expanduser("~/zf-li23/subcellspace/merfish_touch_normalize_report.json")
report = {
    "summary": {"total": total, "ok": ok, "no_data": no_data, "errors": errors},
    "results": results,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
}
with open(out, "w") as f:
    json.dump(report, f, indent=2)

print("\nDone: %d total, %d OK, %d no_data, %d errors" % (total, ok, no_data, errors))
print("Report saved to %s" % out)
