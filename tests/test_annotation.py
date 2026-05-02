from __future__ import annotations

import numpy as np

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

    def test_celltypist_lognorm_recovery(self, sample_anndata, monkeypatch):
        """celltypist should auto-recover lognorm layer if present in adata.layers."""
        import sys
        import pandas as pd

        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]
        assert "lognorm" in sample_anndata.layers

        # Monkey-patch celltypist to avoid needing an actual model.
        # _anno_celltypist does `import celltypist` inside, so we patch sys.modules.
        class FakePrediction:
            predicted_labels = pd.DataFrame({
                "majority_voting": ["T_cell"] * sample_anndata.n_obs,
                "conf_score": [0.95] * sample_anndata.n_obs,
            })
            probability_matrix = pd.DataFrame(
                np.random.rand(sample_anndata.n_obs, 3),
            )

        class FakeModels:
            class Model:
                @staticmethod
                def load(model=None):
                    return "fake_model"

        class FakeCellTypistModule:
            models = FakeModels
            class logger:
                pass
            @staticmethod
            def annotate(adata, model, majority_voting, mode, p_thres):
                return FakePrediction()

        # Also patch celltypist.models.download_models
        FakeCellTypistModule.models.download_models = lambda model=None: None

        monkeypatch.setitem(sys.modules, "celltypist", FakeCellTypistModule)
        monkeypatch.setitem(sys.modules, "celltypist.models", FakeModels)
        monkeypatch.setitem(sys.modules, "celltypist.classifier", type(sys)("celltypist.classifier"))

        # Reload the annotation module to pick up the patched imports
        import importlib
        import src.steps.annotation as anno_mod
        importlib.reload(anno_mod)

        result = run_cell_type_annotation(sample_anndata.copy(), "celltypist")
        result_adata = result.output
        summary = result.summary
        assert "cell_type" in result_adata.obs
        assert result_adata.obs["cell_type"].notna().all()
        assert summary["annotation_backend_used"] == "celltypist"
        # When conf_score is present, it should be used
        assert "celltypist_score" in result_adata.obs

    def test_celltypist_conf_score_fallback(self, sample_anndata, monkeypatch):
        """celltypist should handle missing conf_score column (majority_voting=True).

        When majority_voting=True, predicted_labels does NOT contain 'conf_score'.
        The fix uses prediction.probability_matrix.max(axis=1) as fallback.
        """
        import sys
        import pandas as pd

        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]
        assert "lognorm" in sample_anndata.layers

        # Simulate majority_voting=True output: NO conf_score column
        class FakePrediction:
            predicted_labels = pd.DataFrame({
                "predicted_labels": ["T_cell"] * sample_anndata.n_obs,
                "over_clustering": ["0"] * sample_anndata.n_obs,
                "majority_voting": ["T_cell"] * sample_anndata.n_obs,
            })
            probability_matrix = pd.DataFrame(
                np.random.rand(sample_anndata.n_obs, 3),
            )

        class FakeModels:
            class Model:
                @staticmethod
                def load(model=None):
                    return "fake_model"

        class FakeCellTypistModule:
            models = FakeModels
            class logger:
                pass
            @staticmethod
            def annotate(adata, model, majority_voting, mode, p_thres):
                return FakePrediction()

        FakeCellTypistModule.models.download_models = lambda model=None: None

        monkeypatch.setitem(sys.modules, "celltypist", FakeCellTypistModule)
        monkeypatch.setitem(sys.modules, "celltypist.models", FakeModels)
        monkeypatch.setitem(sys.modules, "celltypist.classifier", type(sys)("celltypist.classifier"))

        import importlib
        import src.steps.annotation as anno_mod
        importlib.reload(anno_mod)

        # Should NOT raise KeyError 'conf_score'
        result = run_cell_type_annotation(sample_anndata.copy(), "celltypist")
        result_adata = result.output
        assert "cell_type" in result_adata.obs
        assert "celltypist_score" in result_adata.obs
        assert result.summary["annotation_backend_used"] == "celltypist"

    def test_celltypist_no_conf_score_with_prob_matrix(self, sample_anndata, monkeypatch):
        """celltypist should fall back to probability_matrix when conf_score is missing."""
        import sys
        import pandas as pd

        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]

        class FakePrediction:
            predicted_labels = pd.DataFrame({
                "predicted_labels": ["T_cell"] * sample_anndata.n_obs,
                "over_clustering": ["0"] * sample_anndata.n_obs,
                "majority_voting": ["T_cell"] * sample_anndata.n_obs,
            })
            probability_matrix = pd.DataFrame(
                np.random.rand(sample_anndata.n_obs, 3),
            )

        class FakeModels:
            class Model:
                @staticmethod
                def load(model=None):
                    return "fake_model"

        class FakeCellTypistModule:
            models = FakeModels
            class logger:
                pass
            @staticmethod
            def annotate(adata, model, majority_voting, mode, p_thres):
                return FakePrediction()

        FakeCellTypistModule.models.download_models = lambda model=None: None

        monkeypatch.setitem(sys.modules, "celltypist", FakeCellTypistModule)
        monkeypatch.setitem(sys.modules, "celltypist.models", FakeModels)
        monkeypatch.setitem(sys.modules, "celltypist.classifier", type(sys)("celltypist.classifier"))

        import importlib
        import src.steps.annotation as anno_mod
        importlib.reload(anno_mod)

        # Should fall back via probability_matrix fallback path
        result = run_cell_type_annotation(sample_anndata.copy(), "celltypist")
        assert "cell_type" in result.output.obs
        assert "celltypist_score" in result.output.obs
        assert result.summary["annotation_backend_used"] == "celltypist"

    def test_celltypist_missing_lognorm_recovery(self, sample_anndata, monkeypatch):
        """celltypist should handle when lognorm layer is missing by using X directly."""
        import sys
        import pandas as pd

        sample_anndata.obs["cluster"] = [str(i % 3) for i in range(sample_anndata.n_obs)]
        adata = sample_anndata.copy()
        if "lognorm" in adata.layers:
            del adata.layers["lognorm"]

        class FakePrediction:
            predicted_labels = pd.DataFrame({
                "majority_voting": ["B_cell"] * adata.n_obs,
                "conf_score": [0.9] * adata.n_obs,
            })

        class FakeModels:
            class Model:
                @staticmethod
                def load(model=None):
                    return "fake_model"

        class FakeCellTypistModule:
            models = FakeModels
            class logger:
                pass
            @staticmethod
            def annotate(adata, model, majority_voting, mode, p_thres):
                return FakePrediction()

        FakeCellTypistModule.models.download_models = lambda model=None: None

        monkeypatch.setitem(sys.modules, "celltypist", FakeCellTypistModule)
        monkeypatch.setitem(sys.modules, "celltypist.models", FakeModels)
        monkeypatch.setitem(sys.modules, "celltypist.classifier", type(sys)("celltypist.classifier"))

        import importlib
        import src.steps.annotation as anno_mod
        importlib.reload(anno_mod)

        # Should not raise; will construct layer from X
        result = run_cell_type_annotation(adata, "celltypist")
        assert "cell_type" in result.output.obs
        assert result.summary["annotation_backend_used"] == "celltypist"

    def test_available_backends(self):
        backends = get_available_backends("annotation")
        assert "cluster_label" in backends
        assert "rank_marker" in backends
        assert "celltypist" in backends

