from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

# ── Backend implementations ────────────────────────────────────────────────


def _denoise_none(df: pd.DataFrame) -> pd.DataFrame:
    return df


def _denoise_intracellular(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["CellComp"].isin(["Nuclear", "Cytoplasm"])].copy()


def _denoise_nuclear_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["CellComp"] == "Nuclear"].copy()


def _denoise_sparc(df: pd.DataFrame) -> pd.DataFrame:
    """spARC (Spatially-Aware Regularized Clustering) denoising.

    Builds a cell×gene expression matrix from the transcript DataFrame,
    runs spARC to denoise the expression matrix (smoothing expression
    values based on spatial and expression neighbourhoods), and stores
    the denoised matrix for downstream use.

    The transcript-level DataFrame is returned unchanged (all transcripts
    pass through), because spARC operates at the expression level, not
    the transcript level.
    """
    from SPARC import spARC

    # Build cell×gene expression matrix
    expr_matrix = df.pivot_table(
        index="cell",
        columns="target",
        values="target",
        aggfunc="count",
        fill_value=0,
    ).astype(np.float64)
    cells = expr_matrix.index.tolist()
    genes = expr_matrix.columns.tolist()
    X = expr_matrix.to_numpy()

    # Build cell-level spatial coordinates (mean per cell)
    spatial_coords = df.groupby("cell")[["x_global_px", "y_global_px"]].mean().to_numpy()

    # Run spARC
    model = spARC(
        expression_graph=True,
        spatial_graph=True,
        expression_knn=15,
        spatial_knn=15,
        expression_n_pca=min(50, X.shape[0] - 1, X.shape[1] - 1),
        random_state=42,
    )
    X_denoised = model.fit_transform(X, spatial_X=spatial_coords)

    # Store denoised matrix as DataFrame for downstream use
    denoised_expr_df = pd.DataFrame(
        X_denoised,
        index=cells,
        columns=genes,
    )
    # Attach to DataFrame as an attribute so the step runner can extract it
    df.attrs["denoised_expression"] = denoised_expr_df
    df.attrs["denoised_backend"] = "sparc"
    return df


# Register backends (order: (step_name, backend_name))
register_backend("denoise", "none")(_denoise_none)
register_backend("denoise", "intracellular")(_denoise_intracellular)
register_backend("denoise", "nuclear_only")(_denoise_nuclear_only)
register_backend("denoise", "sparc")(_denoise_sparc)

# Dispatch table
_DENOISE_FUNCS = {
    "none": _denoise_none,
    "intracellular": _denoise_intracellular,
    "nuclear_only": _denoise_nuclear_only,
    "sparc": _denoise_sparc,
}


# ── Main entry point ──────────────────────────────────────────────────────


def apply_transcript_denoise(df: pd.DataFrame, backend: str) -> StepResult:
    if backend not in _DENOISE_FUNCS:
        raise ValueError(f"Unknown denoise backend: {backend}. Available: {list(_DENOISE_FUNCS)}")

    before = len(df)
    filtered = _DENOISE_FUNCS[backend](df)
    after = len(filtered)
    dropped = before - after
    ratio = 0.0 if before == 0 else dropped / before
    summary = {
        "denoise_backend": backend,
        "before_transcripts": int(before),
        "after_transcripts": int(after),
        "dropped_transcripts": int(dropped),
        "drop_ratio": float(ratio),
    }
    return StepResult(output=filtered, summary=summary, backend_used=backend)


# ── Step runner (registered for pipeline engine) ──────────────────────────


@register_runner("denoise")
def _run_denoise(
    ctx: ExecutionContext,
    backend: str,
    _params: dict[str, Any],  # noqa: ARG001
) -> StepResult:
    if ctx.transcripts is None:
        raise ValueError("No transcripts loaded before denoise step")
    result = apply_transcript_denoise(ctx.transcripts, backend)

    # Extract denoised expression matrix from DataFrame attrs (set by spARC backend)
    if result.output.attrs.get("denoised_expression") is not None:
        ctx.denoised_expression = result.output.attrs.pop("denoised_expression")

    ctx.denoised_df = result.output
    return result
