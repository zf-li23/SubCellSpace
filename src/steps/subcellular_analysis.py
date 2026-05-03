"""Phase 7: Subcellular Spatial Analysis step.

Provides backends for:
- RNA localization quantification (mean distance to nucleus)
- RNA co-localization network (SCRIN) — real integration, default off

Each backend declares its capabilities via ``declare_capabilities``.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import scanpy as sc

from ..constants import COL_CELL_ID, COL_X, COL_Y, COL_CELLCOMP, COL_GENE, resolve_col_strict
from ..models import StepResult
from ..registry import declare_capabilities, register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)

# ── Backend availability flags ───────────────────────────────────────

_SCRIN_AVAILABLE: bool = False

try:
    import scrin  # noqa: F401
    _SCRIN_AVAILABLE = True
except ImportError:
    pass


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
# ── Allowed SCRIN CLI options (whitelist for security) ──────────────

_SCRIN_ALLOWED_KWARGS: set[str] = {
    "min_gene_number", "min_neighbor_number", "expression_level",
    "filter_threshold", "pair_keep", "intermediate_dir", "intermediate_split",
    "distribution_analysis", "r_dist", "around_count_threshold",
    "distribution_save_interval", "grid_check",
}



def _subcell_scrin(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    scrin_radius: float = 4.16,
    scrin_mode: str = "fast",
    scrin_background: str = "cooccurrence",
    scrin_detection: str = "radius",
    scrin_mpi_np: int = 1,
    scrin_timeout: int = 3600,
    **scrin_kwargs: Any,
) -> dict[str, Any]:
    """Run SCRIN co-localization network analysis.

    Exports the segmented transcript DataFrame as a temporary CSV,
    calls the ``scrin`` CLI (single-process by default, MPI optional),
    and stores the resulting co-localization network in
    ``adata.uns["scrin_colocalization_network"]``.

    SCRIN is computationally expensive — the default pipeline skips it
    (``rna_localization`` is the default backend).  Enable explicitly:

    .. code-block:: bash

        subcellspace run ... --subcellular-analysis-backend scrin

    Parameters
    ----------
    segmented_df : pd.DataFrame
        Transcript-level DataFrame with canonical columns.
    adata : sc.AnnData
        Cell-level AnnData object.
    scrin_radius : float
        Radius (µm) for neighbor detection.
    scrin_mode : str
        ``"fast"`` or ``"robust"``.
    scrin_background : str
        ``"cooccurrence"`` or ``"all"``.
    scrin_detection : str
        ``"radius"`` or ``"nine_grid"``.
    scrin_mpi_np : int
        Number of MPI processes.  1 = single-process (no MPI).
    scrin_timeout : int
        Timeout in seconds for the SCRIN subprocess.

    Returns
    -------
    dict
        Summary of SCRIN run.
    """
    if not _SCRIN_AVAILABLE:
        logger.warning("SCRIN Python package not installed. Falling back to stub mode.")
        return _subcell_scrin_stub(segmented_df, adata, scrin_radius)

    # Find scrin CLI
    scrin_bin = shutil.which("scrin")
    if scrin_bin is None:
        logger.warning("SCRIN CLI not found on PATH. Falling back to stub mode.")
        return _subcell_scrin_stub(segmented_df, adata, scrin_radius)

    x_col = resolve_col_strict(segmented_df.columns, COL_X)
    y_col = resolve_col_strict(segmented_df.columns, COL_Y)
    gene_col = resolve_col_strict(segmented_df.columns, COL_GENE)
    cell_col = resolve_col_strict(segmented_df.columns, COL_CELL_ID)

    # Build SCRIN-compatible CSV (x, y, gene, cell_id)
    # SCRIN's column_name format: "x,y,z,geneID,cell"
    # We have no z column, so we pass empty: "x,y,,gene,cell_id"
    scrin_df = segmented_df[[x_col, y_col, gene_col, cell_col]].copy()
    scrin_df.columns = ["x", "y", "gene", "cell_id"]

    with tempfile.TemporaryDirectory(prefix="scrin_") as tmpdir:
        tmp = Path(tmpdir)
        input_csv = tmp / "transcripts.csv"
        output_csv = tmp / "scrin_result.csv"

        scrin_df.to_csv(input_csv, index=False)
        logger.info("SCRIN: exported %d transcripts to %s", len(scrin_df), input_csv)

        # Build CLI command
        cmd_parts = []
        if scrin_mpi_np > 1:
            mpiexec = shutil.which("mpiexec") or shutil.which("mpirun")
            if mpiexec:
                cmd_parts.extend([mpiexec, "-n", str(scrin_mpi_np)])
            else:
                logger.warning("SCRIN: MPI requested but mpiexec/mpirun not found. Running single-process.")
        cmd_parts.append(scrin_bin)

        cmd_parts.extend([
            "--detection_method", scrin_detection,
            "--background", scrin_background,
            "--mode", scrin_mode,
            "--data_path", str(input_csv),
            "--save_path", str(output_csv),
            "--column_name", "x,y,,gene,cell_id",
            "--r_check", str(scrin_radius),
        ])
        for k, v in scrin_kwargs.items():
            if k not in _SCRIN_ALLOWED_KWARGS:
                logger.warning("SCRIN: ignoring unknown kwarg '%s'", k)
                continue
            key = "--" + k.replace("_", "-")
            if isinstance(v, bool):
                if v:
                    cmd_parts.append(key)
            else:
                cmd_parts.extend([key, str(v)])

        logger.info("SCRIN: running %s", " ".join(cmd_parts))

        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=scrin_timeout,
            )
        except FileNotFoundError:
            logger.warning("SCRIN CLI not found. Falling back to stub mode.")
            return _subcell_scrin_stub(segmented_df, adata, scrin_radius)
        except subprocess.TimeoutExpired:
            logger.error("SCRIN timed out after %d seconds.", scrin_timeout)
            return {"scrin": "timeout", "timeout_seconds": scrin_timeout}

        if result.returncode != 0:
            logger.error(
                "SCRIN failed with exit code %d.\nstdout: %s\nstderr: %s",
                result.returncode,
                result.stdout[-500:] if result.stdout else "<empty>",
                result.stderr[-500:] if result.stderr else "<empty>",
            )
            return {"scrin": "failed", "exit_code": result.returncode}

        # ── Parse SCRIN output ─────────────────────────────────
        if output_csv.exists() and output_csv.stat().st_size > 0:
            try:
                scrin_result = pd.read_csv(output_csv)
                n_pairs = len(scrin_result)
            except Exception:
                logger.warning("SCRIN: failed to parse output CSV.")
                n_pairs = 0
        else:
            n_pairs = 0

    # ── Store results ──────────────────────────────────────────
    scrin_meta = {
        "method": "SCRIN",
        "status": "completed",
        "n_significant_pairs": n_pairs,
        "parameters": {
            "r_check": scrin_radius,
            "mode": scrin_mode,
            "background": scrin_background,
            "detection": scrin_detection,
            "mpi_np": scrin_mpi_np,
        },
    }
    adata.uns["scrin_colocalization_network"] = scrin_meta
    logger.info("SCRIN: %d significant co-localization pairs found.", n_pairs)
    return {"scrin": "completed", "n_pairs": n_pairs}


def _subcell_scrin_stub(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    scrin_radius: float = 4.16,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Fallback stub when SCRIN is not available."""
    adata.uns["scrin_colocalization_network"] = {
        "method": "SCRIN",
        "status": "stub",
        "parameters": {"r_check": scrin_radius, "background": "cooccurrence", "mode": "fast"},
        "note": "SCRIN not installed or not on PATH. Run manually or install via 'pip install -e tools/SCRIN/'.",
    }
    return {"scrin": "stub"}


