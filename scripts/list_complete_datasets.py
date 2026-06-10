"""
列出所有完整的 CosMx GEO 数据集（用于 Slurm job array 输入）。

输出格式: GSE/GSM\t/path/to/data
每行一个数据集，stdout 输出。
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.database.resolver import list_datasets
from src.touch import touch

MIN_OPTIONAL = 3

datasets = [
    d for d in list_datasets(platform="CosMx", status="ready")
    if d.source.endswith("_geo") and d.resolved_path
]

results = []
for ds in datasets:
    try:
        r = touch(ds.resolved_path, normalize=False, platform_override="cosmx")
        s = r.to_dict()["summary"]
        if s["required_found"] >= 1 and s["optional_found"] >= MIN_OPTIONAL:
            gsm_label = ds.gsm or (ds.gse or "")
            results.append((f"{ds.gse}/{gsm_label}", ds.resolved_path))
    except Exception:
        pass

for label, path in results:
    print(f"{label}\t{path}")
print(f"TOTAL:{len(results)}")
