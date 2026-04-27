from __future__ import annotations

import numpy as np
import pandas as pd
from src.evaluation.metrics import (
    _safe_ratio,
    _series_distribution,
    _silhouette_from_pca,
    _spatial_graph_metrics,
    build_layer_evaluation,
)


class TestSafeRatio:
    def test_normal_ratio(self):
        assert _safe_ratio(3.0, 6.0) == 0.5

    def test_zero_denominator(self):
        assert _safe_ratio(5.0, 0.0) == 0.0

    def test_zero_numerator(self):
        assert _safe_ratio(0.0, 10.0) == 0.0


class TestSeriesDistribution:
    def test_basic(self):
        s = pd.Series(["a", "a", "b", "c", "c", "c"])
        dist = _series_distribution(s)
        assert dist["a"] == 2 / 6
        assert dist["b"] == 1 / 6
        assert dist["c"] == 3 / 6

    def test_empty(self):
        s = pd.Series([], dtype=str)
        assert _series_distribution(s) == {}


class TestSilhouetteFromPca:
    def test_returns_float(self, sample_anndata):
        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]
        result = _silhouette_from_pca(sample_anndata)
        assert result is not None
        assert -1.0 <= result <= 1.0

    def test_single_cluster_returns_none(self, sample_anndata):
        sample_anndata.obs["cluster"] = "0"
        assert _silhouette_from_pca(sample_anndata) is None

    def test_no_cluster_returns_none(self, sample_anndata):
        if "cluster" in sample_anndata.obs:
            del sample_anndata.obs["cluster"]
        assert _silhouette_from_pca(sample_anndata) is None


class TestSpatialGraphMetrics:
    def test_with_connectivities(self, sample_anndata):
        metrics = _spatial_graph_metrics(sample_anndata)
        assert metrics["graph_available"] is True
        assert metrics["n_nodes"] == sample_anndata.n_obs
        assert metrics["n_edges"] > 0
        assert metrics["avg_degree"] > 0

    def test_without_connectivities(self, sample_anndata):
        adata = sample_anndata.copy()
        if "spatial_connectivities" in adata.obsp:
            del adata.obsp["spatial_connectivities"]
        metrics = _spatial_graph_metrics(adata)
        assert metrics["graph_available"] is False


class TestBuildLayerEvaluation:
    def test_returns_full_dict(self, sample_transcripts_df, sample_anndata):
        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]
        sample_anndata.obs["cell_type"] = [f"Type_{i % 3}" for i in range(sample_anndata.n_obs)]
        sample_anndata.obs["spatial_domain"] = [str(i % 2) for i in range(sample_anndata.n_obs)]

        eval_result = build_layer_evaluation(
            sample_transcripts_df,
            sample_transcripts_df,
            sample_transcripts_df,
            sample_anndata,
        )
        assert "ingestion" in eval_result
        assert "denoise" in eval_result
        assert "segmentation" in eval_result
        assert "expression" in eval_result
        assert "clustering" in eval_result
        assert "annotation" in eval_result
        assert "spatial_domain" in eval_result
        assert "spatial" in eval_result
        assert isinstance(eval_result["ingestion"]["n_transcripts"], int)