from __future__ import annotations

import json
from pathlib import Path

from ..evaluation import build_layer_evaluation
from ..io.cosmx import build_cell_level_adata, build_spatialdata, load_cosmx_transcripts, summarize_cosmx_transcripts
from ..models import PipelineResult
from ..steps import (
    apply_transcript_denoise,
    assign_cells,
    run_cell_type_annotation,
    run_expression_and_spatial_analysis,
    run_spatial_domain_identification,
    run_subcellular_spatial_domain,
)


def run_cosmx_minimal(
    input_csv: str | Path,
    output_dir: str | Path,
    min_transcripts: int = 10,
    min_genes: int = 10,
    denoise_backend: str = "intracellular",
    segmentation_backend: str = "provided_cells",
    clustering_backend: str = "leiden",
    leiden_resolution: float = 1.0,
    annotation_backend: str = "rank_marker",
    spatial_domain_backend: str = "spatial_leiden",
    spatial_domain_resolution: float = 1.0,
    n_spatial_domains: int | None = None,
    subcellular_domain_backend: str = "hdbscan",
) -> PipelineResult:
    input_csv = Path(input_csv)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    transcripts = load_cosmx_transcripts(input_csv)
    summary = summarize_cosmx_transcripts(transcripts, input_csv)

    denoised, denoise_summary = apply_transcript_denoise(transcripts, backend=denoise_backend)
    segmented, segmentation_summary = assign_cells(denoised, backend=segmentation_backend)
    adata = build_cell_level_adata(segmented)

    # Step 3: Spatial Domain Identification (cell-level + subcellular-level)
    adata, spatial_domain_summary = run_spatial_domain_identification(
        adata,
        backend=spatial_domain_backend,
        domain_resolution=spatial_domain_resolution,
        n_spatial_domains=n_spatial_domains,
    )
    segmented, adata, subcellular_summary = run_subcellular_spatial_domain(
        segmented, adata, backend=subcellular_domain_backend
    )

    # Step 4: Clustering & Expression Analysis
    adata, analysis_summary = run_expression_and_spatial_analysis(
        adata,
        min_transcripts=min_transcripts,
        min_genes=min_genes,
        clustering_backend=clustering_backend,
        leiden_resolution=leiden_resolution,
    )

    # Step 5: Cell-type Annotation
    adata, annotation_summary = run_cell_type_annotation(adata, backend=annotation_backend)

    sdata = build_spatialdata(adata)
    layer_evaluation = build_layer_evaluation(
        raw_df=transcripts,
        denoised_df=denoised,
        segmented_df=segmented,
        adata=adata,
    )

    adata_path = output_dir / "cosmx_minimal.h5ad"
    report_path = output_dir / "cosmx_minimal_report.json"
    transcripts_path = output_dir / "cosmx_minimal_transcripts.parquet"
    adata.write_h5ad(adata_path)
    segmented.to_parquet(transcripts_path)

    report = {
        "input_csv": str(input_csv),
        "n_obs": int(adata.n_obs),
        "n_vars": int(adata.n_vars),
        "clusters": adata.obs["cluster"].value_counts().sort_index().to_dict(),
        "summary": {
            "n_transcripts": summary.n_transcripts,
            "n_cells": summary.n_cells,
            "n_genes": summary.n_genes,
            "n_fovs": summary.n_fovs,
            **summary.extra,
        },
        "step_summary": {
            "denoise": denoise_summary,
            "segmentation": segmentation_summary,
            "spatial_domain": spatial_domain_summary,
            "subcellular_spatial_domain": subcellular_summary,
            "analysis": analysis_summary,
            "annotation": annotation_summary,
        },
        "layer_evaluation": layer_evaluation,
        "outputs": {
            "adata": str(adata_path),
            "report": str(report_path),
            "transcripts": str(transcripts_path),
            "spatialdata_points": list(sdata.points.keys()),
            "spatialdata_tables": list(sdata.tables.keys()),
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return PipelineResult(
        adata=adata,
        summary=summary,
        sdata=sdata,
        adata_path=adata_path,
        report_path=report_path,
    )