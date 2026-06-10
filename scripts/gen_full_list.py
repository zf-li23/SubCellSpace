"""生成全库 CosMx GEO 数据集列表"""
import sys
sys.path.insert(0, "/Share/home/yangxr002/zf-li23/subcellspace")
from src.database.resolver import list_datasets
from src.touch import touch

MIN_OPT = 3
EXCLUDE_GSES = {"GSE253474"}

datasets = [d for d in list_datasets(platform="CosMx", status="ready")
            if d.source.endswith("_geo") and d.resolved_path]

results = []
for ds in datasets:
    gsm = ds.gsm or ""
    merged = "-" in gsm
    if ds.gse in EXCLUDE_GSES and not merged:
        continue
    r = touch(ds.resolved_path, normalize=False, platform_override="cosmx")
    s = r.to_dict()["summary"]
    if s["required_found"] >= 1 and s["optional_found"] >= MIN_OPT:
        label = f"{ds.gse}/{gsm}"
        results.append((label, ds.resolved_path))

for label, path in results:
    print(f"{label}\t{path}")
print(f"TOTAL:{len(results)}")
