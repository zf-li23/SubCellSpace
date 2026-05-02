#!/usr/bin/env python3
"""
SubCellSpace — Benchmark all backends on the test CosMx dataset.

Tests each backend individually (one variation at a time, others at defaults)
and records PASS/FAIL status in a JSON summary file.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# ── ensure we can import from the project root ──────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipelines.cosmx_minimal import run_cosmx_minimal
from src.registry import get_available_backends, registry

# ── paths ───────────────────────────────────────────────────────────
INPUT_CSV = PROJECT_ROOT / "data" / "test" / "Mouse_brain_CosMX_1000cells.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "backend_validation"
SUMMARY_PATH = OUTPUT_DIR / "benchmark_results.json"
LOG_PATH = OUTPUT_DIR / "benchmark_log.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── tee: write to both stdout and log file ─────────────────────────
_log_file = open(LOG_PATH, "w", encoding="utf-8")  # noqa: SIM115


def log(msg: str = "") -> None:
    """Print *msg* to stdout and append it to the log file."""
    print(msg)
    _log_file.write(msg + "\n")
    _log_file.flush()


# ── default backends ───────────────────────────────────────────────
DEFAULTS: dict[str, str] = {
    "denoise": "intracellular",
    "segmentation": "provided_cells",
    "analysis": "leiden",
    "annotation": "rank_marker",
    "spatial_domain": "spatial_leiden",
    "subcellular_spatial_domain": "hdbscan",
}

KWARG_MAP: dict[str, str] = {
    "denoise": "denoise_backend",
    "segmentation": "segmentation_backend",
    "analysis": "clustering_backend",
    "annotation": "annotation_backend",
    "spatial_domain": "spatial_domain_backend",
    "subcellular_spatial_domain": "subcellular_domain_backend",
}

MIN_TRANSCRIPTS = 10
MIN_GENES = 5


def test_single_backend(step_name: str, backend: str) -> dict:
    """Run the pipeline with only *step_name* changed to *backend*."""
    tag = f"{step_name}={backend}"
    combo_dir = OUTPUT_DIR / tag.replace("=", "_")

    kwargs: dict = {
        "input_csv": INPUT_CSV,
        "output_dir": combo_dir,
        "min_transcripts": MIN_TRANSCRIPTS,
        "min_genes": MIN_GENES,
    }

    for s, default_backend in DEFAULTS.items():
        param_name = KWARG_MAP[s]
        if s == step_name:
            kwargs[param_name] = backend
        else:
            kwargs[param_name] = default_backend

    print(f"\n{'='*60}")
    print(f"  [{tag}]  starting …")
    print(f"{'='*60}")
    t0 = time.time()

    try:
        result = run_cosmx_minimal(**kwargs)
        elapsed = time.time() - t0

        report_path = Path(result.report_path)
        if not report_path.exists():
            raise FileNotFoundError(f"Report not found at {report_path}")

        report = json.loads(report_path.read_text(encoding="utf-8"))
        n_cells = report.get("layer_evaluation", {}).get("expression", {}).get("n_cells_after_qc", 0)
        n_genes = report.get("layer_evaluation", {}).get("expression", {}).get("n_genes_after_hvg", 0)
        n_clusters = report.get("layer_evaluation", {}).get("clustering", {}).get("n_clusters", 0)
        n_domains = report.get("layer_evaluation", {}).get("spatial_domain", {}).get("n_spatial_domains", 0)
        n_subdomains = report.get("layer_evaluation", {}).get("subcellular", {}).get("n_subcellular_domains", 0)

        print(f"  ✅  [{tag}] PASS  ({elapsed:.1f}s)  cells={n_cells} genes={n_genes} clusters={n_clusters} spatial_domains={n_domains} subcellular_domains={n_subdomains}")
        return {
            "status": "PASS",
            "elapsed_seconds": round(elapsed, 1),
            "n_cells": n_cells,
            "n_genes": n_genes,
            "n_clusters": n_clusters,
            "n_spatial_domains": n_domains,
            "n_subcellular_domains": n_subdomains,
        }

    except Exception as e:
        elapsed = time.time() - t0
        error_msg = str(e).rstrip()
        print(f"  ❌  [{tag}] FAIL  ({elapsed:.1f}s)  {error_msg[:300]}")
        return {
            "status": "FAIL",
            "elapsed_seconds": round(elapsed, 1),
            "error": error_msg[:500],
        }


def main() -> None:
    registry.load_backends()
    results: dict[str, dict] = {}

    for step_name in [
        "denoise",
        "segmentation",
        "analysis",
        "annotation",
        "spatial_domain",
        "subcellular_spatial_domain",
    ]:
        backends = get_available_backends(step_name)
        for backend in backends:
            tag = f"{step_name}={backend}"
            results[tag] = test_single_backend(step_name, backend)
            # Save incrementally so partial results survive a crash
            SUMMARY_PATH.write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    # ── print summary ──────────────────────────────────────────────
    print(f"\n\n{'='*60}")
    print("  BENCHMARK SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] == "FAIL")
    print(f"  Total: {len(results)}  |  ✅ PASS: {passed}  |  ❌ FAIL: {failed}")
    print()
    for tag, r in sorted(results.items()):
        icon = "✅" if r["status"] == "PASS" else "❌"
        extra = ""
        if r["status"] == "PASS":
            extra = f"cells={r['n_cells']} clusters={r['n_clusters']} domains={r['n_spatial_domains']} subdomains={r['n_subcellular_domains']}"
        else:
            extra = r.get("error", "")[:80]
        print(f"  {icon}  {tag:45s}  ({r['elapsed_seconds']:5.1f}s)  {extra}")

    print(f"\nResults saved to: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
