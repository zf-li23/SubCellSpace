"""生成全库 MERFISH GEO 数据集列表"""
import sys
sys.path.insert(0, "/Share/home/yangxr002/zf-li23/subcellspace")
from src.database.resolver import list_datasets
from src.touch import touch

MIN_OPT = 1  # MERFISH 有 3 个可选文件，至少需要 1 个
PLATFORM = "MERFISH"

datasets = [d for d in list_datasets(platform=PLATFORM, status="ready")
            if d.source.endswith("_geo") and d.resolved_path]

results = []
for ds in datasets:
    gsm = ds.gsm or ""
    r = touch(ds.resolved_path, normalize=False, platform_override="merfish")
    s = r.to_dict()["summary"]
    if s["required_found"] >= 1 and s["optional_found"] >= MIN_OPT:
        label = f"{ds.gse}/{gsm}"
        results.append((label, ds.resolved_path))

for label, path in results:
    print(f"{label}\t{path}")
print(f"TOTAL:{len(results)}")
