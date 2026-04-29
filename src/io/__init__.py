# ─────────────────────────────────────────────────────────────────────
# SubCellSpace I/O module
# Platform-specific data loaders for spatial transcriptomics data.
# ─────────────────────────────────────────────────────────────────────

from .base import BaseDataLoader, DataLoadError, DataValidationError
from .cosmx import (
    CosMxDataLoader,
    build_cell_level_adata,
    load_cosmx_transcripts,
    summarize_cosmx_transcripts,
)
from .merfish import MERFISHDataLoader
from .stereoseq import StereoSeqDataLoader
from .xenium import XeniumDataLoader

__all__ = [
    # Base abstractions
    "BaseDataLoader",
    "DataLoadError",
    "DataValidationError",
    # CosMx
    "CosMxDataLoader",
    "load_cosmx_transcripts",
    "summarize_cosmx_transcripts",
    "build_cell_level_adata",
    # Xenium
    "XeniumDataLoader",
    # MERFISH
    "MERFISHDataLoader",
    # Stereo-seq
    "StereoSeqDataLoader",
]

# ── Loader registry: platform name → loader class ─────────────────────
PLATFORM_LOADERS: dict[str, type[BaseDataLoader]] = {
    "cosmx": CosMxDataLoader,
    "xenium": XeniumDataLoader,
    "merfish": MERFISHDataLoader,
    "stereoseq": StereoSeqDataLoader,
}


def get_loader(platform: str) -> BaseDataLoader:
    """Return a singleton loader instance for the given *platform*.

    Parameters
    ----------
    platform : str
        One of ``"cosmx"``, ``"xenium"``, ``"merfish"``, ``"stereoseq"``.

    Returns
    -------
    BaseDataLoader
        An instance of the corresponding platform data loader.
    """
    cls = PLATFORM_LOADERS.get(platform)
    if cls is None:
        raise DataLoadError(
            f"Unknown platform '{platform}'. Available: {sorted(PLATFORM_LOADERS)}",
            platform=platform,
        )
    return cls()


def get_available_platforms() -> list[str]:
    """Return sorted list of supported platform names."""
    return sorted(PLATFORM_LOADERS)
