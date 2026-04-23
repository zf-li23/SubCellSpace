from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anndata as ad
from spatialdata import SpatialData


@dataclass(slots=True)
class DatasetSummary:
    source_path: Path
    n_transcripts: int
    n_cells: int
    n_genes: int
    n_fovs: int
    extra: dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        lines = [
            f"source_path: {self.source_path}",
            f"n_transcripts: {self.n_transcripts}",
            f"n_cells: {self.n_cells}",
            f"n_genes: {self.n_genes}",
            f"n_fovs: {self.n_fovs}",
        ]
        for key, value in self.extra.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)


@dataclass(slots=True)
class PipelineResult:
    adata: ad.AnnData
    summary: DatasetSummary
    sdata: SpatialData
    adata_path: Path
    report_path: Path
