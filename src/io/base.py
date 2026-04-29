# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Multi-Platform Data Loading Abstraction
#
# Defines the abstract ``BaseDataLoader`` interface that all spatial
# transcriptomics platform loaders must implement.  New platforms
# (Xenium, MERFISH, Stereo-seq, etc.) only need to subclass this and
# implement the three abstract methods.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import anndata as ad
import pandas as pd
from spatialdata import SpatialData

from ..models import DatasetSummary


class DataLoadError(Exception):
    """Raised when a data loader fails to read or validate input data."""

    def __init__(self, message: str, platform: str = "unknown", path: str | Path | None = None) -> None:
        self.platform = platform
        self.path = str(path) if path else None
        super().__init__(message)


class DataValidationError(DataLoadError):
    """Raised when loaded data fails structural/content validation."""

    pass


class BaseDataLoader(ABC):
    """Abstract base class for all spatial transcriptomics data loaders.

    Each subclass must implement::

        load(path)           → pd.DataFrame   # raw transcript-level data
        summarize(df, path)  → DatasetSummary  # summary statistics
        build_adata(df)      → AnnData         # cell-level expression matrix
        build_spatialdata(adata) → SpatialData # spatial data container

    Subclasses also declare:
    - ``platform`` (str): short platform name, e.g. ``"cosmx"``
    - ``required_columns`` (set[str]): columns that must exist in the CSV
    """

    # ── Subclass contract ────────────────────────────────────────────

    platform: str = "unknown"
    required_columns: set[str] = set()

    @abstractmethod
    def load(self, path: str | Path) -> pd.DataFrame:
        """Load raw transcript-level data from *path*.

        Must validate that the file exists and that all
        ``required_columns`` are present.
        """
        ...

    @abstractmethod
    def summarize(self, df: pd.DataFrame, source_path: str | Path) -> DatasetSummary:
        """Compute dataset-level summary statistics from the loaded DataFrame."""
        ...

    @abstractmethod
    def build_adata(self, df: pd.DataFrame) -> ad.AnnData:
        """Build a cell-level AnnData from transcript-level data.

        Typically involves cross-tabulation of ``cell`` × ``target``
        columns and aggregating cell-level covariates into ``obs``.
        """
        ...

    @abstractmethod
    def build_spatialdata(self, adata: ad.AnnData) -> SpatialData:
        """Build a SpatialData container from cell-level AnnData."""
        ...

    # ── Shared helpers ───────────────────────────────────────────────

    def _validate_columns(self, df: pd.DataFrame, path: str | Path) -> None:
        """Check that all ``required_columns`` are present in *df*."""
        missing = self.required_columns - set(df.columns)
        if missing:
            raise DataValidationError(
                f"Missing required columns for platform '{self.platform}': {sorted(missing)}",
                platform=self.platform,
                path=path,
            )

    def _validate_file_exists(self, path: str | Path) -> Path:
        """Resolve *path* and raise ``DataLoadError`` if it doesn't exist."""
        resolved = Path(path)
        if not resolved.exists():
            raise DataLoadError(
                f"Input file does not exist: {resolved}",
                platform=self.platform,
                path=resolved,
            )
        return resolved
