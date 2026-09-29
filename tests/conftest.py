from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_transcripts_df() -> pd.DataFrame:
    """CosMx-style transcript DataFrame with 100 rows across 10 cells, 5 FOVs."""
    rng = np.random.default_rng(42)
    n = 100
    fovs = rng.integers(1, 6, size=n)
    cell_ids = rng.integers(1, 11, size=n)
    targets = rng.choice(["GeneA", "GeneB", "GeneC", "GeneD", "GeneE"], size=n)
    comps = rng.choice(["Nuclear", "Cytoplasm", "Membrane"], size=n)
    cells = [f"{f}_{c}" for f, c in zip(fovs, cell_ids, strict=False)]

    return pd.DataFrame(
        {
            "fov": fovs,
            "cell_ID": cell_ids,
            "x_global_px": rng.uniform(0, 1000, size=n),
            "y_global_px": rng.uniform(0, 1000, size=n),
            "x_local_px": rng.uniform(0, 500, size=n),
            "y_local_px": rng.uniform(0, 500, size=n),
            "z": rng.integers(-1, 1, size=n),
            "target": targets,
            "CellComp": comps,
            "cell": cells,
        }
    )


@pytest.fixture
def sample_transcripts_csv(tmp_path, sample_transcripts_df) -> str:
    """Write sample_transcripts_df to a temporary CSV and return its path."""
    csv_path = tmp_path / "test_transcripts.csv"
    sample_transcripts_df.to_csv(csv_path, index=False)
    return str(csv_path)
