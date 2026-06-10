"""重新统计所有 CosMx GEO 数据集的 opt 分布"""
import sys
sys.path.insert(0, "/Share/home/yangxr002/zf-li23/subcellspace")
from src.database.resolver import list_datasets
from src.touch import touch

datasets = [d for d in list_datasets(platform="CosMx", status="ready")
            if d.source.endswith("_geo") and d.resolved_path]

opt_counts = {}
gse_details = {}
for ds in datasets:
    r = touch(ds.resolved_path, normalize=False, platform_override="cosmx")
    s = r.to_dict()["summary"]
    opt = s["optional_found"]
    opt_counts[opt] = opt_counts.get(opt, 0) + 1
    if opt not in gse_details:
        gse_details[opt] = {}
    gse = ds.gse or "unknown"
    gse_details[opt][gse] = gse_details[opt].get(gse, 0) + 1

print("CosMx GEO optional file distribution (after fov_position fix):")
for k in sorted(opt_counts):
    print(f"  opt={k}: {opt_counts[k]} datasets")
    for gse, cnt in sorted(gse_details[k].items()):
        print(f"    {gse}: {cnt}")
