from __future__ import annotations

import numpy as np
import pytest
from sklearn.cluster import KMeans

from src.registry import get_available_backends
from src.steps.spatial_domain import run_spatial_domain_identification


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
        assert "graphst" in backends
        assert len(backends) == 3

    # ── GraphST embedding key probing ─────────────────────────────────────

    @pytest.mark.parametrize(
        "emb_key",
        ["emb", "GraphST", "embedding", "latent", "graphst_emb"],
    )
    def test_graphst_probes_known_embedding_keys(self, sample_anndata, monkeypatch, emb_key):
        """Verify _domain_graphst probes all known embedding keys.

        We monkey-patch sys.modules['GraphST'] to simulate its behaviour
        without running the real GraphST training (which is slow and may
        produce OOM errors in CI).
        """
        import sys
        import types as mt
        import src.steps.spatial_domain as sd_mod

        adata = sample_anndata.copy()
        sd_mod._GRAPHST_AVAILABLE = True

        fake_emb = np.zeros((adata.n_obs, 8), dtype=np.float32)

        # Build a fake module that looks like the real GraphST top-level package
        fake_graphst_mod = mt.ModuleType("GraphST")

        class FakeGraphSTClass:
            def __init__(self, *a, **kw): pass
            def train(self):
                adata.obsm[emb_key] = fake_emb
                return adata

        def fake_preprocess(adata_): pass
        def fake_get_feature(adata_): pass
        def fake_clustering(adata_, n_clusters, radius, key, method, start, end, increment, refinement):
            adata_.obs["domain"] = [str(i % max(1, n_clusters)) for i in range(adata_.n_obs)]

        fake_graphst_mod.preprocess = fake_preprocess
        fake_graphst_mod.get_feature = fake_get_feature
        fake_graphst_mod.GraphST = FakeGraphSTClass
        fake_graphst_mod.clustering = fake_clustering

        monkeypatch.setitem(sys.modules, "GraphST", fake_graphst_mod)

        # Also need torch for the import inside _domain_graphst
        import torch
        _ = torch

        backend_used = sd_mod._domain_graphst(adata, domain_resolution=1.0, n_spatial_domains=3)
        assert backend_used == "graphst"
        assert "spatial_domain" in adata.obs

    def test_graphst_fallback_on_no_embeddings(self, sample_anndata, monkeypatch):
        """When GraphST returns no embeddings, fall back to spatial_leiden."""
        import sys
        import types as mt
        import src.steps.spatial_domain as sd_mod

        adata = sample_anndata.copy()
        sd_mod._GRAPHST_AVAILABLE = True

        fake_graphst_mod = mt.ModuleType("GraphST")

        import anndata as ad

        class FakeGraphSTClass:
            def __init__(self, *a, **kw): pass
            def train(self):
                # Return a minimal adata with NO obsm embeddings and NO obs columns
                return ad.AnnData(X=adata.X[:1], dtype=adata.X.dtype)

        def fake_preprocess(adata_): pass
        def fake_get_feature(adata_): pass
        def fake_clustering(*a, **kw): pass

        fake_graphst_mod.preprocess = fake_preprocess
        fake_graphst_mod.get_feature = fake_get_feature
        fake_graphst_mod.GraphST = FakeGraphSTClass
        fake_graphst_mod.clustering = fake_clustering

        monkeypatch.setitem(sys.modules, "GraphST", fake_graphst_mod)

        backend_used = sd_mod._domain_graphst(adata, domain_resolution=1.0, n_spatial_domains=3)
        # Should fall back gracefully to spatial_leiden
        assert "spatial_leiden" in backend_used


