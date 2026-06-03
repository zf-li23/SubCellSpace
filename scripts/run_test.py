#!/usr/bin/env python3
"""Run SubCellSpace pipeline on a single CosMx dataset and report results."""
import json, logging, sys, time
from pathlib import Path

sys.path.insert(0, "/Share/home/yangxr002/zf-li23/subcellspace")

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

data_path = sys.argv[1]
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)

from src.config import Settings, settings as default_settings
from src.io.cosmx import build_cell_level_adata, build_spatialdata_from_csv
from src.pipeline_engine import run_pipeline

# Ingest
print(f"Ingesting: {data_path}")
sdata = build_spatialdata_from_csv(data_path, platform="cosmx")
print(f"  Transcripts: {len(sdata.points['transcripts'])}")
print(f"  FOVs: {sdata.attrs.get('ingestion_summary', {}).get('n_fovs', '?')}")

# Run pipeline
print("Running pipeline...")
t0 = time.time()
settings = default_settings.copy()
settings.set("output_dir", str(output_dir))
settings.set("min_transcripts", 10)
settings.set("min_genes", 10)

result = run_pipeline(settings=settings, sdata=sdata, skip_container=False)
elapsed = time.time() - t0

print(f"\n=== RESULTS ===")
print(f"Elapsed: {elapsed:.1f}s")
print(f"Cells after QC: {result.adata.n_obs}")
print(f"Genes after HVG: {result.adata.n_vars}")
print(f"Report: {result.report_path}")
print(f"Adata: {result.adata_path}")

# Step timing
report = json.loads(open(result.report_path).read())
steps = report.get("step_summary", {})
for sn, sv in steps.items():
    if isinstance(sv, dict):
        e = sv.get("__elapsed_seconds__", 0)
        b = sv.get("backend_used", "?")
        print(f"  {sn:25s} backend={b:20s} {e:.1f}s")
