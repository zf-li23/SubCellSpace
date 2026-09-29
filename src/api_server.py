"""Minimal FastAPI server used by the frontend in development.

Only serves read-only lookups over the GEO registries (``data/*_geo.csv``).
The published site is static; this server exists for local browsing.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

REPO_ROOT = Path(__file__).resolve().parent.parent
GEO_CSV_DIR = REPO_ROOT / "data"
GEO_CSV_FILES = {"cosmx": "cosmx_geo.csv", "xenium": "xenium_geo.csv", "merfish": "merfish_geo.csv"}

# CosMx registry names its sample column ``sample_name``; Xenium / MERFISH use ``GSM``.
SAMPLE_COLUMNS = ("GSM", "sample_name")
NUMERIC_COLUMNS = {
    "n_transcripts", "n_cells", "n_genes", "n_fovs",
    "gene_panel_size", "median_transcripts", "median_genes", "data_size",
}

_DEFAULT_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174"


def _parse_allowed_origins() -> list[str]:
    raw = os.environ.get("SUBCELLSPACE_ALLOWED_ORIGINS", _DEFAULT_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="SubCellSpace API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def sample_id(row: dict[str, Any]) -> str:
    """Return the GSM accession (or GSM range) of a registry row, whatever its column name."""
    for col in SAMPLE_COLUMNS:
        value = (row.get(col) or "").strip()
        if value:
            return value
    return ""


def _clean_row(row: dict[str, Any], platform: str) -> dict[str, Any]:
    cleaned: dict[str, Any] = {"platform": platform}
    for key, value in row.items():
        if value is None:
            cleaned[key] = None
            continue
        value = value.strip()
        if key in NUMERIC_COLUMNS and value:
            try:
                cleaned[key] = int(float(value))
            except ValueError:
                cleaned[key] = value
        else:
            cleaned[key] = value
    cleaned["GSM"] = sample_id(row)
    return cleaned


def search_registries(query: str, csv_dir: Path = GEO_CSV_DIR) -> list[dict[str, Any]]:
    """Match rows by exact GSE, exact GSM (or GSM range), or a keyword in the dataset name."""
    q = query.strip().upper()
    results: list[dict[str, Any]] = []
    for platform, fname in GEO_CSV_FILES.items():
        fpath = csv_dir / fname
        if not fpath.exists():
            continue
        with open(fpath, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                gse = (row.get("GSE") or "").strip().upper()
                gsm = sample_id(row).upper()
                name = (row.get("name") or "").strip().lower()
                if q in (gse, gsm) or q.lower() in name:
                    results.append(_clean_row(row, platform))
    return results


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "SubCellSpace API", "docs": "/docs", "health": "/api/health"}


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dataset")
def geo_dataset_lookup(gse: str = Query(..., description="GSE ID, GSM ID, or dataset name keyword")) -> Any:
    """Search the GEO registries; returns one row or a list of rows."""
    results = search_registries(gse)
    if not results:
        raise HTTPException(status_code=404, detail=f"Dataset '{gse}' not found in any GEO registry")
    return results[0] if len(results) == 1 else results


def main() -> None:
    import uvicorn

    uvicorn.run(
        "src.api_server:app",
        host=os.environ.get("SUBCELLSPACE_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("SUBCELLSPACE_API_PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
