from __future__ import annotations

from pathlib import Path

from ..pipeline_engine import run_pipeline
from ..models import PipelineResult


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
    """Run the full CosMx minimal analysis pipeline.

    This is a convenience wrapper that delegates to the plugin-style
    :func:`run_pipeline` engine.  The function signature is preserved
    for backward compatibility.

    Parameters
    ----------
    input_csv : str or Path
        Path to the input CosMx transcripts CSV file.
    output_dir : str or Path
        Directory where outputs (h5ad, report JSON, parquet) are written.
    min_transcripts : int
        Minimum number of transcripts per cell (QC filter).
    min_genes : int
        Minimum number of genes per cell (QC filter).
    denoise_backend : str
        Backend for transcript denoising.
    segmentation_backend : str
        Backend for cell segmentation.
    clustering_backend : str
        Backend for clustering (e.g. ``"leiden"``, ``"kmeans"``).
    leiden_resolution : float
        Resolution parameter for Leiden clustering.
    annotation_backend : str
        Backend for cell-type annotation.
    spatial_domain_backend : str
        Backend for spatial domain identification.
    spatial_domain_resolution : float
        Resolution for spatial domain leiden.
    n_spatial_domains : int or None
        Number of spatial domains (for k-means based backends).
    subcellular_domain_backend : str
        Backend for subcellular spatial domain identification.

    Returns
    -------
    PipelineResult
        The aggregated pipeline result.
    """
    return run_pipeline(
        input_csv=str(input_csv),
        output_dir=str(output_dir),
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
