#!/usr/bin/env python3
"""
SubCellSpace — Benchmark all backends across all platforms.

Tests each backend individually (one variation at a time, others at defaults)
and records PASS/FAIL status in a JSON summary file.

Usage:
    # CosMx (default)
    python scripts/benchmark_all_backends.py

    # Specific platform
    python scripts/benchmark_all_backends.py --platform xenium

    # All platforms sequentially
    python scripts/benchmark_all_backends.py --all-platforms

    # Custom output directory
    python scripts/benchmark_all_backends.py --platform merfish -o outputs/my_benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# ── ensure we can import from the project root ──────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.io import ingest, get_available_platforms
from src.pipeline_engine import run_pipeline
from src.registry import get_available_backends, load_backends

# ── Platform → test data mapping ────────────────────────────────────
PLATFORM_DATA: dict[str, Path] = {
    "cosmx":     PROJECT_ROOT / "data" / "test" / "Mouse_brain_CosMx_1000cells.csv",
    "xenium":    PROJECT_ROOT / "data" / "test" / "Xenium_mouse_brain_rep3_1000cells.parquet",
    "merfish":   PROJECT_ROOT / "data" / "test" / "MERFISH_1014_region_1_detected_transcripts.csv",
    "stereoseq": PROJECT_ROOT / "data" / "test" / "Stereo_seq_mouse_spleen_bin40.gem",
}

# ── Steps to benchmark ─────────────────────────────────────────────
# Excludes patchify (optional, needs Snakemake) and subcellular_analysis
# (expensive SCRIN — tested separately).
BENCHMARK_STEPS = [
    "denoise",
    "segmentation",
    "analysis",
    "annotation",
    "spatial_domain",
    "subcellular_spatial_domain",
    "spatial_analysis",
]

# ── Default backends per step ──────────────────────────────────────
DEFAULTS: dict[str, str] = {
    "denoise": "intracellular",
    "segmentation": "provided_cells",
    "patchify": "none",
    "analysis": "leiden",
    "annotation": "rank_marker",
    "spatial_domain": "spatial_leiden",
    "subcellular_spatial_domain": "hdbscan",
    "spatial_analysis": "squidpy",
    "subcellular_analysis": "rna_localization",
}

# Maps step names (as used internally) → run_pipeline kwarg key
STEP_TO_KWARG: dict[str, str] = {
    "denoise": "denoise_backend",
    "segmentation": "segmentation_backend",
    "patchify": "patchify_backend",
    "analysis": "clustering_backend",
    "annotation": "annotation_backend",
    "spatial_domain": "spatial_domain_backend",
    "subcellular_spatial_domain": "subcellular_spatial_domain_backend",
    "spatial_analysis": "spatial_analysis_backend",
    "subcellular_analysis": "subcellular_analysis_backend",
}

MIN_TRANSCRIPTS = 10
MIN_GENES = 5


def _extract_report_metrics(report: dict) -> dict:
    """Extract key metrics from a pipeline report JSON."""
    le = report.get("layer_evaluation", {})
    return {
        "n_cells":     le.get("expression", {}).get("n_cells_after_qc", 0),
        "n_genes":     le.get("expression", {}).get("n_genes_after_hvg", 0),
        "n_clusters":  le.get("clustering", {}).get("n_clusters", 0),
        "n_domains":   le.get("spatial_domain", {}).get("n_spatial_domains", 0),
        "n_subdomains": le.get("subcellular", {}).get("n_subcellular_domains", 0),
    }


def benchmark_platform(
    platform: str,
    sdata,
    output_dir: Path,
    results: dict[str, dict],
) -> dict[str, dict]:
    """Run all backend variations for a single platform.

    Parameters
    ----------
    platform : str
        Platform name (cosmx, xenium, etc.).
    sdata : SpatialData
        Pre-ingested spatial data object.
    output_dir : Path
        Root output directory for this platform's benchmark results.
    results : dict
        Accumulated results dict (mutated in-place).

    Returns
    -------
    dict
        The updated results dict.
    """
    platform_dir = output_dir / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    summary_path = platform_dir / "benchmark_results.json"

    for step_name in BENCHMARK_STEPS:
        backends = get_available_backends(step_name)
        if not backends:
            continue

        for backend in backends:
            tag = f"{platform}/{step_name}={backend}"
            combo_dir = platform_dir / tag.split("/")[1].replace("=", "_")

            # ── Build kwargs with only this backend changed ────────
            kwargs: dict = {
                "output_dir": combo_dir,
                "min_transcripts": MIN_TRANSCRIPTS,
                "min_genes": MIN_GENES,
            }
            for s, default_backend in DEFAULTS.items():
                kwarg_key = STEP_TO_KWARG.get(s)
                if kwarg_key is None:
                    continue
                kwargs[kwarg_key] = backend if s == step_name else default_backend

            print(f"\n{'='*60}")
            print(f"  [{tag}]  starting …")
            print(f"{'='*60}")
            t0 = time.time()

            try:
                result = run_pipeline(sdata=sdata, **kwargs)
                elapsed = time.time() - t0

                report_path = Path(result.report_path)
                if not report_path.exists():
                    raise FileNotFoundError(f"Report not found at {report_path}")

                report = json.loads(report_path.read_text(encoding="utf-8"))
                metrics = _extract_report_metrics(report)

                print(
                    f"  ✅  [{tag}] PASS  ({elapsed:.1f}s)  "
                    f"cells={metrics['n_cells']} "
                    f"genes={metrics['n_genes']} "
                    f"clusters={metrics['n_clusters']} "
                    f"domains={metrics['n_domains']} "
                    f"subdomains={metrics['n_subdomains']}"
                )
                results[tag] = {
                    "platform": platform,
                    "step": step_name,
                    "backend": backend,
                    "status": "PASS",
                    "elapsed_seconds": round(elapsed, 1),
                    **metrics,
                }
            except Exception as e:
                elapsed = time.time() - t0
                error_msg = str(e).rstrip()
                print(f"  ❌  [{tag}] FAIL  ({elapsed:.1f}s)  {error_msg[:300]}")
                results[tag] = {
                    "platform": platform,
                    "step": step_name,
                    "backend": backend,
                    "status": "FAIL",
                    "elapsed_seconds": round(elapsed, 1),
                    "error": error_msg[:500],
                }

            # Save incrementally
            summary_path.write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    return results


def _print_summary(results: dict[str, dict]) -> None:
    """Print a formatted summary of all benchmark results."""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  BENCHMARK SUMMARY")
    lines.append("=" * 60)

    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] == "FAIL")
    lines.append(f"  Total: {len(results)}  |  ✅ PASS: {passed}  |  ❌ FAIL: {failed}")
    lines.append("")

    # Group by platform
    by_platform: dict[str, list[tuple[str, dict]]] = {}
    for tag, r in sorted(results.items()):
        plat = r.get("platform", "unknown")
        by_platform.setdefault(plat, []).append((tag, r))

    for plat, items in sorted(by_platform.items()):
        lines.append(f"  ── {plat} ──")
        for tag, r in items:
            icon = "✅" if r["status"] == "PASS" else "❌"
            extra = ""
            if r["status"] == "PASS":
                extra = (
                    f"cells={r['n_cells']} "
                    f"clusters={r['n_clusters']} "
                    f"domains={r['n_domains']} "
                    f"subdomains={r['n_subdomains']}"
                )
            else:
                extra = r.get("error", "")[:80]
            lines.append(f"  {icon}  {tag:55s}  ({r['elapsed_seconds']:5.1f}s)  {extra}")

    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark all backends on one or all platforms."
    )
    parser.add_argument(
        "--platform", type=str, default="cosmx",
        choices=list(PLATFORM_DATA),
        help="Platform to benchmark (default: cosmx)",
    )
    parser.add_argument(
        "--all-platforms", action="store_true",
        help="Benchmark all platforms sequentially",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path,
        default=PROJECT_ROOT / "outputs" / "backend_validation",
        help="Output directory for benchmark results",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: run only default backends (one run per platform)",
    )
    args = parser.parse_args()

    load_backends()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    platforms = list(PLATFORM_DATA) if args.all_platforms else [args.platform]

    all_results: dict[str, dict] = {}
    for platform in platforms:
        data_path = PLATFORM_DATA.get(platform)
        if data_path is None or not data_path.exists():
            print(f"⚠️  No test data for platform '{platform}' (expected: {data_path}). Skipping.")
            continue

        print(f"\n{'=' * 60}")
        print(f"  Platform: {platform}")
        print(f"  Input:    {data_path}")
        print(f"{'=' * 60}")

        # Ingest once — reuse across all backend combinations
        sdata = ingest(platform, data_path)

        summary = sdata.attrs.get("ingestion_summary", {})
        print(f"  Ingested: {summary.get('n_transcripts', '?'):,} transcripts, "
              f"{summary.get('n_cells', '?')} cells")

        if args.quick:
            # Quick mode: run defaults only (one run per platform)
            tag = f"{platform}/defaults"
            combo_dir = output_dir / platform / "defaults"
            kwargs = {"output_dir": combo_dir}
            for s, default_backend in DEFAULTS.items():
                kwarg_key = STEP_TO_KWARG.get(s)
                if kwarg_key is not None:
                    kwargs[kwarg_key] = default_backend

            print(f"  [{tag}]  quick mode — running defaults …")
            t0 = time.time()
            try:
                result = run_pipeline(sdata=sdata, **kwargs)
                elapsed = time.time() - t0
                report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
                metrics = _extract_report_metrics(report)
                print(f"  ✅  [{tag}] PASS  ({elapsed:.1f}s)  "
                      f"cells={metrics['n_cells']} clusters={metrics['n_clusters']}")
                all_results[tag] = {"platform": platform, "step": "defaults", "backend": "defaults",
                                     "status": "PASS", "elapsed_seconds": round(elapsed, 1), **metrics}
            except Exception as e:
                elapsed = time.time() - t0
                all_results[tag] = {"platform": platform, "step": "defaults", "backend": "defaults",
                                     "status": "FAIL", "elapsed_seconds": round(elapsed, 1), "error": str(e)[:500]}
                print(f"  ❌  [{tag}] FAIL  ({elapsed:.1f}s)  {str(e)[:200]}")

            # List available backends
            print(f"  Available backends:")
            for step_name in BENCHMARK_STEPS:
                backends = get_available_backends(step_name)
                print(f"    {step_name}: {', '.join(backends)}")
        else:
            all_results = benchmark_platform(platform, sdata, output_dir, all_results)

    _print_summary(all_results)

    # Save combined results
    combined_path = output_dir / "benchmark_results_combined.json"
    combined_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nCombined results saved to: {combined_path}")


if __name__ == "__main__":
    main()
