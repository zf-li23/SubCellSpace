#!/usr/bin/env python3
"""Cluster test: verify environment and ingestion work."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.registry import registry
registry.load_backends()

print("=== Steps & Backends ===")
for s in registry.get_step_order():
    print(f"  {s}: {list(registry.get_available_backends(s))}")

print()

from src.io import detect_platform, get_available_platforms, ingest
print(f"Platforms: {get_available_platforms()}")

files = {
    "CosMx": "/data3/yangxr002/CosMx/P0032/D0059/GSM8522533_6226_S496622_tx_file.csv",
    "Xenium": "/data3/yangxr002/Xenium/P1012/D1033/transcripts.csv.gz",
    "MERFISH": "/data3/yangxr002/MERFISH/P2005/D2010/HumanOvarianCancerPatient2Slice2_detected_transcripts.csv",
}

for name, path in files.items():
    plat = detect_platform(path)
    sdata = ingest(plat, path)
    pts = sdata.points["raw_transcripts"].compute()
    cells = pts["cell_id"].nunique() if "cell_id" in pts.columns else 0
    genes = pts["gene"].nunique() if "gene" in pts.columns else 0
    print(f"{name}: platform={plat}  tx={len(pts):,}  cells={cells:,}  genes={genes:,}")

print("\n=== ALL OK ===")
