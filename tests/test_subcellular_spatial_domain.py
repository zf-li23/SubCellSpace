from __future__ import annotations

import numpy as np
import pandas as pd
import anndata as ad
import pytest
from src.steps.subcellular_spatial_domain import (
    AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS,
    run_subcellular_spatial_domain,
)


class TestRunSubcellularSpatialDomain:
    def test_hdbscan_backend(self, sample_transcripts_df, sample_anndata):
        """HDBSCAN backend assigns subcellular_domain labels and writes adata.obs stats."""
        result_df, result_adata, summary = run_subcellular_spatial_domain(
            sample_transcripts_df.copy(),
            sample_anndata.copy(),
            backend="hdbscan",
        )
        assert "subcellular_domain" in result_df.columns
        assert result_df["subcellular_domain"].nunique() >= 1
        assert "n_subcellular_domains" in result_adata.obs
        assert "subcellular_domain_distribution" in result_adata.obs
        assert summary["subcellular_spatial_domain_backend"] == "hdbscan"
        assert summary["n_cells_processed"] > 0

    def test_dbscan_backend(self, sample_transcripts_df, sample_anndata):
        """DBSCAN backend assigns subcellular_domain labels."""
        result_df, result_adata, summary = run_subcellular_spatial_domain(
            sample_transcripts_df.copy(),
            sample_anndata.copy(),
            backend="dbscan",
            dbscan_eps=50.0,
            dbscan_min_samples=2,
        )
        assert "subcellular_domain" in result_df.columns
        assert "n_subcellular_domains" in result_adata.obs
        assert summary["subcellular_spatial_domain_backend"] == "dbscan"

    def test_leiden_spatial_backend(self, sample_transcripts_df, sample_anndata):
        """Leiden spatial backend assigns subcellular_domain labels."""
        result_df, result_adata, summary = run_subcellular_spatial_domain(
            sample_transcripts_df.copy(),
            sample_anndata.copy(),
            backend="leiden_spatial",
        )
        assert "subcellular_domain" in result_df.columns
        assert "n_subcellular_domains" in result_adata.obs
        assert summary["subcellular_spatial_domain_backend"] == "leiden_spatial"

    def test_none_backend(self, sample_transcripts_df, sample_anndata):
        """None backend assigns all domains to '0'."""
        result_df, result_adata, summary = run_subcellular_spatial_domain(
            sample_transcripts_df.copy(),
            sample_anndata.copy(),
            backend="none",
        )
        assert "subcellular_domain" in result_df.columns
        assert result_df["subcellular_domain"].unique().tolist() == ["0"]
        assert "n_subcellular_domains" not in result_adata.obs
        assert summary["subcellular_spatial_domain_backend"] == "none"
        assert summary["n_cells_processed"] == 0

    def test_unknown_backend_raises(self, sample_transcripts_df, sample_anndata):
        with pytest.raises(ValueError, match="Unknown subcellular spatial domain backend"):
            run_subcellular_spatial_domain(
                sample_transcripts_df.copy(),
                sample_anndata.copy(),
                backend="bad_backend",
            )

    def test_summary_has_expected_keys(self, sample_transcripts_df, sample_anndata):
        """Summary dict contains all expected keys."""
        _, _, summary = run_subcellular_spatial_domain(
            sample_transcripts_df.copy(),
            sample_anndata.copy(),
            backend="hdbscan",
        )
        expected_keys = [
            "subcellular_spatial_domain_backend",
            "n_cells_processed",
            "n_cells_with_multiple_domains",
            "fraction_multi_domain",
            "mean_domains_per_cell",
            "total_noise_transcripts",
        ]
        for key in expected_keys:
            assert key in summary, f"Missing key: {key}"

    def test_fraction_multi_domain_in_range(self, sample_transcripts_df, sample_anndata):
        """fraction_multi_domain should be between 0 and 1."""
        _, _, summary = run_subcellular_spatial_domain(
            sample_transcripts_df.copy(),
            sample_anndata.copy(),
            backend="dbscan",
            dbscan_eps=100.0,
            dbscan_min_samples=2,
        )
        assert 0.0 <= summary["fraction_multi_domain"] <= 1.0

    def test_available_backends(self):
        assert "hdbscan" in AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS
        assert "dbscan" in AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS
        assert "leiden_spatial" in AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS
        assert "none" in AVAILABLE_SUBCELLULAR_SPATIAL_DOMAIN_BACKENDS

    def test_adata_obs_names_match_cell_column(self, sample_transcripts_df, sample_anndata):
        """The function should handle mismatched cell names gracefully."""
        # Create adata with a different cell set
        rng = np.random.default_rng(99)
        adata2 = ad.AnnData(X=rng.poisson(lam=3, size=(3, 5)).astype(np.float32))
        adata2.obs_names = ["Cell_A", "Cell_B", "Cell_C"]
        adata2.obsm["spatial"] = rng.uniform(0, 100, size=(3, 2)).astype(np.float32)

        # transcripts df only references Cell_A
        df = pd.DataFrame(
            {
                "cell": ["Cell_A", "Cell_A", "Cell_A", "Cell_A"],
                "x_global_px": [10.0, 20.0, 30.0, 40.0],
                "y_global_px": [10.0, 20.0, 30.0, 40.0],
            }
        )

        result_df, result_adata, summary = run_subcellular_spatial_domain(
            df, adata2.copy(), backend="hdbscan", hdbscan_min_cluster_size=2, hdbscan_min_samples=1
        )
        # Should not crash for cells not in the transcript set
        assert "subcellular_domain" in result_df.columns
        assert summary["n_cells_processed"] == 1  # Only Cell_A