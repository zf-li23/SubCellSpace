"""Test: subcellspace touch --output on GEO datasets."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cli import build_parser, _cmd_touch

p = build_parser()

datasets = [
    ("CosMx GEO", "/data3/yangxr002/CosMx_GEO/GSE234713/GSM7473682"),
    ("Xenium GEO", "/data3/yangxr002/Xenium_GEO/GSE243168/GSM7780153"),
    ("MERFISH GEO", "/data3/yangxr002/MERFISH_GEO/GSE202623/GSM6125919"),
]

for label, path in datasets:
    print(f"{'='*60}")
    print(f"  {label}: {path}")
    print(f"{'='*60}")

    out_path = f"/tmp/{label.lower().replace(' ', '_')}_touch.json"
    args = p.parse_args(["touch", path, "--output", out_path])
    _cmd_touch(args)

    with open(out_path) as f:
        d = json.load(f)

    s = d["summary"]
    print(f"\n  Summary: {s['required_found']}/{s['total_files']} required, "
          f"{s['optional_found']} optional, {s['unexpected']} unexpected, "
          f"{s['redundant']} redundant")
    print(f"  Report: {out_path}")
    print()

# Also test --platform override
print("--- --platform override test ---")
args = p.parse_args(["touch", "/data3/yangxr002/CosMx_GEO/GSE234713/GSM7473682",
                     "--platform", "xenium", "--output", "/tmp/wrong_platform.json"])
_cmd_touch(args)
with open("/tmp/wrong_platform.json") as f:
    d = json.load(f)
s = d["summary"]
print(f"  Forced xenium on CosMx data: found={s['required_found']}/{s['total_files']}, missing_required={d['missing_required']}")
