#!/usr/bin/env python3
"""
Comprehensive backend test suite for SubCellSpace.

Tests all pipeline backends across all 4 platforms using ingested .zarr files.
Estimated time:
  - CosMx (1000 cells): ~60-90s (standard) or ~120s (with HDBSCAN)
  - Xenium (1000 cells): ~60-90s (standard) or ~120s (with HDBSCAN)
  - MERFISH (461 cells): ~20-30s (most steps will fail/skip)
  - Stereo-seq (0 cells): ~5s (will skip most steps)
  - Total: ~3-5 minutes for "standard" tests, ~6-8 min with all slow backends
"""
from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path

# Add project root to path
PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_ROOT))

import pandas as pd
import spatialdata
from tqdm import tqdm

from src.steps.denoise import apply_transcript_denoise
from src.steps.segmentation import _seg_provided_cells, _seg_fov_cell_id
from src.steps.spatial_domain import run_spatial_domain_identification
from src.steps.subcellular_spatial_domain import run_subcellular_spatial_domain
from src.steps.analysis import run_expression_and_spatial_analysis
from src.steps.annotation import run_cell_type_annotation
from src.steps.spatial_analysis import run_spatial_analysis
from src.steps.subcellular_analysis import run_subcellular_analysis
from src.io.cosmx import build_cell_level_adata
from src.constants import COL_CELL_ID, resolve_col_strict


RESULTS: list[dict] = []


