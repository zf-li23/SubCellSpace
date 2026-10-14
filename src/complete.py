"""Data completion: turn whatever a GEO sample provides into one cell × gene table.

Rules (owner, 2026-09-29 — AGENTS.md §6 Phase 7):

1. A vendor cell × gene matrix is used as-is.
2. Otherwise, transcripts with a cell_id are counted per cell.
3. Otherwise, transcripts + cell boundaries: transcripts are assigned to cells and counted by SOPA.
4. Transcripts without any cell information would need segmentation — not done here (tier S).

Cell coordinates come from the vendor cell table, else from transcript centroids, else from boundary centroids.
Everything derived (rather than copied from a vendor file) is recorded in ``provenance``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import anndata as ad
import numpy as np
import pandas as pd

from .analysis import count_by_cell_id, count_with_boundaries
from .io.sample import Sample

log = logging.getLogger(__name__)

XENIUM_MIN_QV = 20  # Xenium Ranger only counts transcripts with qv >= 20 into cell_feature_matrix

TIERS = {
    "A": "transcripts assigned to cells (cell_id or boundaries)",
    "B": "cell x gene matrix + cell coordinates, no cell-assigned transcripts",
    "C": "cell x gene matrix only, no coordinates",
    "S": "transcripts without cell information (needs segmentation)",
    "D": "unreadable",
}


class SegmentationRequiredError(RuntimeError):
    """Transcripts exist but there is no matrix, cell_id or boundary to build cells from."""


@dataclass
class Completion:
    table: ad.AnnData
    tier: str
    provenance: dict[str, str] = field(default_factory=dict)
    checks: dict[str, float] = field(default_factory=dict)


def assess_tier(s: Sample) -> str:
    if s.transcripts is not None and (s.has_cell_ids or s.boundaries is not None):
        return "A"
    if s.matrix is not None:
        has_coords = s.cells is not None and {"x", "y"} <= set(s.cells.columns)
        return "B" if has_coords or s.boundaries is not None else "C"
    if s.transcripts is not None:
        return "S"
    return "D"


def _countable(s: Sample) -> pd.DataFrame:
    """Gene transcripts usable for counting (controls dropped; Xenium qv >= 20)."""
    tx = s.transcripts[~s.transcripts["is_control"]]
    if s.platform == "xenium" and "qv" in tx.columns:
        tx = tx[tx["qv"] >= XENIUM_MIN_QV]
    return tx


def _coordinates(s: Sample, cell_ids: pd.Index) -> tuple[np.ndarray | None, str]:
    if s.cells is not None and {"x", "y"} <= set(s.cells.columns) and cell_ids.isin(s.cells.index).all():
        return s.cells.loc[cell_ids, ["x", "y"]].to_numpy(float), f"vendor cell table ({s.sources.get('cells')})"
    if s.transcripts is not None and s.has_cell_ids:
        cent = s.transcripts[s.transcripts["cell_id"].notna()].groupby("cell_id", observed=True)[["x", "y"]].mean()
        if cell_ids.isin(cent.index).all():
            return cent.loc[cell_ids].to_numpy(float), "derived: mean position of the cell's transcripts"
    if s.boundaries is not None and cell_ids.isin(s.boundaries.index).all():
        c = s.boundaries.loc[cell_ids].geometry.centroid
        return np.c_[c.x.to_numpy(), c.y.to_numpy()], "derived: centroid of the vendor cell boundary"
    return None, "none"


DUPLICATE_ROWS_THRESHOLD = 0.05  # above this, exact duplicate transcript rows are an upload artefact


def drop_duplicate_transcripts(s: Sample) -> tuple[float, int]:
    """Fraction of exact duplicate transcript rows; removes them when above the threshold.

    Some GEO uploads contain every transcript twice (GSE278766/GSM8554642: matrix = 0.5 × assigned transcripts
    for every cell and gene). Real transcripts essentially never share coordinates, gene and cell.
    """
    if s.transcripts is None or s.transcripts.empty:
        return 0.0, 0
    cols = [c for c in ("x", "y", "z", "gene", "cell_id") if c in s.transcripts.columns]
    dup = s.transcripts.duplicated(cols).to_numpy()
    frac = float(dup.mean())
    if frac <= DUPLICATE_ROWS_THRESHOLD:
        return frac, 0
    s.transcripts = s.transcripts[~dup].reset_index(drop=True)
    return frac, int(dup.sum())


def complete(s: Sample) -> Completion:
    tier = assess_tier(s)
    prov: dict[str, str] = {"files": ", ".join(f"{k}={v}" for k, v in s.sources.items())}
    checks: dict[str, float] = {}

    dup_frac, removed = drop_duplicate_transcripts(s)
    checks["duplicate_transcript_rows"] = round(dup_frac, 4)
    if removed:
        prov["transcripts"] = f"derived: {removed:,} exact duplicate rows removed ({dup_frac:.1%} of the upload)"

    if s.matrix is not None:
        table = s.matrix.copy()
        prov["matrix"] = f"vendor ({s.sources.get('matrix')})"
        if s.transcripts is not None and s.has_cell_ids:
            assigned = int(_countable(s)["cell_id"].notna().sum())
            checks["matrix_vs_assigned_transcripts"] = round(float(table.X.sum()) / assigned, 4) if assigned else float("nan")
    elif s.transcripts is not None and s.has_cell_ids:
        table = count_by_cell_id(_countable(s))
        prov["matrix"] = "derived: assigned transcripts counted per vendor cell_id" + (
            f" (qv >= {XENIUM_MIN_QV})" if s.platform == "xenium" else ""
        )
    elif s.transcripts is not None and s.boundaries is not None:
        tx = _countable(s)
        table, assigned = count_with_boundaries(tx, s.boundaries)
        s.transcripts["cell_id"] = pd.Categorical(assigned.reindex(s.transcripts.index))
        prov["matrix"] = "derived: transcripts assigned to vendor boundaries and counted (sopa.aggregate)"
        prov["cell_id"] = "derived: sopa.spatial.assign_transcript_to_cell on vendor boundaries"
    elif s.transcripts is not None:
        raise SegmentationRequiredError(f"{s.sample_dir}: transcripts have no cell_id, no boundaries and no matrix")
    else:
        raise RuntimeError(f"{s.sample_dir}: nothing to build cells from")

    xy, coord_src = _coordinates(s, table.obs_names)
    prov["coordinates"] = coord_src
    if xy is not None:
        table.obsm["spatial"] = xy
    elif tier == "B":
        tier = "C"

    if s.cells is not None:
        extra = [c for c in s.cells.columns if c not in ("x", "y")]
        if extra:
            table.obs = table.obs.join(s.cells[extra], how="left")
    if s.annotations is not None:
        ann = s.annotations.add_prefix("author_")
        table.obs = table.obs.join(ann, how="left")
        prov["annotations"] = f"author ({s.sources.get('annotations')})"

    table.obs["n_transcripts"] = np.asarray(table.X.sum(axis=1)).ravel()
    table.obs["n_genes"] = np.asarray((table.X > 0).sum(axis=1)).ravel()
    table.obs_names.name = "cell_id"
    log.info("Completed %s: tier %s, %d cells x %d genes", s.sample_dir.name, tier, table.n_obs, table.n_vars)
    return Completion(table=table, tier=tier, provenance=prov, checks=checks)
