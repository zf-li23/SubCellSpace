# ─────────────────────────────────────────────────────────────────────
# SubCellSpace I/O module
# Platform-specific data ingestors for spatial transcriptomics data.
#
# Usage::
#
#     from subcellspace.io import ingest
#     sdata = ingest("cosmx", "data/test/Mouse_brain_CosMX_1000cells.csv")
#
# Each platform ingestor produces a standardised ``SpatialData`` object.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from pathlib import Path

from .base import (
    BaseIngestor,
    DataLoadError,
    DataValidationError,
    get_available_platforms,
    get_ingestor,
    register_ingestor,
)

# Import platform modules to trigger @register_ingestor decorators
from . import cosmx   # noqa: F401
from . import merfish  # noqa: F401
from . import stereoseq  # noqa: F401
from . import xenium   # noqa: F401


def ingest(platform: str, input_path: str | Path) -> Any:
    """Run data ingestion for *platform* and return a SpatialData object.

    Parameters
    ----------
    platform : str
        One of ``"cosmx"``, ``"xenium"``, ``"merfish"``, ``"stereoseq"``.
    input_path : str or Path
        Path to the input data file or directory.

    Returns
    -------
    SpatialData
        Standardised spatial data object.
    """
    return get_ingestor(platform).ingest(Path(input_path))


__all__ = [
    "BaseIngestor",
    "DataLoadError",
    "DataValidationError",
    "get_ingestor",
    "get_available_platforms",
    "register_ingestor",
    "ingest",
]
