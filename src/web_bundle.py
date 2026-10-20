"""Lightweight per-sample web bundle (``subcellspace_web.json``) for the static site (AGENTS.md D5).

Built from the outputs of ``subcellspace process`` without loading the expression matrix:

- ``summary``: full-data statistics and provenance from ``subcellspace_summary.json``;
- ``qc``: histograms (pre-binned) of transcripts / genes / area per clustered cell;
- ``clusters``: size and top marker genes per leiden cluster;
- ``points``: a cluster-stratified sample of cells (at most ``MAX_POINTS``) with spatial position (µm, rounded) and
  UMAP (×100, rounded) for the scatter plots. ``n_total`` says how many cells the sample was drawn from.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MAX_POINTS = 10_000
MIN_PER_CLUSTER = 50
N_BINS = 40
SUMMARY_KEYS = (
    "platform", "data_tier", "data_tier_meaning", "n_cells", "n_cells_with_transcripts", "n_cells_clustered",
    "min_transcripts_for_clustering", "n_clusters", "gene_panel_size", "n_genes", "n_transcripts",
    "n_transcripts_in_cells", "n_control_transcripts", "fraction_transcripts_in_cells", "fraction_qv_ge_20",
    "n_fovs", "median_transcripts", "median_genes", "median_cell_area_um2", "umap_init", "provenance", "notes",
    "software", "generated",
)


def _hist(values: np.ndarray, cap_pct: float = 99.5) -> dict | None:
    values = values[np.isfinite(values)]
    if not len(values):
        return None
    hi = float(np.percentile(values, cap_pct))
    lo = float(values.min())
    counts, edges = np.histogram(values[values <= hi], bins=N_BINS, range=(lo, hi if hi > lo else lo + 1))
    return {"edges": [round(float(e), 2) for e in edges], "counts": counts.tolist(),
            "n_above": int((values > hi).sum())}


def sample_cells(clusters: np.ndarray, max_points: int = MAX_POINTS, seed: int = 0) -> np.ndarray:
    """Indices of a cluster-stratified sample: proportional, with at least MIN_PER_CLUSTER per cluster."""
    n = len(clusters)
    if n <= max_points:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    labels, counts = np.unique(clusters, return_counts=True)
    want = np.maximum(np.minimum(counts, MIN_PER_CLUSTER), np.floor(counts / n * max_points).astype(int))
    picked = [rng.choice(np.flatnonzero(clusters == lab), size=int(k), replace=False) for lab, k in zip(labels, want, strict=True)]
    return np.sort(np.concatenate(picked))


def build_web_bundle(output_dir: str | Path, max_points: int = MAX_POINTS) -> Path:
    import anndata as ad

    output_dir = Path(output_dir)
    summary = json.loads((output_dir / "subcellspace_summary.json").read_text(encoding="utf-8"))
    adata = ad.read_h5ad(output_dir / "subcellspace_cells.h5ad", backed="r")
    obs = adata.obs
    bundle: dict = {"version": 1, "summary": {k: summary[k] for k in SUMMARY_KEYS if k in summary}}

    bundle["qc"] = {k: _hist(obs[k].to_numpy(float)) for k in ("n_transcripts", "n_genes", "area") if k in obs.columns}

    has_leiden = "leiden" in obs.columns
    clusters = obs["leiden"].astype(str).to_numpy() if has_leiden else np.zeros(adata.n_obs, dtype=str)
    markers = adata.uns.get("markers", {}) if "markers" in adata.uns else {}
    if has_leiden:
        labels, counts = np.unique(clusters, return_counts=True)
        order = sorted(range(len(labels)), key=lambda i: int(labels[i]) if labels[i].isdigit() else labels[i])
        bundle["clusters"] = [{"id": str(labels[i]), "n": int(counts[i]), "markers": list(markers.get(labels[i], []))}
                              for i in order]
    else:
        bundle["clusters"] = []

    idx = sample_cells(clusters, max_points)
    points: dict = {"n_total": int(adata.n_obs), "n_shown": int(len(idx))}
    if "spatial" in adata.obsm:
        xy = np.asarray(adata.obsm["spatial"])[idx]
        points["x"], points["y"] = np.rint(xy[:, 0]).astype(int).tolist(), np.rint(xy[:, 1]).astype(int).tolist()
    if "X_umap" in adata.obsm:
        um = np.asarray(adata.obsm["X_umap"])[idx]
        points["u1"], points["u2"] = np.rint(um[:, 0] * 100).astype(int).tolist(), np.rint(um[:, 1] * 100).astype(int).tolist()
    if has_leiden:
        c = clusters[idx]
        points["c"] = [int(v) for v in c] if all(v.isdigit() for v in labels) else c.tolist()
    bundle["points"] = points
    if adata.isbacked:
        adata.file.close()

    path = output_dir / "subcellspace_web.json"
    path.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    return path
