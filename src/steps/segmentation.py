from __future__ import annotations

import pandas as pd

AVAILABLE_SEGMENTATION_BACKENDS = ("provided_cells", "fov_cell_id")


def assign_cells(df: pd.DataFrame, backend: str) -> tuple[pd.DataFrame, dict[str, int | str]]:
    if backend not in AVAILABLE_SEGMENTATION_BACKENDS:
        raise ValueError(f"Unknown segmentation backend: {backend}")

    if backend == "provided_cells":
        assigned = df[df["cell"].notna() & (df["cell"].astype(str) != "")].copy()
    else:
        assigned = df.copy()
        assigned["cell"] = assigned["fov"].astype(str) + "_" + assigned["cell_ID"].astype(str)

    summary = {
        "segmentation_backend": backend,
        "n_transcripts_assigned": int(len(assigned)),
        "n_cells_assigned": int(assigned["cell"].nunique()),
    }
    return assigned, summary
