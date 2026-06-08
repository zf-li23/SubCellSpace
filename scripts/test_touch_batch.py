"""
批量测试 subcellspace touch 在 GEO 数据集上的表现。
在集群上运行: python3 scripts/test_touch_batch.py
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.touch import touch

TEST_PATHS = [
    # ── CosMx GEO (9 samples, 6 GSEs) ──
    "/data3/yangxr002/CosMx_GEO/GSE305978/GSM9190966/",
    "/data3/yangxr002/CosMx_GEO/GSE277782/GSM8529621-GSM8529624/",
    "/data3/yangxr002/CosMx_GEO/GSE277782/GSM8529618-GSM8529620/",
    "/data3/yangxr002/CosMx_GEO/GSE292268/GSM8855042/",
    "/data3/yangxr002/CosMx_GEO/GSE292268/GSM8855043/",
    "/data3/yangxr002/CosMx_GEO/GSE277441/GSM8522535/",
    "/data3/yangxr002/CosMx_GEO/GSE277441/GSM8522534/",
    "/data3/yangxr002/CosMx_GEO/GSE283625/GSM8668172-GSM8668179/",
    "/data3/yangxr002/CosMx_GEO/GSE291308/GSM8833258/",
    # ── Xenium GEO (11 samples, 6 GSEs) ──
    "/data3/yangxr002/Xenium_GEO/GSE313081/GSM9360616/",
    "/data3/yangxr002/Xenium_GEO/GSE313081/GSM9360614/",
    "/data3/yangxr002/Xenium_GEO/GSE320403/GSM9542521/",
    "/data3/yangxr002/Xenium_GEO/GSE290468/GSM8815002/",
    "/data3/yangxr002/Xenium_GEO/GSE290468/GSM8814979/",
    "/data3/yangxr002/Xenium_GEO/GSE266690/GSM8253800/",
    "/data3/yangxr002/Xenium_GEO/GSE266690/GSM8253792/",
    "/data3/yangxr002/Xenium_GEO/GSE308148/GSM9238737/",
    "/data3/yangxr002/Xenium_GEO/GSE308148/GSM9238738/",
    "/data3/yangxr002/Xenium_GEO/GSE313636/GSM9371395/",
    "/data3/yangxr002/Xenium_GEO/GSE313636/GSM9371393/",
    # ── MERFISH GEO (11 samples, 7 GSEs) ──
    "/data3/yangxr002/MERFISH_GEO/GSE274617/GSM8453700/",
    "/data3/yangxr002/MERFISH_GEO/GSE269617/GSM8323064/",
    "/data3/yangxr002/MERFISH_GEO/GSE269617/GSM8323033/",
    "/data3/yangxr002/MERFISH_GEO/GSE319949/GSM9530210/",
    "/data3/yangxr002/MERFISH_GEO/GSE319949/GSM9530211/",
    "/data3/yangxr002/MERFISH_GEO/GSE313704/GSM9372789/",
    "/data3/yangxr002/MERFISH_GEO/GSE313704/GSM9372791/",
    "/data3/yangxr002/MERFISH_GEO/GSE301696/GSM9087497/",
    "/data3/yangxr002/MERFISH_GEO/GSE301696/GSM9087496/",
    "/data3/yangxr002/MERFISH_GEO/GSE330849/GSM9733697/",
    "/data3/yangxr002/MERFISH_GEO/GSE330849/GSM9733696/",
]

# Also test CosMx merged (GSM range - needs platform hint)
EXTRA_PATHS = []


def run_batch(paths, label):
    print(f"\n{'='*70}")
    print(f"  {label} ({len(paths)} datasets)")
    print(f"{'='*70}")
    
    results = []
    for path in paths:
        path = path.rstrip("/")
        # Extract GSE and GSM from path
        gse_match = __import__("re").search(r"(GSE\d+)", path)
        gsm_match = __import__("re").search(r"(GSM[\d\-]+)", path)
        gse = gse_match.group(1) if gse_match else "?"
        gsm = gsm_match.group(1) if gsm_match else "?"
        
        try:
            r = touch(path)
            s = r.to_dict()["summary"]
            
            status = "✅" if s["required_found"] > 0 else "⚠️"
            plat = r.platform or "none"
            results.append({
                "path": path, "gse": f"GSE{gse}", "gsm": gsm,
                "platform": plat,
                "required": s["required_found"],
                "total": s["total_files"],
                "optional": s["optional_found"],
                "unexpected": s["unexpected"],
                "missing": r.missing_required,
                "error": None,
            })
            print(f"  {status} {plat:8s} | req={s['required_found']}/{s['total_files']} "
                  f"| opt={s['optional_found']} | unexp={s['unexpected']} | {gse}/{gsm}")
        except Exception as e:
            results.append({
                "path": path, "gse": f"GSE{gse}", "gsm": gsm,
                "platform": None, "required": 0, "total": 0,
                "optional": 0, "unexpected": 0, "missing": [],
                "error": str(e),
            })
            print(f"  ❌ ERROR: {e}")
    
    return results


def summarize(results, label):
    total = len(results)
    success = sum(1 for r in results if r["error"] is None and r["required"] > 0)
    no_data = sum(1 for r in results if r["error"] is None and r["required"] == 0)
    errors = sum(1 for r in results if r["error"] is not None)
    
    platforms = {}
    for r in results:
        p = r["platform"] or "none"
        platforms[p] = platforms.get(p, 0) + 1
    
    total_unexp = sum(r["unexpected"] for r in results if r["error"] is None)
    
    print(f"\n  ── {label} Summary ──")
    print(f"  Total: {total} | ✅ OK: {success} | ⚠️  No data: {no_data} | ❌ Error: {errors}")
    print(f"  Platforms: {platforms}")
    print(f"  Total unexpected files: {total_unexp}")
    
    if no_data > 0:
        print(f"  Datasets with 0 required files found:")
        for r in results:
            if r["error"] is None and r["required"] == 0:
                print(f"    - {r['gse']}/{r['gsm']} (detected: {r['platform']})")
    
    if errors > 0:
        print(f"  Errors:")
        for r in results:
            if r["error"] is not None:
                print(f"    - {r['gse']}/{r['gsm']}: {r['error']}")


if __name__ == "__main__":
    # Group by platform prefix for reporting
    cosmx_paths = [p for p in TEST_PATHS if "CosMx_GEO" in p]
    xenium_paths = [p for p in TEST_PATHS if "Xenium_GEO" in p]
    merfish_paths = [p for p in TEST_PATHS if "MERFISH_GEO" in p]
    
    all_results = []
    for paths, label in [(cosmx_paths, "CosMx GEO"), (xenium_paths, "Xenium GEO"), (merfish_paths, "MERFISH GEO")]:
        results = run_batch(paths, label)
        summarize(results, label)
        all_results.extend(results)
        print()
    
    # Overall summary
    print(f"\n{'='*70}")
    print(f"  OVERALL: {len(all_results)} datasets tested")
    print(f"{'='*70}")
    ok = sum(1 for r in all_results if r["error"] is None and r["required"] > 0)
    no_data = sum(1 for r in all_results if r["error"] is None and r["required"] == 0)
    err = sum(1 for r in all_results if r["error"] is not None)
    print(f"  ✅ Files found: {ok} | ⚠️  No required files: {no_data} | ❌ Errors: {err}")
    
    # Save full results
    out = "/tmp/touch_batch_results.json"
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  Full results saved to {out}")
