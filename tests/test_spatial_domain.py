from __future__ import annotations

import numpy as np
import scanpy as sc
from src.steps.spatial_domain import run_spatial_domain_identification
from src.registry import get_available_backends


class TestRunSpatialDomainIdentification:
    def test_spatial_leiden_backend(self, sample_anndata):
        # Ensure spatial_connectivities exists
        result = run_spatial_domain_identification(
            sample_anndata.copy(),
            backend="spatial_leiden",
            domain_resolution=1.0,
            n_spatial_domains=None,
        )
        result_adata = result.output
        summary = result.summary
        assert "spatial_domain" in result_adata.obs
        assert summary["spatial_domain_backend_used"].startswith("spatial_leiden")
        assert "n_spatial_domains" in summary

    def test_spatial_kmeans_backend(self, sample_anndata):
        result = run_spatial_domain_identification(
            sample_anndata.copy(),
            backend="spatial_kmeans",
            domain_resolution=1.0,
            n_spatial_domains=3,
        )
        result_adata = result.output
        summary = result.summary
        assert "spatial_domain" in result_adata.obs
        assert summary["spatial_domain_backend_used"] == "spatial_kmeans"
        assert summary["n_spatial_domains"] > 0

    def test_missing_connectivities_auto_computed(self, sample_anndata):
        """When spatial_connectivities is missing, _ensure_spatial_neighbors auto-computes it."""
        adata = sample_anndata.copy()
        if "spatial_connectivities" in adata.obsp:
            del adata.obsp["spatial_connectivities"]
        # Should NOT raise -- the function auto-computes spatial neighbors
        result = run_spatial_domain_identification(
            adata,
            backend="spatial_leiden",
            domain_resolution=1.0,
            n_spatial_domains=None,
        )
        result_adata = result.output
        assert "spatial_domain" in result_adata.obs
        assert "spatial_connectivities" in result_adata.obsp

    def test_unknown_backend_raises(self, sample_anndata):
        with __import__("pytest").raises(ValueError, match="Unknown spatial domain backend"):
            run_spatial_domain_identification(
                sample_anndata.copy(),
                backend="bad_backend",
                domain_resolution=1.0,
                n_spatial_domains=None,
            )

    def test_distribution_summary(self, sample_anndata):
        result = run_spatial_domain_identification(
            sample_anndata.copy(),
            backend="spatial_leiden",
            domain_resolution=1.0,
            n_spatial_domains=None,
        )
        summary = result.summary
        assert "spatial_domain_distribution" in summary
        assert isinstance(summary["spatial_domain_distribution"], dict)

    def test_available_backends(self):
        backends = get_available_backends("spatial_domain")
        assert "spatial_leiden" in backends
        assert "spatial_kmeans" in backends
