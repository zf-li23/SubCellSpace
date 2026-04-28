from __future__ import annotations

import itertools
import json
from pathlib import Path

import pandas as pd

from .pipeline import run_cosmx_minimal
from .steps.annotation import AVAILABLE_ANNOTATION_BACKENDS
from .steps.analysis import AVAILABLE_CLUSTERING_BACKENDS
from .steps.denoise import AVAILABLE_DENOISE_BACKENDS
from .steps.segmentation import AVAILABLE_SEGMENTATION_BACKENDS
from .steps.spatial_domain import AVAILABLE_SPATIAL_DOMAIN_BACKENDS
from .steps.subcellular_spatial_domain import AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS


def run_cosmx_backend_benchmark(
    input_csv: str | Path,
    output_dir: str | Path,
    min_transcripts: int = 10,
    min_genes: int = 10,
    leiden_resolution: float = 1.0,
    spatial_domain_resolution: float = 1.0,
    n_spatial_domains: int | None = None,
) -> dict:
    input_csv = Path(input_csv)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_reports: list[dict] = []
    rows: list[dict] = []

    combinations = itertools.product(
        AVAILABLE_DENOISE_BACKENDS,
        AVAILABLE_SEGMENTATION_BACKENDS,
        AVAILABLE_CLUSTERING_BACKENDS,
        AVAILABLE_ANNOTATION_BACKENDS,
        AVAILABLE_SPATIAL_DOMAIN_BACKENDS,
        AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS,
    )

    for denoise_backend, segmentation_backend, clustering_backend, annotation_backend, spatial_domain_backend, subcellular_domain_backend in combinations:
        tag = (
            f"denoise-{denoise_backend}__seg-{segmentation_backend}__cluster-{clustering_backend}"
            f"__anno-{annotation_backend}__domain-{spatial_domain_backend}"
            f"__subdomain-{subcellular_domain_backend}"
        )
        combo_output = output_dir / tag

        result = run_cosmx_minimal(
            input_csv=input_csv,
            output_dir=combo_output,
            min_transcripts=min_transcripts,
            min_genes=min_genes,
            denoise_backend=denoise_backend,
            segmentation_backend=segmentation_backend,
            clustering_backend=clustering_backend,
            leiden_resolution=leiden_resolution,
            annotation_backend=annotation_backend,
            spatial_domain_backend=spatial_domain_backend,
            spatial_domain_resolution=spatial_domain_resolution,
            n_spatial_domains=n_spatial_domains,
            subcellular_domain_backend=subcellular_domain_backend,
        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))
        all_reports.append(report)

        row = {
            "tag": tag,
            "denoise_backend": denoise_backend,
            "segmentation_backend": segmentation_backend,
            "clustering_backend": clustering_backend,
            "annotation_backend": annotation_backend,
            "spatial_domain_backend": spatial_domain_backend,
            "n_cells_after_qc": report["layer_evaluation"]["expression"]["n_cells_after_qc"],
            "n_genes_after_hvg": report["layer_evaluation"]["expression"]["n_genes_after_hvg"],
            "n_clusters": report["layer_evaluation"]["clustering"]["n_clusters"],
            "n_cell_types": report["layer_evaluation"]["annotation"]["n_cell_types"],
            "n_spatial_domains": report["layer_evaluation"]["spatial_domain"]["n_spatial_domains"],
            "domain_cluster_ari": report["layer_evaluation"]["spatial_domain"]["domain_cluster_ari"],
            "silhouette_pca": report["layer_evaluation"]["clustering"]["silhouette_pca"],
            "avg_spatial_degree": report["layer_evaluation"]["spatial"].get("avg_degree"),
            "connected_components": report["layer_evaluation"]["spatial"].get("connected_components"),
        }
        rows.append(row)

    summary_csv = output_dir / "benchmark_summary.csv"
    summary_json = output_dir / "benchmark_summary.json"
    pd.DataFrame(rows).to_csv(summary_csv, index=False)
    summary_json.write_text(json.dumps(all_reports, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "n_runs": len(rows),
        "summary_csv": str(summary_csv),
        "summary_json": str(summary_json),
    }
