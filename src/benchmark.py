from __future__ import annotations

import itertools
import json
import logging
from pathlib import Path

import pandas as pd

from .io import ingest
from .pipeline_engine import run_pipeline
from .registry import get_available_backends

logger = logging.getLogger(__name__)


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

    # Phase 0: ingest once, reuse for all combinations
    logger.info("Ingesting %s …", input_csv)
    sdata = ingest("cosmx", input_csv)

    denoise_backends = get_available_backends("denoise")
    seg_backends = get_available_backends("segmentation")
    clustering_backends = get_available_backends("analysis")
    annotation_backends = get_available_backends("annotation")
    spatial_domain_backends = get_available_backends("spatial_domain")
    subcellular_domain_backends = get_available_backends("subcellular_spatial_domain")

    combinations = itertools.product(
        denoise_backends, seg_backends, clustering_backends,
        annotation_backends, spatial_domain_backends, subcellular_domain_backends,
    )

    all_reports: list[dict] = []
    rows: list[dict] = []

    for (denoise_backend, segmentation_backend, clustering_backend,
         annotation_backend, spatial_domain_backend, subcellular_domain_backend) in combinations:
        tag = (
            f"denoise-{denoise_backend}__seg-{segmentation_backend}__cluster-{clustering_backend}"
            f"__anno-{annotation_backend}__domain-{spatial_domain_backend}"
            f"__subdomain-{subcellular_domain_backend}"
        )
        combo_output = output_dir / tag
        logger.info("Benchmark: %s", tag)

        try:
            result = run_pipeline(
                sdata=sdata,
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
        except Exception as exc:
            logger.error("Benchmark %s FAILED: %s", tag, exc)

    summary_csv = output_dir / "benchmark_summary.csv"
    summary_json = output_dir / "benchmark_summary.json"
    pd.DataFrame(rows).to_csv(summary_csv, index=False)
    summary_json.write_text(json.dumps(all_reports, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    return {
        "n_runs": len(rows),
        "summary_csv": str(summary_csv),
        "summary_json": str(summary_json),
    }
