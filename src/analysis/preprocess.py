"""Cell-table preprocessing, ported from SOPA's ``scanpy-preprocess`` command."""

from __future__ import annotations

import anndata as ad
import pandas as pd

LEIDEN_RESOLUTION = 1.0
N_MARKERS = 10


def preprocess(adata: ad.AnnData, resolution: float = LEIDEN_RESOLUTION) -> ad.AnnData:
    """``sopa scanpy-preprocess`` (sopa/cli/app.py) on an AnnData, without SOPA's image requirement.

    Changes vs upstream: no ``read_zarr_standardized`` image sanity check; explicit PCA so the number of PCs and
    neighbours can be capped for very small samples (upstream defaults otherwise: 50 PCs, 15 neighbours).
    """
    import scanpy as sc

    adata.layers["counts"] = adata.X.copy()
    sc.pp.normalize_total(adata)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata)
    use_hvg = adata.var["highly_variable"].sum() > 50
    if not use_hvg:  # same fallback as SOPA: too few HVGs → use all genes
        hvg = adata.var.pop("highly_variable")
    # SOPA's defaults (50 PCs, 15 neighbours) only cap down for very small samples
    n_pcs = min(50, adata.n_obs - 1, adata.n_vars - 1)
    sc.pp.pca(adata, n_comps=n_pcs, mask_var="highly_variable" if use_hvg else None)
    sc.pp.neighbors(adata, n_neighbors=min(15, adata.n_obs - 1))
    sc.tl.umap(adata)
    sc.tl.leiden(adata, resolution=resolution, flavor="igraph")
    if not use_hvg:
        adata.var["highly_variable"] = hvg
    return adata


def add_markers(adata: ad.AnnData, groupby: str = "leiden", n: int = N_MARKERS) -> None:
    import scanpy as sc

    if groupby not in adata.obs or adata.obs[groupby].nunique() < 2:
        return
    sc.tl.rank_genes_groups(adata, groupby, method="wilcoxon", n_genes=n)
    names = pd.DataFrame(adata.uns["rank_genes_groups"]["names"])
    adata.uns["markers"] = {str(g): names[g].astype(str).tolist() for g in names.columns}
