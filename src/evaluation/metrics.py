from __future__ import annotations

from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import adjusted_rand_score, silhouette_score


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _series_distribution(series: pd.Series) -> dict[str, float]:
    counts = series.astype(str).value_counts(dropna=False)
    total = int(counts.sum())
    if total == 0:
        return {}
    return {str(k): float(v / total) for k, v in counts.to_dict().items()}


def _silhouette_from_pca(adata: ad.AnnData) -> float | None:
    if "cluster" not in adata.obs or "X_pca" not in adata.obsm:
        return None
    labels = adata.obs["cluster"].astype(str)
    if labels.nunique() < 2:
        return None

    pca = adata.obsm["X_pca"]
    n_dim = min(10, pca.shape[1])
    if n_dim < 2:
        return None

    try:
        return float(silhouette_score(pca[:, :n_dim], labels.to_numpy()))
    except Exception:
        return None


def _spatial_graph_metrics(adata: ad.AnnData) -> dict[str, Any]:
    matrix = adata.obsp.get("spatial_connectivities")
    if matrix is None:
        return {
            "graph_available": False,
        }

    graph = csr_matrix(matrix)
    graph_bool = graph.copy()
    graph_bool.data = np.ones_like(graph_bool.data)

    degrees = np.asarray(graph_bool.sum(axis=1)).ravel()
    n_nodes = int(graph.shape[0])
    n_edges = int(graph_bool.nnz // 2)
    n_components, _ = connected_components(graph_bool, directed=False)

    return {
        "graph_available": True,
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "avg_degree": float(degrees.mean()) if n_nodes else 0.0,
        "median_degree": float(np.median(degrees)) if n_nodes else 0.0,
        "connected_components": int(n_components),
    }


def build_layer_evaluation(
    raw_df: pd.DataFrame,
    denoised_df: pd.DataFrame,
    segmented_df: pd.DataFrame,
    adata: ad.AnnData,
) -> dict[str, Any]:
    transcripts_per_cell = (
        segmented_df.groupby("cell")["target"].size() if len(segmented_df) else pd.Series(dtype=float)
    )
    n_clusters = int(adata.obs["cluster"].nunique()) if "cluster" in adata.obs else 0
    n_cell_types = int(adata.obs["cell_type"].nunique()) if "cell_type" in adata.obs else 0
    n_domains = int(adata.obs["spatial_domain"].nunique()) if "spatial_domain" in adata.obs else 0

    if "cluster" in adata.obs and "spatial_domain" in adata.obs:
        try:
            domain_cluster_ari: float | None = float(
                adjusted_rand_score(adata.obs["cluster"].astype(str), adata.obs["spatial_domain"].astype(str))
            )
        except Exception:
            domain_cluster_ari = None
    else:
        domain_cluster_ari = None

    evaluation = {
        "ingestion": {
            "n_transcripts": int(len(raw_df)),
            "n_cells_raw": int(raw_df["cell"].astype(str).nunique()),
            "n_genes_raw": int(raw_df["target"].astype(str).nunique()),
            "n_fovs": int(raw_df["fov"].nunique()),
            "cellcomp_distribution": _series_distribution(raw_df["CellComp"]),
            "missing_cell_ratio": _safe_ratio(float(raw_df["cell"].isna().sum()), float(len(raw_df))),
        },
        "denoise": {
            "n_transcripts_before": int(len(raw_df)),
            "n_transcripts_after": int(len(denoised_df)),
            "retained_ratio": _safe_ratio(float(len(denoised_df)), float(len(raw_df))),
            "cellcomp_distribution_after": _series_distribution(denoised_df["CellComp"]) if len(denoised_df) else {},
        },
        "segmentation": {
            "n_transcripts_assigned": int(len(segmented_df)),
            "n_cells_assigned": int(segmented_df["cell"].nunique()) if len(segmented_df) else 0,
            "assignment_ratio": _safe_ratio(float(len(segmented_df)), float(len(denoised_df))),
            "mean_transcripts_per_cell": float(transcripts_per_cell.mean()) if len(transcripts_per_cell) else 0.0,
            "median_transcripts_per_cell": float(transcripts_per_cell.median()) if len(transcripts_per_cell) else 0.0,
        },
        "expression": {
            "n_cells_after_qc": int(adata.n_obs),
            "n_genes_after_hvg": int(adata.n_vars),
            "qc_pass_ratio_vs_segmented": _safe_ratio(
                float(adata.n_obs), float(segmented_df["cell"].nunique() if len(segmented_df) else 0)
            ),
            "median_total_counts": float(adata.obs["total_counts"].median()) if "total_counts" in adata.obs else 0.0,
            "median_n_genes_by_counts": float(adata.obs["n_genes_by_counts"].median())
            if "n_genes_by_counts" in adata.obs
            else 0.0,
        },
        "clustering": {
            "n_clusters": n_clusters,
            "largest_cluster_fraction": _safe_ratio(
                float(adata.obs["cluster"].value_counts().max()) if n_clusters else 0.0,
                float(adata.n_obs),
            ),
            "silhouette_pca": _silhouette_from_pca(adata),
        },
        "annotation": {
            "n_cell_types": n_cell_types,
            "largest_cell_type_fraction": _safe_ratio(
                float(adata.obs["cell_type"].astype(str).value_counts().max()) if n_cell_types else 0.0,
                float(adata.n_obs),
            ),
        },
        "spatial_domain": {
            "n_spatial_domains": n_domains,
            "largest_spatial_domain_fraction": _safe_ratio(
                float(adata.obs["spatial_domain"].astype(str).value_counts().max()) if n_domains else 0.0,
                float(adata.n_obs),
            ),
            "domain_cluster_ari": domain_cluster_ari,
        },
        "subcellular_spatial_domain": {
            "n_cells_with_multiple_domains": int(adata.obs["n_subcellular_domains"].gt(1).sum())
            if "n_subcellular_domains" in adata.obs
            else 0,
            "fraction_multi_domain": float(adata.obs["n_subcellular_domains"].gt(1).mean())
            if "n_subcellular_domains" in adata.obs
            else 0.0,
            "mean_domains_per_cell": float(adata.obs["n_subcellular_domains"].mean())
            if "n_subcellular_domains" in adata.obs
            else 1.0,
            "n_transcripts_in_multi_domain_cells": int(
                segmented_df[
                    segmented_df["cell"].isin(adata.obs_names[adata.obs["n_subcellular_domains"].gt(1)])
                ].shape[0]
            )
            if (
                "n_subcellular_domains" in adata.obs
                and len(segmented_df)
                and "subcellular_domain" in segmented_df.columns
            )
            else 0,
        }
        if (adata.n_obs > 0 and "n_subcellular_domains" in adata.obs)
        else {
            "n_cells_with_multiple_domains": 0,
            "fraction_multi_domain": 0.0,
            "mean_domains_per_cell": 1.0,
            "n_transcripts_in_multi_domain_cells": 0,
        },
        "spatial": _spatial_graph_metrics(adata),
    }
    return evaluation
