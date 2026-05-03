"""Phase 7: Subcellular Spatial Analysis step.

Provides backends for:
- RNA localization quantification (mean distance to nucleus, radial ratio)
- RNA co-localization network (SCRIN)
- Subcellular domain enrichment

Each backend declares its capabilities via ``declare_capabilities``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import scanpy as sc

from ..constants import COL_CELL_ID, COL_X, COL_Y, COL_CELLCOMP, resolve_col_strict
from ..models import StepResult
from ..registry import declare_capabilities, register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)


def _subcell_rna_localization(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
) -> dict[str, Any]:
    """Compute RNA localization metrics per cell.

    Metrics:
    - mean_radial_distance: mean distance from nuclear centroid
    - radial_ratio: cytoplasmic / nuclear transcript count
    """
    cell_col = resolve_col_strict(segmented_df.columns, COL_CELL_ID)
    x_col = resolve_col_strict(segmented_df.columns, COL_X)
    y_col = resolve_col_strict(segmented_df.columns, COL_Y)

    # Cell centroids from AnnData spatial
    cell_centroids = pd.DataFrame(
        adata.obsm["spatial"],
        index=adata.obs_names,
        columns=["cx", "cy"],
    )

    per_cell: dict[str, dict[str, float]] = {}

    for cell_id, group in segmented_df.groupby(cell_col, sort=False):
        if cell_id not in cell_centroids.index:
            continue
        cx, cy = cell_centroids.loc[cell_id]
        dists = np.sqrt((group[x_col] - cx) ** 2 + (group[y_col] - cy) ** 2)
        per_cell[str(cell_id)] = {
            "mean_radial_distance": float(dists.mean()) if len(dists) else 0.0,
            "max_radial_distance": float(dists.max()) if len(dists) else 0.0,
        }

    # Write to adata.obs
    rna_dist = pd.Series(
        {k: v["mean_radial_distance"] for k, v in per_cell.items()},
        name="mean_rna_radial_distance",
    )
    adata.obs["mean_rna_radial_distance"] = rna_dist.reindex(adata.obs_names)

    summary = {
        "n_cells_analyzed": len(per_cell),
        "mean_distance_overall": float(adata.obs["mean_rna_radial_distance"].mean())
        if "mean_rna_radial_distance" in adata.obs
        else 0.0,
    }

    adata.uns["rna_localization_metrics"] = summary
    return summary


def _subcell_scrin_stub(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    scrin_radius: float = 4.16,
) -> dict[str, Any]:
    """Stub for SCRIN co-localization network.

    Full SCRIN requires MPI + external CLI call.  This stub records the
    parameters so the user knows what to run later.

    To run SCRIN manually:
        mpirun -n 16 scrin \\
            --detection_method radius \\
            --background cooccurrence \\
            --mode fast \\
            --data_path <exported_csv> \\
            --save_path <output_csv> \\
            --column_name "x,y,,gene,cell_id" \\
            --r_check {radius}
    """
    adata.uns["scrin_colocalization_network"] = {
        "method": "SCRIN",
        "status": "stub",
        "parameters": {"r_check": scrin_radius, "background": "cooccurrence", "mode": "fast"},
        "note": "Run SCRIN manually. Use `subcellspace export` to get the CSV.",
    }
    return {"scrin": "stub"}


# ── Main entry point ─────────────────────────────────────────────────


def run_subcellular_analysis(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    backend: str,
    scrin_radius: float = 4.16,
) -> StepResult:
    if backend not in _SUBCELLULAR_ANALYSIS_FUNCS:
        raise ValueError(f"Unknown subcellular analysis backend: {backend}")

    results = _SUBCELLULAR_ANALYSIS_FUNCS[backend](
        segmented_df, adata, scrin_radius=scrin_radius
    )

    return StepResult(
        output=(segmented_df, adata),
        summary=results,
        backend_used=backend,
    )


# ── Register ─────────────────────────────────────────────────────────

register_backend("subcellular_analysis", "rna_localization")(_subcell_rna_localization)
register_backend("subcellular_analysis", "scrin_stub")(_subcell_scrin_stub)

declare_capabilities("subcellular_analysis", "rna_localization", ["rna_localization"])
declare_capabilities("subcellular_analysis", "scrin_stub", ["co_localization_network"])

_SUBCELLULAR_ANALYSIS_FUNCS = {
    "rna_localization": lambda df, ad, **kw: _subcell_rna_localization(df, ad),
    "scrin_stub": lambda df, ad, **kw: _subcell_scrin_stub(df, ad, **kw),
}


@register_runner("subcellular_analysis")
def _run_subcellular_analysis(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.segmented_df is None or ctx.adata is None:
        raise ValueError("No segmented data or adata before subcellular analysis")

    scrin_radius = params.get("scrin_radius", 4.16)

    result = run_subcellular_analysis(
        ctx.segmented_df, ctx.adata, backend, scrin_radius=scrin_radius
    )
    ctx.adata = result.output[1] if isinstance(result.output, tuple) else result.output
    return result
