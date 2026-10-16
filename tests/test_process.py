from __future__ import annotations

import json
import subprocess
import sys

from src.process import process_sample


def test_cli_help_works():
    # Regression: sopa skips its submodule imports when "--help" is in sys.argv, which broke `subcellspace --help`.
    out = subprocess.run([sys.executable, "-m", "src", "--help"], capture_output=True, text=True, check=True)
    assert "process" in out.stdout


def test_process_and_report_real_sample(testdata, tmp_path):
    from src.html_report import generate_html_report

    summary = process_sample(testdata / "xenium", tmp_path)
    assert summary["data_tier"] == "A"
    assert summary["n_cells"] == 419 and summary["n_transcripts"] == 106206
    assert summary["n_clusters"] >= 2
    on_disk = json.loads((tmp_path / "subcellspace_summary.json").read_text())
    assert on_disk["provenance"]["matrix"].startswith("vendor")

    import anndata as ad

    adata = ad.read_h5ad(tmp_path / "subcellspace_cells.h5ad")
    assert adata.n_vars == 468  # all genes kept (no HVG subsetting)
    assert "counts" in adata.layers and adata.layers["counts"].sum() == adata.obs["n_transcripts"].sum()
    assert "markers" in adata.uns
    assert generate_html_report(tmp_path).stat().st_size > 0


def test_tiny_sample_is_clustered_with_capped_pcs(testdata, tmp_path):
    summary = process_sample(testdata / "cosmx", tmp_path)  # 13 cells pass QC
    assert summary["n_cells_clustered"] == 13


def test_cli_process_failure_writes_status(tmp_path):
    out = tmp_path / "out"
    res = subprocess.run([sys.executable, "-m", "src", "process", str(tmp_path / "missing"), "-o", str(out)],
                         capture_output=True, text=True)
    assert res.returncode != 0
    status = json.loads((out / "subcellspace_status.json").read_text())
    assert status["status"] == "failed" and status["error_type"]


def test_umap_pca_init(testdata, tmp_path):
    # Regression (GSE301112/GSM9075556, GSE293144/GSM8877284): ARPACK segfaulted in UMAP's spectral init;
    # --umap-init pca skips it and is recorded in the summary.
    import anndata as ad

    summary = process_sample(testdata / "xenium", tmp_path, umap_init="pca")
    assert summary["umap_init"] == "pca" and summary["n_clusters"] >= 2
    assert ad.read_h5ad(tmp_path / "subcellspace_cells.h5ad").obsm["X_umap"].shape == (summary["n_cells_clustered"], 2)
