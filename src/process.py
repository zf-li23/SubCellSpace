"""Process one GEO sample: read → complete → SOPA preprocessing → outputs.

Outputs (all in ``out_dir``, never in the raw sample directory unless the caller points there):

- ``subcellspace_cells.h5ad``  the same table: all genes, raw counts in ``layers["counts"]``, log-normalised ``X``,
  UMAP, leiden clusters, per-cluster marker genes
- ``subcellspace_summary.json`` full-data statistics, data tier and provenance (what was copied, what was derived)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import anndata as ad
import numpy as np

from .analysis import add_markers, preprocess
from .complete import TIERS, Completion, complete
from .io import read_sample
from .io.sample import Sample

log = logging.getLogger(__name__)

MIN_TRANSCRIPTS_PER_CELL = 10  # cells below this are kept in the stats but left out of clustering


def code_version() -> str:
    """Git commit of the code that produced the outputs (BUILD file written by scripts/deploy_cluster.sh)."""
    build = Path(__file__).with_name("BUILD")
    if build.exists():
        return build.read_text().strip()
    import subprocess

    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _median(values: np.ndarray) -> float | None:
    return float(np.median(values)) if len(values) else None


def compute_summary(s: Sample, c: Completion) -> dict:
    """Statistics on the **full** data (before any QC filter or plotting subsample)."""
    t = c.table
    with_counts = t.obs["n_transcripts"].to_numpy() > 0
    out: dict = {
        "platform": s.platform,
        "sample_dir": s.sample_dir.name,
        "data_tier": c.tier,
        "data_tier_meaning": TIERS[c.tier],
        "n_cells": int(t.n_obs),
        "n_cells_with_transcripts": int(with_counts.sum()),
        "gene_panel_size": int(t.n_vars),
        "n_transcripts_in_cells": int(t.X.sum()),
        "median_transcripts": _median(t.obs["n_transcripts"].to_numpy()[with_counts]),
        "median_genes": _median(t.obs["n_genes"].to_numpy()[with_counts]),
    }
    if s.transcripts is not None:
        tx = s.transcripts
        genes = tx[~tx["is_control"]]
        out.update({
            "n_transcripts": int(len(genes)),
            "n_control_transcripts": int(tx["is_control"].sum()),
            "n_genes": int(genes["gene"].nunique()),
            "fraction_transcripts_in_cells": round(float(genes["cell_id"].notna().mean()), 4) if len(genes) else None,
        })
        if "fov" in tx.columns:
            out["n_fovs"] = int(tx["fov"].nunique())
        if "qv" in tx.columns:
            out["fraction_qv_ge_20"] = round(float((genes["qv"] >= 20).mean()), 4)
    else:
        out.update({"n_transcripts": None, "n_genes": int((np.asarray(t.X.sum(axis=0)).ravel() > 0).sum())})
    if "area" in t.obs.columns:
        out["median_cell_area_um2"] = _median(t.obs["area"].dropna().to_numpy())
    out["checks"] = c.checks
    out["provenance"] = c.provenance
    out["notes"] = s.notes
    return out


def _h5ad_safe(adata: ad.AnnData) -> ad.AnnData:
    for col in adata.obs.columns:
        if adata.obs[col].dtype == object:
            adata.obs[col] = adata.obs[col].astype("string").fillna("NA").astype("category")
    return adata


def process_sample(sample_dir: str | Path, out_dir: str | Path, platform: str | None = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    s = read_sample(sample_dir, platform=platform)
    c = complete(s)
    summary = compute_summary(s, c)

    table = c.table
    keep = table.obs["n_transcripts"].to_numpy() >= MIN_TRANSCRIPTS_PER_CELL
    summary["n_cells_clustered"] = int(keep.sum())
    summary["min_transcripts_for_clustering"] = MIN_TRANSCRIPTS_PER_CELL

    if keep.sum() >= 3:
        processed = preprocess(_h5ad_safe(table[keep].copy()))
        add_markers(processed)
        summary["n_clusters"] = int(processed.obs["leiden"].nunique()) if "leiden" in processed.obs else 0
    else:
        processed = _h5ad_safe(table.copy())
        processed.layers["counts"] = processed.X.copy()
        summary["n_clusters"] = 0
        s.notes.append(f"fewer than 3 cells with >= {MIN_TRANSCRIPTS_PER_CELL} transcripts; not clustered")

    summary["software"] = {pkg: version(pkg) for pkg in ("sopa", "scanpy", "anndata", "spatialdata")}
    summary["software"]["subcellspace"] = code_version()
    summary["generated"] = datetime.now(UTC).isoformat(timespec="seconds")
    processed.uns["subcellspace_summary"] = json.dumps(summary)
    processed.write_h5ad(out_dir / "subcellspace_cells.h5ad")
    (out_dir / "subcellspace_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log.info("Processed %s → %s (tier %s, %d cells)", s.sample_dir.name, out_dir, c.tier, table.n_obs)
    return summary
