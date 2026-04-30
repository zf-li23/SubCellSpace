from __future__ import annotations

import scanpy as sc

from src.registry import get_available_backends
from src.steps.analysis import run_expression_and_spatial_analysis


class TestRunExpressionAndSpatialAnalysis:
    def test_output_returns_adata_and_summary(self, sample_anndata):
        adata = sample_anndata.copy()
        result = run_expression_and_spatial_analysis(
            adata,
            min_transcripts=0,
            min_genes=0,
            clustering_backend="leiden",
            leiden_resolution=1.0,
        )
        result_adata = result.output
        summary = result.summary
        assert isinstance(result_adata, sc.AnnData)
        assert isinstance(summary, dict)
        assert "n_obs_before_qc" in summary
        assert "n_obs_after_qc" in summary
        assert "clustering_backend_used" in summary
        assert "cluster" in result_adata.obs
        assert "X_pca" in result_adata.obsm
        assert "X_umap" in result_adata.obsm
        assert "connectivities" in result_adata.obsp

    def test_adds_spatial_neighbors(self, sample_anndata):
        adata = sample_anndata.copy()
        result = run_expression_and_spatial_analysis(
            adata,
            min_transcripts=0,
            min_genes=0,
            clustering_backend="leiden",
            leiden_resolution=1.0,
        )
        result_adata = result.output
        assert "spatial_connectivities" in result_adata.obsp

    def test_quality_filtering_removes_low_counts(self, sample_anndata):
        adata = sample_anndata.copy()
        # Set a high threshold so some cells get filtered out
        result = run_expression_and_spatial_analysis(
            adata,
            min_transcripts=99999,
            min_genes=0,
            clustering_backend="leiden",
            leiden_resolution=1.0,
        )
        result_adata = result.output
        assert result_adata.n_obs <= sample_anndata.n_obs

    def test_kmeans_backend(self, sample_anndata):
        adata = sample_anndata.copy()
        result = run_expression_and_spatial_analysis(
            adata,
            min_transcripts=0,
            min_genes=0,
            clustering_backend="kmeans",
            leiden_resolution=1.0,
        )
        assert "cluster" in result.output.obs
        assert result.summary["clustering_backend_used"] == "kmeans"

    def test_unknown_backend_raises(self, sample_anndata):
        with __import__("pytest").raises(ValueError, match="Unknown clustering backend"):
            run_expression_and_spatial_analysis(
                sample_anndata.copy(),
                min_transcripts=0,
                min_genes=0,
                clustering_backend="bad_backend",
                leiden_resolution=1.0,
            )

    def test_available_backends(self):
        backends = get_available_backends("analysis")
        assert "leiden" in backends
        assert "kmeans" in backends
        assert "scvi" in backends
