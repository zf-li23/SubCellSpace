from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from ..constants import COL_CELL_ID, COL_CELLCOMP, COL_GENE, COL_X, COL_Y, resolve_col_strict
from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

# ── Backend implementations ────────────────────────────────────────────────


def _denoise_none(df: pd.DataFrame) -> pd.DataFrame:
    return df


def _denoise_intracellular(df: pd.DataFrame) -> pd.DataFrame:
    cc = resolve_col_strict(df.columns, COL_CELLCOMP)
    return df[df[cc].isin(["Nuclear", "Cytoplasm"])].copy()


def _denoise_nuclear_only(df: pd.DataFrame) -> pd.DataFrame:
    cc = resolve_col_strict(df.columns, COL_CELLCOMP)
    return df[df[cc] == "Nuclear"].copy()


def _denoise_sparc(df: pd.DataFrame) -> pd.DataFrame:
    """spARC (Spatially-Aware Regularized Clustering) denoising."""
    from SPARC import spARC

    cell_col = resolve_col_strict(df.columns, COL_CELL_ID)
    gene_col = resolve_col_strict(df.columns, COL_GENE)
    x_col = resolve_col_strict(df.columns, COL_X)
    y_col = resolve_col_strict(df.columns, COL_Y)

    expr_matrix = pd.crosstab(
        index=df[cell_col],
        columns=df[gene_col].astype(str),
    ).astype(np.float64)
    cells = expr_matrix.index.tolist()
    genes = expr_matrix.columns.tolist()
    X = expr_matrix.to_numpy()

    spatial_coords = df.groupby(cell_col)[[x_col, y_col]].mean().to_numpy()

    model = spARC(
        expression_knn=15,
        spatial_knn=15,
        expression_n_pca=min(50, X.shape[0] - 1, X.shape[1] - 1),
        random_state=42,
    )
    X_denoised = model.fit_transform(X, spatial_X=spatial_coords)

    denoised_expr_df = pd.DataFrame(X_denoised, index=cells, columns=genes)
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
