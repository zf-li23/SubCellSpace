"""
三平台数据库 ↔ 集群目录一致性校验。

检查每个平台 GEO CSV 中 status=ready 的行，
是否在集群上有对应的目录，反之亦然。
"""
import csv, os, re, json
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CLUSTER_BASE = "/data3/yangxr002"

PLATFORMS = {
    "CosMx": {
        "csv": DATA / "cosmx_geo.csv",
        "cluster_dir": f"{CLUSTER_BASE}/CosMx_GEO",
        "gsm_col": "sample_name",  # cosmx uses sample_name
    },
    "Xenium": {
        "csv": DATA / "xenium_geo.csv",
        "cluster_dir": f"{CLUSTER_BASE}/Xenium_GEO",
        "gsm_col": "GSM",
    },
    "MERFISH": {
        "csv": DATA / "merfish_geo.csv",
        "cluster_dir": f"{CLUSTER_BASE}/MERFISH_GEO",
        "gsm_col": "GSM",
    },
}

def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def get_cluster_dirs(base_dir):
    """Scan cluster for GSE/GSM directories. Returns {gse: [gsm_dirs]}"""
    result = {}
    if not os.path.isdir(base_dir):
        return result
    for gse_name in sorted(os.listdir(base_dir)):
        gse_path = os.path.join(base_dir, gse_name)
        if not os.path.isdir(gse_path) or not gse_name.startswith("GSE"):
            continue
        gsms = []
        for item in sorted(os.listdir(gse_path)):
            item_path = os.path.join(gse_path, item)
            if os.path.isdir(item_path) and item.startswith("GSM"):
                gsms.append(item)
        if gsms:
            result[gse_name] = gsms
    return result

def reconcile(plat_name, cfg):
    print(f"\n{'='*70}")
    print(f"  {plat_name} GEO — 一致性校验")
    print(f"{'='*70}")

    # Read CSV ready rows
    rows = read_csv(cfg["csv"])
    ready_rows = [r for r in rows if r["status"] == "ready"]
    gsm_col = cfg["gsm_col"]

    # Build CSV index: {gse: {gsm: row}}
    csv_index = defaultdict(dict)
    for r in ready_rows:
        csv_index[r["GSE"]][r[gsm_col]] = r

    # Scan cluster
    cluster_index = get_cluster_dirs(cfg["cluster_dir"])

    # ── Check 1: CSV ready rows → cluster exists ──
    csv_missing = []
    csv_total = 0
    for gse, gsms in csv_index.items():
        for gsm in gsms:
            csv_total += 1
            if gse not in cluster_index:
                csv_missing.append((gse, gsm, "GSE dir not found on cluster"))
            elif gsm not in cluster_index[gse]:
                csv_missing.append((gse, gsm, f"GSM dir not found under {gse}/"))

    # ── Check 2: Cluster dirs → CSV ready ──
    cluster_not_ready = []
    cluster_total = 0
    for gse, gsms in cluster_index.items():
        # Find all ready GSMs for this GSE in CSV
        csv_gsms = set(csv_index.get(gse, {}).keys())
        for gsm in gsms:
            cluster_total += 1
            if gsm not in csv_gsms:
                cluster_not_ready.append((gse, gsm, "in cluster but not ready in CSV"))

    # ── Report ──
    print(f"\n  CSV ready rows: {csv_total}")
    print(f"  Cluster dirs:   {cluster_total}")

    if not csv_missing and not cluster_not_ready:
        print(f"\n  ✅ 完全一致！")
        return {"plat": plat_name, "ok": True, "csv_total": csv_total,
                "cluster_total": cluster_total, "csv_missing": [], "cluster_not_ready": []}

    if csv_missing:
        print(f"\n  ❌ CSV 中标记 ready 但在集群上找不到的目录 ({len(csv_missing)}):")
        for gse, gsm, reason in csv_missing[:20]:
            print(f"      {gse}/{gsm}  — {reason}")
        if len(csv_missing) > 20:
            print(f"      ... and {len(csv_missing) - 20} more")

    if cluster_not_ready:
        print(f"\n  ⚠️  集群上存在但 CSV 中不是 ready 的目录 ({len(cluster_not_ready)}):")
        for gse, gsm, reason in cluster_not_ready[:20]:
            print(f"      {gse}/{gsm}  — {reason}")
        if len(cluster_not_ready) > 20:
            print(f"      ... and {len(cluster_not_ready) - 20} more")

    return {
        "plat": plat_name, "ok": len(csv_missing) == 0 and len(cluster_not_ready) == 0,
        "csv_total": csv_total, "cluster_total": cluster_total,
        "csv_missing": csv_missing, "cluster_not_ready": cluster_not_ready,
    }


if __name__ == "__main__":
    all_results = []
    for plat_name, cfg in PLATFORMS.items():
        result = reconcile(plat_name, cfg)
        all_results.append(result)

    print(f"\n{'='*70}")
    print(f"  汇总")
    print(f"{'='*70}")
    for r in all_results:
        status = "✅" if r["ok"] else "❌"
        print(f"  {status} {r['plat']:8s}: CSV={r['csv_total']} ready, "
              f"Cluster={r['cluster_total']} dirs, "
              f"CSV缺失={len(r['csv_missing'])}, 集群多余={len(r['cluster_not_ready'])}")
