from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import anndata as ad
from scipy.sparse import csr_matrix


@pytest.fixture
def sample_transcripts_df() -> pd.DataFrame:
    """CosMx-style transcript DataFrame with 100 rows across 10 cells, 5 FOVs."""
    rng = np.random.default_rng(42)
    n = 100
    fovs = rng.integers(1, 6, size=n)
    cell_ids = rng.integers(1, 11, size=n)
    targets = rng.choice(["GeneA", "GeneB", "GeneC", "GeneD", "GeneE"], size=n)
    comps = rng.choice(["Nuclear", "Cytoplasm", "Membrane"], size=n)
    cells = [f"{f}_{c}" for f, c in zip(fovs, cell_ids)]

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
def sample_anndata() -> ad.AnnData:
    """Small AnnData with 50 cells, 20 genes, spatial coordinates, and cluster/spatial_domain obs."""
    rng = np.random.default_rng(123)
    n_obs, n_vars = 50, 20
    X = rng.poisson(lam=3, size=(n_obs, n_vars)).astype(np.float32)
    adata = ad.AnnData(X=X)
    adata.var_names = [f"Gene_{i}" for i in range(n_vars)]
    adata.obs_names = [f"Cell_{i}" for i in range(n_obs)]
    adata.obsm["spatial"] = rng.uniform(0, 100, size=(n_obs, 2)).astype(np.float32)
    adata.obsm["X_pca"] = rng.normal(size=(n_obs, 10)).astype(np.float32)
    adata.obs["cluster"] = [str(i % 5) for i in range(n_obs)]
    adata.obs["spatial_domain"] = [str(i % 4) for i in range(n_obs)]
    adata.obs["total_counts"] = X.sum(axis=1)
    adata.obs["n_genes_by_counts"] = (X > 0).sum(axis=1)
    adata.obs["n_transcripts"] = adata.obs["total_counts"]
    adata.layers["counts"] = X.copy()
    adata.layers["lognorm"] = np.log1p(X)

    # Build a simple spatial connectivities matrix
    from sklearn.neighbors import kneighbors_graph

    spatial_coords = adata.obsm["spatial"]
    knn = kneighbors_graph(spatial_coords, n_neighbors=min(5, n_obs - 1), mode="connectivity")
    adata.obsp["spatial_connectivities"] = csr_matrix(knn)
    return adata


@pytest.fixture
def sample_transcripts_csv(tmp_path, sample_transcripts_df) -> str:
    """Write sample_transcripts_df to a temporary CSV and return its path."""
    csv_path = tmp_path / "test_transcripts.csv"
    sample_transcripts_df.to_csv(csv_path, index=False)
    return str(csv_path)