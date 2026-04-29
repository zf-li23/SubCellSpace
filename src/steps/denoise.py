from __future__ import annotations

from typing import TYPE_CHECKING, Any

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


# Register backends (order: (step_name, backend_name))
register_backend("denoise", "none")(_denoise_none)
register_backend("denoise", "intracellular")(_denoise_intracellular)
register_backend("denoise", "nuclear_only")(_denoise_nuclear_only)

# Dispatch table
_DENOISE_FUNCS = {
    "none": _denoise_none,
    "intracellular": _denoise_intracellular,
    "nuclear_only": _denoise_nuclear_only,
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
    ctx.denoised_df = result.output
    return result
