from __future__ import annotations

import pandas as pd

AVAILABLE_DENOISE_BACKENDS = ("none", "intracellular", "nuclear_only")


def apply_transcript_denoise(df: pd.DataFrame, backend: str) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    if backend not in AVAILABLE_DENOISE_BACKENDS:
        raise ValueError(f"Unknown denoise backend: {backend}")

    before = len(df)
    if backend == "none":
        filtered = df
    elif backend == "intracellular":
        filtered = df[df["CellComp"].isin(["Nuclear", "Cytoplasm"])].copy()
    else:
        filtered = df[df["CellComp"] == "Nuclear"].copy()

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
    return filtered, summary