class TimeoutError_(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError_("Timed out")


def run_with_timeout(func, args, timeout=120):
    """Run a function with a timeout (seconds)."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        result = func(*args)
        signal.alarm(0)
        return result, None
    except Exception as e:
        signal.alarm(0)
        return None, e


def log_result(platform: str, step: str, backend: str, status: str, detail: str = "", elapsed: float = 0.0):
    RESULTS.append({
        "platform": platform,
        "step": step,
        "backend": backend,
        "status": status,
        "detail": detail[:200],
        "elapsed_s": round(elapsed, 2),
    })


def run_backend_test(platform, step, backend, func, args, timeout=120):
    """Run a single backend test with timeout and progress reporting."""
    t0 = time.time()
    result, error = run_with_timeout(func, args, timeout)
    elapsed = time.time() - t0

    status = "OK" if error is None else "FAIL"
    detail = str(error)[:200] if error else ""
    log_result(platform, step, backend, status, detail, elapsed)

    status_icon = "✓" if status == "OK" else "✗"
    print(f"  [{status_icon}] {step}/{backend} ({elapsed:.1f}s)", end="")
    if status == "FAIL":
        print(f" → {detail[:80]}", end="")
    print()

    return result, error


def test_platform(platform: str, zarr_path: str):
    print(f"\n{'='*60}")
    print(f"📦 Platform: {platform}")
    print(f"   Zarr: {zarr_path}")
    print(f"{'='*60}")

    pts = None
    try:
        sdata = spatialdata.read_zarr(zarr_path)
        pts = sdata.points["raw_transcripts"].compute()
        n_cells = pts['cell_id'].nunique()
        n_genes = pts['gene'].nunique()
        print(f"   Transcripts: {len(pts):,} | Cells: {n_cells:,} | Genes: {n_genes}")
    except Exception as e:
        log_result(platform, "load", "zarr", "FAIL", str(e))
        print(f"  [✗] load/zarr → {e}")
        return

    # ── Denoise (fast, ~1-2s each) ──
    print(f"\n  ── Denoise ──")
    for backend in ["none", "intracellular", "nuclear_only"]:
        run_backend_test(platform, "denoise", backend, apply_transcript_denoise, (pts, backend), timeout=30)

    # spARC (may be slow)
    run_backend_test(platform, "denoise", "sparc", apply_transcript_denoise, (pts, "sparc"), timeout=60)

    # ── Segmentation (fast, ~1s each) ──
    print(f"\n  ── Segmentation ──")
    seg_df = None
    _, _ = run_backend_test(platform, "segmentation", "provided_cells", _seg_provided_cells, (pts,), timeout=30)
    _, _ = run_backend_test(platform, "segmentation", "fov_cell_id", _seg_fov_cell_id, (pts,), timeout=30)

    # Cellpose (needs image → SKIP)
    try:
        from src.steps.segmentation import _seg_cellpose
        log_result(platform, "segmentation", "cellpose", "SKIP", "Requires external image file")
    except ImportError:
        log_result(platform, "segmentation", "cellpose", "SKIP", "cellpose not installed")
    print(f"  [~] segmentation/cellpose → SKIP (needs external image)")

    # Baysor (needs Julia CLI → SKIP)
    log_result(platform, "segmentation", "baysor", "SKIP", "Requires Julia+Baysor CLI")
    print(f"  [~] segmentation/baysor → SKIP (needs Julia CLI)")

    # ── Build adata for downstream tests ──
    try:
        seg_df = _seg_provided_cells(pts)
        cell_col = resolve_col_strict(seg_df.columns, COL_CELL_ID)
        n_cells = seg_df[cell_col].nunique()
    except Exception:
        n_cells = 0

    if n_cells < 2:
        log_result(platform, "pipeline", "full", "SKIP", f"Only {n_cells} cells after segmentation")
        print(f"\n  [~] Pipeline → SKIP (only {n_cells} cells, need ≥2)")
        return

    adata = build_cell_level_adata(seg_df)
    print(f"\n  ── Cell-level adata: {adata.n_obs} cells × {adata.n_vars} genes ──")

    # ── Analysis / Clustering (~15-20s each) ──
    adata_ana = None
    print(f"\n  ── Analysis ──")
    for backend in ["leiden", "kmeans"]:
        run_backend_test(platform, "analysis", backend,
                         run_expression_and_spatial_analysis,
                         (adata.copy(), 10, 10, backend, 1.0), timeout=60)

    # scVI (~30-60s)
    print(f"  [~] analysis/scvi → ~30-60s (training neural network)")
    run_backend_test(platform, "analysis", "scvi",
                     run_expression_and_spatial_analysis,
                     (adata.copy(), 10, 10, "scvi", 1.0), timeout=120)

    # Build analysis output for downstream tests
    ana_result = run_expression_and_spatial_analysis(adata.copy(), 10, 10, "leiden", 1.0)
    adata_ana = ana_result.output

    # ── Spatial Domain (~1s each) ──
    print(f"\n  ── Spatial Domain ──")
    for backend in ["spatial_leiden", "spatial_kmeans"]:
        run_backend_test(platform, "spatial_domain", backend,
                         run_spatial_domain_identification,
                         (adata_ana.copy(), backend, 1.0, None), timeout=30)

    # GraphST (~10-30s)
    print(f"  [~] spatial_domain/graphst → may take ~10-30s")
    run_backend_test(platform, "spatial_domain", "graphst",
                     run_spatial_domain_identification,
                     (adata_ana.copy(), "graphst", 1.0, None), timeout=60)

    # ── Subcellular Spatial Domain ──
    print(f"\n  ── Subcellular Spatial Domain ──")
    # "none" is instant
    run_backend_test(platform, "subcellular_domain", "none",
                     run_subcellular_spatial_domain, (seg_df, "none"), timeout=30)

    # HDBSCAN is VERY slow for many cells
    if n_cells <= 500:
        print(f"  [~] subcellular_domain/hdbscan → ~10-30s ({n_cells} cells)")
        run_backend_test(platform, "subcellular_domain", "hdbscan",
                         run_subcellular_spatial_domain, (seg_df, "hdbscan"), timeout=120)
    else:
        print(f"  [~] subcellular_domain/hdbscan → SKIP ({n_cells} cells, would take ~30-60s)")
        log_result(platform, "subcellular_domain", "hdbscan", "SKIP", f"Too many cells ({n_cells}), would be slow")

    # ── Annotation (fast, <1s each) ──
    print(f"\n  ── Annotation ──")
    for backend in ["rank_marker", "cluster_label"]:
        run_backend_test(platform, "annotation", backend,
                         run_cell_type_annotation, (adata_ana.copy(), backend), timeout=30)

    # CellTypist (~5-15s, needs model download)
    print(f"  [~] annotation/celltypist → ~5-15s (may need model download)")
    run_backend_test(platform, "annotation", "celltypist",
                     run_cell_type_annotation, (adata_ana.copy(), "celltypist"), timeout=60)

    # ── Spatial Analysis ──
    print(f"\n  ── Spatial Analysis ──")
    # squidpy (~15-25s)
    print(f"  [~] spatial_analysis/squidpy → ~15-25s")
    run_backend_test(platform, "spatial_analysis", "squidpy",
                     run_spatial_analysis, (adata_ana.copy(), "squidpy"), timeout=120)

    # scFates (~10-20s)
    print(f"  [~] spatial_analysis/scfates → ~10-20s")
    run_backend_test(platform, "spatial_analysis", "scfates",
                     run_spatial_analysis, (adata_ana.copy(), "scfates"), timeout=120)

    # ── Subcellular Analysis ──
    print(f"\n  ── Subcellular Analysis ──")
    # rna_localization (~1-2s)
    run_backend_test(platform, "subcellular_analysis", "rna_localization",
                     run_subcellular_analysis, (seg_df, adata_ana, "rna_localization"), timeout=30)

    # SCRIN (CPU-intensive, skip if too many cells)
    if n_cells <= 200:
        print(f"  [~] subcellular_analysis/scrin → may take ~30-60s")
        run_backend_test(platform, "subcellular_analysis", "scrin",
                         run_subcellular_analysis, (seg_df, adata_ana, "scrin"), timeout=120)
    else:
        print(f"  [~] subcellular_analysis/scrin → SKIP ({n_cells} cells, CPU-intensive)")
        log_result(platform, "subcellular_analysis", "scrin", "SKIP", f"Too many cells ({n_cells}), CPU-intensive")


def print_summary():
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")

    df = pd.DataFrame(RESULTS)

    # Per-platform per-step pivot table
    pivot = df.pivot_table(
        index=["platform", "step"],
        columns="status",
        aggfunc="size",
        fill_value=0
    )
    print(pivot.to_string())
    print()

    # Overall stats
    total = len(df)
    ok = len(df[df["status"] == "OK"])
    fail = len(df[df["status"] == "FAIL"])
    skip = len(df[df["status"] == "SKIP"])
    print(f"Total: {total} | ✅ OK: {ok} | ❌ FAIL: {fail} | ⏭️ SKIP: {skip}")
    print(f"Total elapsed: {df['elapsed_s'].sum():.1f}s")

    # All failures
    failures = df[df["status"] == "FAIL"]
    if len(failures):
        print(f"\n❌ FAILURES ({len(failures)}):")
        for _, row in failures.iterrows():
            print(f"  [{row['platform']}] {row['step']}/{row['backend']}: {row['detail']}")

    # Save
    out_path = Path("outputs/test_all_backends_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(RESULTS, indent=2, default=str))
    print(f"\nResults saved to {out_path}")


def main():
    platforms = {
        "cosmx": "outputs/test_cosmx/experiment.zarr",
        "xenium": "outputs/test_xenium/experiment.zarr",
        "merfish": "outputs/test_merfish/experiment.zarr",
        "stereoseq": "outputs/test_stereoseq/experiment.zarr",
    }

    # Print time estimate
    print("⏱️  Estimated time per platform:")
    print("   CosMx (1000 cells):   ~60-90s standard, ~120s with HDBSCAN")
    print("   Xenium (1000 cells):  ~60-90s standard, ~120s with HDBSCAN")
    print("   MERFISH (461 cells):  ~20-30s (many steps skip)")
    print("   Stereo-seq (0 cells): ~5s (all steps skip)")
    print("   Total: ~3-5 minutes (standard), ~6-8 min (all backends)")
    print()

    t_start = time.time()
    for platform, zarr_path in platforms.items():
        test_platform(platform, zarr_path)

    print(f"\n{'='*60}")
    print(f"⏱️  Total time: {time.time() - t_start:.1f}s")
    print_summary()


if __name__ == "__main__":
    main()
