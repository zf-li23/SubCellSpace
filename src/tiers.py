"""Fast data-tier assessment for many samples: file list from touch + a peek at the transcript file.

Unlike :func:`src.complete.assess_tier`, nothing is loaded in full, so this can run over the whole registry.
"""

from __future__ import annotations

import gzip
import io
from pathlib import Path

import pandas as pd

from .touch import touch

PEEK_ROWS = 200_000
_UNASSIGNED = {"UNASSIGNED", "-1", "0", "", "nan", "None"}
_CELL_COLUMNS = {"cosmx": "cell_ID", "xenium": "cell_id", "merfish": "cell_id"}
_MATRIX = ("expr_matrix", "expr_matrix_mtx", "expr_matrix_zarr")
_CELLS = ("cell_metadata", "cell_metadata_parquet", "cell_metadata_csv", "cell_metadata_zarr")
_BOUNDS = ("polygons", "cell_boundaries", "cell_boundaries_csv")


def _peek(path: Path, column: str) -> tuple[bool, bool]:
    """(column present, any assigned value) from the first rows of a transcript file."""
    name = path.name.lower()
    if ".zarr" in name:
        return False, False
    if ".parquet" in name:
        import pyarrow.parquet as pq

        if name.endswith(".gz"):
            with gzip.open(path) as f:
                src = io.BytesIO(f.read())
        else:
            src = path
        pf = pq.ParquetFile(src)
        if column not in pf.schema_arrow.names:
            return False, False
        values = pf.read_row_group(0, columns=[column]).column(0).to_pandas().head(PEEK_ROWS)
    else:
        head = pd.read_csv(path, nrows=PEEK_ROWS, sep="\t" if ".tsv" in name else ",")
        if column not in head.columns:
            return False, False
        values = head[column]
    if values.dtype == object and len(values) and isinstance(values.iloc[0], bytes):
        values = values.str.decode("utf-8")
    return True, bool((~values.astype(str).isin(_UNASSIGNED)).any())


def quick_tier(sample_dir: str | Path, platform: str | None = None) -> dict:
    report = touch(str(sample_dir), normalize=False, platform_override=platform)
    found = {f.name: Path(f.path) for f in report.files if f.found and f.path}
    tx = found.get("transcripts") or found.get("transcripts_parquet") or found.get("transcripts_detected")
    row = {
        "platform": report.platform,
        "has_transcripts": tx is not None and ".zarr" not in tx.name,
        "has_matrix": any(k in found for k in _MATRIX),
        "has_cell_table": any(k in found for k in _CELLS),
        "has_boundaries": any(k in found for k in _BOUNDS),
        "has_images": any("morphology" in p.name or ".tif" in p.name.lower() for p in Path(report.input_path).glob("*")),
        "has_cell_id": False,
        "error": "",
    }
    if row["has_transcripts"] and report.platform in _CELL_COLUMNS:
        try:
            _, row["has_cell_id"] = _peek(tx, _CELL_COLUMNS[report.platform])
        except Exception as exc:  # recorded per sample; one unreadable file must not stop a registry-wide scan
            row["error"] = f"{type(exc).__name__}: {exc}"[:200]
    if row["has_transcripts"] and (row["has_cell_id"] or row["has_boundaries"]):
        row["data_tier"] = "A"
    elif row["has_matrix"]:
        row["data_tier"] = "B" if row["has_cell_table"] or row["has_boundaries"] else "C"
    elif row["has_transcripts"]:
        row["data_tier"] = "S"
    else:
        row["data_tier"] = "D"
    return row
