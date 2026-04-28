from __future__ import annotations

import argparse
from pathlib import Path

from .benchmark import run_cosmx_backend_benchmark
from .pipeline import run_cosmx_minimal
from .steps.annotation import AVAILABLE_ANNOTATION_BACKENDS
from .steps.analysis import AVAILABLE_CLUSTERING_BACKENDS
from .steps.denoise import AVAILABLE_DENOISE_BACKENDS
from .steps.segmentation import AVAILABLE_SEGMENTATION_BACKENDS
from .steps.spatial_domain import AVAILABLE_SPATIAL_DOMAIN_BACKENDS
from .steps.subcellular_spatial_domain import AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subcellspace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    cosmx = subparsers.add_parser("run-cosmx", help="Run the minimal CosMx pipeline")
    cosmx.add_argument("input_csv", type=Path)
    cosmx.add_argument("--output-dir", type=Path, default=Path("outputs/cosmx_demo"))
    cosmx.add_argument("--min-transcripts", type=int, default=10)
    cosmx.add_argument("--min-genes", type=int, default=10)
    cosmx.add_argument("--denoise-backend", choices=AVAILABLE_DENOISE_BACKENDS, default="intracellular")
    cosmx.add_argument("--segmentation-backend", choices=AVAILABLE_SEGMENTATION_BACKENDS, default="provided_cells")
    cosmx.add_argument("--clustering-backend", choices=AVAILABLE_CLUSTERING_BACKENDS, default="leiden")
    cosmx.add_argument("--leiden-resolution", type=float, default=1.0)
    cosmx.add_argument("--annotation-backend", choices=AVAILABLE_ANNOTATION_BACKENDS, default="rank_marker")
    cosmx.add_argument("--spatial-domain-backend", choices=AVAILABLE_SPATIAL_DOMAIN_BACKENDS, default="spatial_leiden")
    cosmx.add_argument("--spatial-domain-resolution", type=float, default=1.0)
    cosmx.add_argument("--n-spatial-domains", type=int, default=None)
    cosmx.add_argument(
        "--subcellular-domain-backend",
        choices=AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS,
        default="hdbscan",
    )

    benchmark = subparsers.add_parser("benchmark-cosmx", help="Run backend benchmark grid on CosMx data")
    benchmark.add_argument("input_csv", type=Path)
    benchmark.add_argument("--output-dir", type=Path, default=Path("outputs/cosmx_benchmark"))
    benchmark.add_argument("--min-transcripts", type=int, default=10)
    benchmark.add_argument("--min-genes", type=int, default=10)
    benchmark.add_argument("--leiden-resolution", type=float, default=1.0)
    benchmark.add_argument("--spatial-domain-resolution", type=float, default=1.0)
    benchmark.add_argument("--n-spatial-domains", type=int, default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run-cosmx":
        result = run_cosmx_minimal(
            input_csv=args.input_csv,
            output_dir=args.output_dir,
            min_transcripts=args.min_transcripts,
            min_genes=args.min_genes,
            denoise_backend=args.denoise_backend,
            segmentation_backend=args.segmentation_backend,
            clustering_backend=args.clustering_backend,
            leiden_resolution=args.leiden_resolution,
            annotation_backend=args.annotation_backend,
            spatial_domain_backend=args.spatial_domain_backend,
            spatial_domain_resolution=args.spatial_domain_resolution,
            n_spatial_domains=args.n_spatial_domains,
            subcellular_domain_backend=args.subcellular_domain_backend,
        )
        print(result.summary.to_text())
        print(f"Saved AnnData to: {result.adata_path}")
        print(f"Saved report to: {result.report_path}")

    if args.command == "benchmark-cosmx":
        benchmark = run_cosmx_backend_benchmark(
            input_csv=args.input_csv,
            output_dir=args.output_dir,
            min_transcripts=args.min_transcripts,
            min_genes=args.min_genes,
            leiden_resolution=args.leiden_resolution,
            spatial_domain_resolution=args.spatial_domain_resolution,
            n_spatial_domains=args.n_spatial_domains,
        )
        print(f"Completed {benchmark['n_runs']} runs")
        print(f"Benchmark summary CSV: {benchmark['summary_csv']}")
        print(f"Benchmark summary JSON: {benchmark['summary_json']}")