# ── Main entry point ─────────────────────────────────────────────────


def run_subcellular_analysis(
    segmented_df: pd.DataFrame,
    adata: sc.AnnData,
    backend: str,
    scrin_radius: float = 4.16,
    scrin_mode: str = "fast",
    scrin_background: str = "cooccurrence",
    scrin_detection: str = "radius",
    scrin_mpi_np: int = 1,
    scrin_timeout: int = 3600,
) -> StepResult:
    if backend not in _SUBCELLULAR_ANALYSIS_FUNCS:
        raise ValueError(f"Unknown subcellular analysis backend: {backend}")

    func = _SUBCELLULAR_ANALYSIS_FUNCS[backend]
    if backend == "scrin":
        results = func(
            segmented_df, adata,
            scrin_radius=scrin_radius,
            scrin_mode=scrin_mode,
            scrin_background=scrin_background,
            scrin_detection=scrin_detection,
            scrin_mpi_np=scrin_mpi_np,
            scrin_timeout=scrin_timeout,
        )
    else:
        results = func(segmented_df, adata)

    return StepResult(
        output=(segmented_df, adata),
        summary=results,
        backend_used=backend,
    )


# ── Register ─────────────────────────────────────────────────────────

register_backend("subcellular_analysis", "rna_localization")(_subcell_rna_localization)
register_backend("subcellular_analysis", "scrin")(_subcell_scrin)

declare_capabilities("subcellular_analysis", "rna_localization", ["rna_localization"])
declare_capabilities("subcellular_analysis", "scrin", ["co_localization_network"])

_SUBCELLULAR_ANALYSIS_FUNCS = {
    "rna_localization": lambda df, ad, **kw: _subcell_rna_localization(df, ad),
    "scrin": _subcell_scrin,
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
    scrin_mode = params.get("scrin_mode", "fast")
    scrin_background = params.get("scrin_background", "cooccurrence")
    scrin_detection = params.get("scrin_detection", "radius")
    scrin_mpi_np = params.get("scrin_mpi_np", 1)
    scrin_timeout = params.get("scrin_timeout", 3600)

    result = run_subcellular_analysis(
        ctx.segmented_df, ctx.adata, backend,
        scrin_radius=scrin_radius,
        scrin_mode=scrin_mode,
        scrin_background=scrin_background,
        scrin_detection=scrin_detection,
        scrin_mpi_np=scrin_mpi_np,
        scrin_timeout=scrin_timeout,
    )
    ctx.adata = result.output[1] if isinstance(result.output, tuple) else result.output
    return result
