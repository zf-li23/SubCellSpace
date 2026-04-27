from __future__ import annotations

import scanpy as sc

AVAILABLE_ANNOTATION_BACKENDS = ("cluster_label", "rank_marker")


def _cluster_label_annotation(adata: sc.AnnData) -> str:
    if "cluster" not in adata.obs:
        raise ValueError("`cluster` not found in adata.obs. Run clustering before annotation.")
    adata.obs["cell_type"] = adata.obs["cluster"].astype(str).map(lambda x: f"Cluster_{x}")
    return "cluster_label"


def _rank_marker_annotation(adata: sc.AnnData) -> str:
    if "cluster" not in adata.obs:
        raise ValueError("`cluster` not found in adata.obs. Run clustering before annotation.")

    rank_kwargs = {
        "groupby": "cluster",
        "method": "t-test",
        "use_raw": False,
    }
    if "lognorm" in adata.layers:
        rank_kwargs["layer"] = "lognorm"

    sc.tl.rank_genes_groups(adata, **rank_kwargs)
    markers = adata.uns["rank_genes_groups"]["names"]

    cluster_to_label: dict[str, str] = {}
    for cluster in adata.obs["cluster"].astype(str).unique():
        top_gene = str(markers[cluster][0]) if cluster in markers.dtype.names else "UnknownMarker"
        cluster_to_label[cluster] = f"CT_{top_gene}"

    adata.obs["cell_type"] = adata.obs["cluster"].astype(str).map(cluster_to_label).fillna("CT_Unknown")
    return "rank_marker"


def run_cell_type_annotation(
    adata: sc.AnnData,
    backend: str,
) -> tuple[sc.AnnData, dict[str, int | str | dict[str, int]]]:
    if backend not in AVAILABLE_ANNOTATION_BACKENDS:
        raise ValueError(f"Unknown annotation backend: {backend}")

    if backend == "cluster_label":
        backend_used = _cluster_label_annotation(adata)
    else:
        backend_used = _rank_marker_annotation(adata)

    distribution = adata.obs["cell_type"].astype(str).value_counts().to_dict()
    summary = {
        "annotation_backend_requested": backend,
        "annotation_backend_used": backend_used,
        "n_cell_types": int(adata.obs["cell_type"].nunique()),
        "cell_type_distribution": {str(k): int(v) for k, v in distribution.items()},
    }
    return adata, summary
