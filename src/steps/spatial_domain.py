from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import scanpy as sc
import squidpy as sq
from sklearn.cluster import KMeans

from ..models import StepResult
from ..registry import register_backend, register_runner

if TYPE_CHECKING:
    from ..pipeline_engine import ExecutionContext

logger = logging.getLogger(__name__)

# ── Backend availability flags ─────────────────────────────────────────────

_GRAPHST_AVAILABLE: bool = False
_STAGATE_AVAILABLE: bool = False
_SPAGCN_AVAILABLE: bool = False

try:
    import GraphST  # noqa: F401
    _GRAPHST_AVAILABLE = True
except ImportError:
    pass

try:
    import STAGATE  # noqa: F401
    _STAGATE_AVAILABLE = True
except ImportError:
    pass

try:
    import SpaGCN  # noqa: F401
    _SPAGCN_AVAILABLE = True
except ImportError:
    pass


# ── Backend implementations ────────────────────────────────────────────────


def _ensure_spatial_neighbors(adata: sc.AnnData) -> None:
    """Compute spatial neighbors if not already present."""
    if "spatial_connectivities" not in adata.obsp:
        sq.gr.spatial_neighbors(adata, spatial_key="spatial", coord_type="generic")


def _domain_spatial_leiden(
    adata: sc.AnnData,
    domain_resolution: float,
    n_spatial_domains: int | None = None,  # noqa: ARG001
) -> str:
    """Spatial Leiden clustering on spatial neighbor graph.

    Tries three strategies in order:
    1. Leiden with igraph flavor
    2. Leiden with default flavor
    3. KMeans fallback on spatial coordinates

    This ensures robustness even when the spatial connectivities matrix
    is ill-conditioned or igraph is unavailable.
    """
    _ensure_spatial_neighbors(adata)

    try:
        sc.tl.leiden(
            adata,
            adjacency=adata.obsp["spatial_connectivities"],
            resolution=domain_resolution,
            key_added="spatial_domain",
            flavor="igraph",
            directed=False,
            n_iterations=2,
        )
        return "spatial_leiden_igraph"
    except Exception:
        pass

    try:
        sc.tl.leiden(
            adata,
            adjacency=adata.obsp["spatial_connectivities"],
            resolution=domain_resolution,
            key_added="spatial_domain",
        )
        return "spatial_leiden_default"
    except Exception:
        pass

    # Ultimate fallback: use KMeans-based spatial domain assignment
    n_cells = adata.n_obs
    n_domains = max(2, min(8, int(np.sqrt(n_cells) // 2 + 2)))
    coords = adata.obsm.get("spatial")
    if coords is None:
        coords = np.zeros((n_cells, 2))
    labels = KMeans(n_clusters=n_domains, n_init="auto", random_state=0).fit_predict(coords)
    adata.obs["spatial_domain"] = labels.astype(str)
    return "spatial_leiden_fallback_kmeans"


def _domain_spatial_kmeans(
    adata: sc.AnnData,
    _domain_resolution: float = 1.0,
    n_spatial_domains: int | None = None,  # noqa: ARG001
) -> str:
    """Spatial domain identification via KMeans on spatial coordinates."""
    if "spatial" not in adata.obsm:
        raise ValueError("`spatial` not found in adata.obsm.")

    coords = adata.obsm["spatial"]
    if n_spatial_domains is None:
        n_spatial_domains = max(2, min(12, int(np.sqrt(max(adata.n_obs, 2)) // 2 + 2)))

    n_spatial_domains = max(2, min(int(n_spatial_domains), adata.n_obs))
    labels = KMeans(n_clusters=n_spatial_domains, n_init="auto", random_state=0).fit_predict(coords)
    adata.obs["spatial_domain"] = labels.astype(str)
    return "spatial_kmeans"


def _domain_graphst(
    adata: sc.AnnData,
    domain_resolution: float,
    n_spatial_domains: int | None = None,  # noqa: ARG001
) -> str:
    """GraphST: Graph-guided Spatial Transformer for spatial domain identification.

    Uses graph attention to learn cell representations, then clusters
    the embeddings with Leiden to identify spatial domains.

    NOTE: GraphST versions may store embeddings under different keys in
    ``adata.obsm`` (e.g. ``"emb"``, ``"GraphST"``, or custom).  This
    implementation probes for the embedding and falls back gracefully.
    """
    try:
        import GraphST
        _GraphST = GraphST.GraphST
    except ImportError as exc:
        raise ImportError(
            "GraphST backend requires 'GraphST' to be installed. "
            "Run: pip install -e tools/GraphST/"
        ) from exc

    # GraphST requires preprocessed adata (normalized, log1p)
    adata_tmp = adata.copy()
    sc.pp.normalize_total(adata_tmp, target_sum=1e4)
    sc.pp.log1p(adata_tmp)

    # Preprocess: find highly variable genes
    sc.pp.highly_variable_genes(adata_tmp, flavor="seurat_v3", n_top_genes=min(2000, adata_tmp.n_vars))
    if "highly_variable" not in adata_tmp.var or not adata_tmp.var["highly_variable"].any():
        logger.warning("GraphST: HVG selection produced no genes, using all genes.")
    else:
        adata_tmp = adata_tmp[:, adata_tmp.var["highly_variable"]].copy()

    # Run GraphST pre-processing pipeline
    try:
        GraphST.preprocess(adata_tmp)
    except Exception as exc:
        logger.warning("GraphST.preprocess failed: %s. Falling back to spatial_leiden.", exc)
        return _domain_spatial_leiden(adata, domain_resolution, n_spatial_domains)

    GraphST.get_feature(adata_tmp)

    n_clusters = n_spatial_domains if n_spatial_domains is not None else max(
        2, int(np.sqrt(adata.n_obs) // 2 + 2)
    )

    # Train the GraphST model to get embeddings
    import torch

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda:0" if use_cuda else "cpu")
    try:
        model = _GraphST(
            adata_tmp,
            device=device,
            learning_rate=0.001,
            epochs=200,
            dim_output=64,
            random_seed=42,
        )
        adata_tmp = model.train()
    except Exception as exc:
        logger.warning("GraphST model training failed: %s. Falling back to spatial_leiden.", exc)
        return _domain_spatial_leiden(adata, domain_resolution, n_spatial_domains)

    # Probe for the embedding key
    logger.info("GraphST: adata_tmp.obsm keys = %s", list(adata_tmp.obsm.keys()))
    logger.info("GraphST: adata_tmp.obs columns = %s", list(adata_tmp.obs.columns))

    known_emb_keys = {"emb", "GraphST", "embedding", "latent", "graphst_emb"}
    emb_key: str | None = None
    for k in known_emb_keys:
        if k in adata_tmp.obsm:
            emb_key = k
            break
    if emb_key is None and adata_tmp.obsm:
        emb_key = list(adata_tmp.obsm.keys())[0]
        logger.info("GraphST: No known embedding key found, using '%s' as fallback.", emb_key)

    if emb_key is not None:
        GraphST.clustering(
            adata_tmp,
            n_clusters=n_clusters,
            radius=50,
            key=emb_key,
            method="leiden",
            start=0.1,
            end=3.0,
            increment=0.01,
            refinement=False,
        )

    # Determine the column name where GraphST.clustering stored labels
    known_label_cols = {"domain", "clusters", "label", "spatial_domain"}
    label_col: str | None = None
    for c in known_label_cols:
        if c in adata_tmp.obs:
            label_col = c
            break
    if label_col is None:
        logger.warning("GraphST: No cluster label column found. Falling back to KMeans on embeddings.")
        if emb_key is not None and emb_key in adata_tmp.obsm:
            embed = adata_tmp.obsm[emb_key]
            from sklearn.cluster import KMeans as _KMeans

            labels = _KMeans(n_clusters=n_clusters, n_init="auto", random_state=0).fit_predict(embed)
            adata_tmp.obs["spatial_domain_fallback"] = labels.astype(str)
            label_col = "spatial_domain_fallback"
        else:
            logger.warning("GraphST: No embeddings available either. Falling back to spatial_leiden.")
            return _domain_spatial_leiden(adata, domain_resolution, n_spatial_domains)

    # Transfer domain labels — guard against length mismatch
    domain_labels = adata_tmp.obs[label_col].astype(str).to_numpy()
    if len(domain_labels) != adata.n_obs:
        logger.warning(
            "GraphST: label length mismatch (%d vs %d). Falling back to spatial_leiden.",
            len(domain_labels),
            adata.n_obs,
        )
        return _domain_spatial_leiden(adata, domain_resolution, n_spatial_domains)
    adata.obs["spatial_domain"] = domain_labels
    return "graphst"


def _domain_stagate(
    adata: sc.AnnData,
    _domain_resolution: float = 1.0,
    n_spatial_domains: int | None = None,  # noqa: ARG001
) -> str:
    """STAGATE: Spatially-Aware Graph Attention Autoencoder.

    Learns latent representations using a graph attention autoencoder
    that incorporates spatial information. Then clusters embeddings
    with KMeans to identify spatial domains.

    All failures (import, preprocessing, training, shape mismatches)
    degrade gracefully to spatial_leiden fallback.
    """
    try:
        import STAGATE
    except ImportError as exc:
        raise ImportError(
            "STAGATE backend requires 'STAGATE' to be installed. "
            "Run: pip install -e tools/STAGATE/"
        ) from exc

    # Preprocess
    adata_tmp = adata.copy()
    sc.pp.normalize_total(adata_tmp, target_sum=1e4)
    sc.pp.log1p(adata_tmp)
    sc.pp.highly_variable_genes(adata_tmp, flavor="seurat_v3", n_top_genes=min(2000, adata_tmp.n_vars))
    if "highly_variable" in adata_tmp.var and adata_tmp.var["highly_variable"].any():
        adata_tmp = adata_tmp[:, adata_tmp.var.highly_variable].copy()
    else:
        logger.warning("STAGATE: HVG selection produced no genes, using all genes.")
    sc.pp.scale(adata_tmp, max_value=10)

    # Calculate spatial network from coordinates
    coords = adata.obsm["spatial"]
    adata_tmp.obsm["spatial"] = coords.copy()
    STAGATE.Cal_Spatial_Net(adata_tmp, rad_cutoff=None, k_cutoff=None, model="Radius", verbose=False)

    # Train STAGATE to get embeddings
    try:
        adata_tmp, _ = STAGATE.train_STAGATE(
            adata_tmp,
            hidden_dims=[512, 30],
            alpha=0,
            n_epochs=500,
            lr=0.0001,
            key_added="STAGATE",
            verbose=False,
        )
    except Exception as exc:
        logger.warning("STAGATE training failed: %s. Falling back to spatial_leiden.", exc)
        return _domain_spatial_leiden(adata, _domain_resolution, n_spatial_domains)

    # Debug: probe STAGATE output
    logger.info("STAGATE: adata_tmp.obsm keys = %s", list(adata_tmp.obsm.keys()))
    logger.info("STAGATE: adata_tmp.n_obs = %d, adata.n_obs = %d", adata_tmp.n_obs, adata.n_obs)

    # Guard: empty return
    if adata_tmp.n_obs == 0:
        logger.warning("STAGATE returned empty adata. Falling back to spatial_leiden.")
        return _domain_spatial_leiden(adata, _domain_resolution, n_spatial_domains)

    # Probe for the correct embedding key
    known_emb_keys = {"STAGATE", "embedding", "latent", "stagate_emb"}
    emb_key: str | None = None
    for k in known_emb_keys:
        if k in adata_tmp.obsm:
            emb_key = k
            break
    if emb_key is None and adata_tmp.obsm:
        emb_key = list(adata_tmp.obsm.keys())[0]
        logger.info("STAGATE: No known embedding key found, using '%s' as fallback.", emb_key)

    if emb_key is None or emb_key not in adata_tmp.obsm:
        logger.warning("STAGATE: No embeddings found. Falling back to spatial_leiden.")
        return _domain_spatial_leiden(adata, _domain_resolution, n_spatial_domains)

    embed = adata_tmp.obsm[emb_key]

    # Guard: embedding shape mismatch (e.g. STAGATE filtered cells)
    if embed.shape[0] != adata.n_obs or embed.shape[0] != adata_tmp.n_obs:
        logger.warning(
            "STAGATE: embedding shape mismatch — embed=%s, adata_tmp.n_obs=%d, adata.n_obs=%d. "
            "Falling back to spatial_leiden.",
            embed.shape,
            adata_tmp.n_obs,
            adata.n_obs,
        )
        return _domain_spatial_leiden(adata, _domain_resolution, n_spatial_domains)

    n_clusters = n_spatial_domains if n_spatial_domains is not None else max(
        2, int(np.sqrt(adata.n_obs) // 2 + 2)
    )
    n_clusters = max(2, min(int(n_clusters), adata_tmp.n_obs))

    labels = KMeans(n_clusters=n_clusters, n_init="auto", random_state=0).fit_predict(embed)

    # Final guard: label count mismatch
    if len(labels) != adata.n_obs:
        logger.warning(
            "STAGATE: label count mismatch (%d vs %d). Falling back to spatial_leiden.",
            len(labels),
            adata.n_obs,
        )
        return _domain_spatial_leiden(adata, _domain_resolution, n_spatial_domains)

    adata.obs["spatial_domain"] = labels.astype(str)
    return "stagate"


def _domain_spagcn(
    adata: sc.AnnData,
    _domain_resolution: float = 1.0,
    n_spatial_domains: int | None = None,
) -> str:
    """SpaGCN: Spatial Graph Convolutional Network.

    Constructs a spatial adjacency graph and uses a GCN to assign
    spatial domains. For CosMx transcript-only data (no image),
    it runs with histology=False.
    """
    try:
        import SpaGCN
    except ImportError as exc:
        raise ImportError(
            "SpaGCN backend requires 'SpaGCN' to be installed. "
            "Run: pip install -e tools/SpaGCN/"
        ) from exc

    coords = adata.obsm["spatial"]
    x_array = coords[:, 0].tolist()
    y_array = coords[:, 1].tolist()

    n_clusters = n_spatial_domains if n_spatial_domains is not None else max(
        2, int(np.sqrt(adata.n_obs) // 2 + 2)
    )
    n_clusters = max(2, min(int(n_clusters), adata.n_obs))

    # Preprocess adata
    adata_tmp = adata.copy()
    sc.pp.normalize_total(adata_tmp, target_sum=1e4)
    sc.pp.log1p(adata_tmp)

    # Run SpaGCN's easy-mode detection (no image)
    y_pred = SpaGCN.detect_spatial_domains_ez_mode(
        adata_tmp,
        img=None,
        x_array=x_array,
        y_array=y_array,
        x_pixel=x_array,
        y_pixel=y_array,
        n_clusters=n_clusters,
        histology=False,
        s=1,
        b=49,
        p=0.5,
        r_seed=100,
        t_seed=100,
        n_seed=100,
    )

    adata.obs["spatial_domain"] = y_pred.astype(str)
    return "spagcn"


# Register backends
register_backend("spatial_domain", "spatial_leiden")(_domain_spatial_leiden)
register_backend("spatial_domain", "spatial_kmeans")(_domain_spatial_kmeans)
register_backend("spatial_domain", "graphst")(_domain_graphst)
register_backend("spatial_domain", "stagate")(_domain_stagate)
register_backend("spatial_domain", "spagcn")(_domain_spagcn)

# Dispatch table
_SPATIAL_DOMAIN_FUNCS = {
    "spatial_leiden": _domain_spatial_leiden,
    "spatial_kmeans": _domain_spatial_kmeans,
    "graphst": _domain_graphst,
    "stagate": _domain_stagate,
    "spagcn": _domain_spagcn,
}


# ── Main entry point ──────────────────────────────────────────────────────


def run_spatial_domain_identification(
    adata: sc.AnnData,
    backend: str,
    domain_resolution: float,
    n_spatial_domains: int | None,
) -> StepResult:
    if backend not in _SPATIAL_DOMAIN_FUNCS:
        raise ValueError(
            f"Unknown spatial domain backend: {backend}. Available: {list(_SPATIAL_DOMAIN_FUNCS)}"
        )

    backend_used = _SPATIAL_DOMAIN_FUNCS[backend](adata, domain_resolution, n_spatial_domains)

    distribution = adata.obs["spatial_domain"].astype(str).value_counts().to_dict()
    summary = {
        "spatial_domain_backend_requested": backend,
        "spatial_domain_backend_used": backend_used,
        "domain_resolution": float(domain_resolution),
        "n_spatial_domains_requested": int(n_spatial_domains) if n_spatial_domains is not None else None,
        "n_spatial_domains": int(adata.obs["spatial_domain"].nunique()),
        "spatial_domain_distribution": {str(k): int(v) for k, v in distribution.items()},
    }
    return StepResult(output=adata, summary=summary, backend_used=backend_used)


# ── Step runner (registered for pipeline engine) ──────────────────────────


@register_runner("spatial_domain")
def _run_spatial_domain(
    ctx: ExecutionContext,
    backend: str,
    params: dict[str, Any],
) -> StepResult:
    if ctx.adata is None:
        raise ValueError("No AnnData before spatial_domain step")
    resolution = params.get("domain_resolution", 1.0)
    n_domains = params.get("n_spatial_domains")
    result = run_spatial_domain_identification(ctx.adata, backend, resolution, n_domains)
    ctx.adata = result.output
    return result
