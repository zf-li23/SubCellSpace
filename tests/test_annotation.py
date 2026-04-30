from __future__ import annotations

from src.registry import get_available_backends
from src.steps.annotation import run_cell_type_annotation


class TestRunCellTypeAnnotation:
    def test_cluster_label_backend(self, sample_anndata):
        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]
        result = run_cell_type_annotation(sample_anndata.copy(), "cluster_label")
        result_adata = result.output
        summary = result.summary
        assert "cell_type" in result_adata.obs
        assert result_adata.obs["cell_type"].notna().all()
        assert summary["annotation_backend_used"] == "cluster_label"
        # cluster_label produces labels like "Cluster_0"
        assert result_adata.obs["cell_type"].str.startswith("Cluster_").all()

    def test_rank_marker_backend(self, sample_anndata):
        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]
        # rank_marker expects lognorm layer
        sample_anndata.layers["lognorm"] = sample_anndata.X.copy()
        result = run_cell_type_annotation(sample_anndata.copy(), "rank_marker")
        result_adata = result.output
        summary = result.summary
        assert "cell_type" in result_adata.obs
        assert result_adata.obs["cell_type"].notna().all()
        assert summary["annotation_backend_used"] == "rank_marker"
        assert "n_cell_types" in summary
        assert "cell_type_distribution" in summary

    def test_missing_cluster_raises(self, sample_anndata):
        adata = sample_anndata.copy()
        if "cluster" in adata.obs:
            del adata.obs["cluster"]
        with __import__("pytest").raises(ValueError, match="`cluster` not found"):
            run_cell_type_annotation(adata, "cluster_label")

    def test_unknown_backend_raises(self, sample_anndata):
        sample_anndata.obs["cluster"] = ["0"] * sample_anndata.n_obs
        with __import__("pytest").raises(ValueError, match="Unknown annotation backend"):
            run_cell_type_annotation(sample_anndata.copy(), "bad_backend")

    def test_available_backends(self):
        backends = get_available_backends("annotation")
        assert "cluster_label" in backends
        assert "rank_marker" in backends
        assert "celltypist" in backends
