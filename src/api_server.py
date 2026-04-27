from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .benchmark import run_cosmx_backend_benchmark
from .pipeline import run_cosmx_minimal
from .steps.annotation import AVAILABLE_ANNOTATION_BACKENDS
from .steps.analysis import AVAILABLE_CLUSTERING_BACKENDS
from .steps.denoise import AVAILABLE_DENOISE_BACKENDS
from .steps.segmentation import AVAILABLE_SEGMENTATION_BACKENDS
from .steps.spatial_domain import AVAILABLE_SPATIAL_DOMAIN_BACKENDS

DEFAULT_INPUT_CSV = Path("data/test/Mouse_brain_CosMX_1000cells.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/api_runs")
DEFAULT_REPORT_RUN = "cosmx_try_again_round"
DEFAULT_BENCHMARK_RUN = "cosmx_benchmark_round"

app = FastAPI(title="SubCellSpace API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CosmxRunRequest(BaseModel):
    input_csv: str = Field(default=str(DEFAULT_INPUT_CSV))
    output_dir: str | None = None
    min_transcripts: int = 10
    min_genes: int = 10
    denoise_backend: str = "intracellular"
    segmentation_backend: str = "provided_cells"
    clustering_backend: str = "leiden"
    leiden_resolution: float = 1.0
    annotation_backend: str = "rank_marker"
    spatial_domain_backend: str = "spatial_leiden"
    spatial_domain_resolution: float = 1.0
    n_spatial_domains: int | None = None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_backend(name: str, value: str, allowed: list[str]) -> None:
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported {name}: {value}. Allowed: {allowed}")


def _resolve_output_dir(request: CosmxRunRequest) -> Path:
    if request.output_dir:
        return Path(request.output_dir)

    token = hashlib.sha1(
        "|".join(
            [
                request.input_csv,
                request.denoise_backend,
                request.segmentation_backend,
                request.clustering_backend,
                request.annotation_backend,
                request.spatial_domain_backend,
                str(request.min_transcripts),
                str(request.min_genes),
                str(request.leiden_resolution),
                str(request.spatial_domain_resolution),
                str(request.n_spatial_domains),
            ]
        ).encode("utf-8")
    ).hexdigest()[:12]
    return DEFAULT_OUTPUT_DIR / token


def _run_cosmx(request: CosmxRunRequest) -> dict[str, Any]:
    _validate_backend("denoise_backend", request.denoise_backend, AVAILABLE_DENOISE_BACKENDS)
    _validate_backend("segmentation_backend", request.segmentation_backend, AVAILABLE_SEGMENTATION_BACKENDS)
    _validate_backend("clustering_backend", request.clustering_backend, AVAILABLE_CLUSTERING_BACKENDS)
    _validate_backend("annotation_backend", request.annotation_backend, AVAILABLE_ANNOTATION_BACKENDS)
    _validate_backend("spatial_domain_backend", request.spatial_domain_backend, AVAILABLE_SPATIAL_DOMAIN_BACKENDS)

    result = run_cosmx_minimal(
        input_csv=request.input_csv,
        output_dir=_resolve_output_dir(request),
        min_transcripts=request.min_transcripts,
        min_genes=request.min_genes,
        denoise_backend=request.denoise_backend,
        segmentation_backend=request.segmentation_backend,
        clustering_backend=request.clustering_backend,
        leiden_resolution=request.leiden_resolution,
        annotation_backend=request.annotation_backend,
        spatial_domain_backend=request.spatial_domain_backend,
        spatial_domain_resolution=request.spatial_domain_resolution,
        n_spatial_domains=request.n_spatial_domains,
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    report["api"] = {
        "input_csv": request.input_csv,
        "output_dir": str(result.adata_path.parent),
        "parameters": request.model_dump(),
    }
    return report


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta/backends")
def backends() -> dict[str, list[str]]:
    return {
        "denoise": AVAILABLE_DENOISE_BACKENDS,
        "segmentation": AVAILABLE_SEGMENTATION_BACKENDS,
        "clustering": AVAILABLE_CLUSTERING_BACKENDS,
        "annotation": AVAILABLE_ANNOTATION_BACKENDS,
        "spatial_domain": AVAILABLE_SPATIAL_DOMAIN_BACKENDS,
    }


@app.get("/api/reports/{run_name}")
def get_report(run_name: str) -> dict[str, Any]:
    report_path = Path("outputs") / run_name / "cosmx_minimal_report.json"
    return _load_json(report_path)


@app.get("/api/benchmarks/{run_name}")
def get_benchmark(run_name: str) -> dict[str, Any]:
    benchmark_path = Path("outputs") / run_name / "benchmark_summary.json"
    benchmark = _load_json(benchmark_path)
    summary_csv = Path("outputs") / run_name / "benchmark_summary.csv"
    return {"summary": benchmark, "summary_csv": str(summary_csv) if summary_csv.exists() else None}


@app.get("/api/cosmx/report")
def cosmx_report(
    input_csv: str = Query(default=str(DEFAULT_INPUT_CSV)),
    output_dir: str | None = Query(default=None),
    min_transcripts: int = Query(default=10, ge=0),
    min_genes: int = Query(default=10, ge=0),
    denoise_backend: str = Query(default="intracellular"),
    segmentation_backend: str = Query(default="provided_cells"),
    clustering_backend: str = Query(default="leiden"),
    leiden_resolution: float = Query(default=1.0, gt=0),
    annotation_backend: str = Query(default="rank_marker"),
    spatial_domain_backend: str = Query(default="spatial_leiden"),
    spatial_domain_resolution: float = Query(default=1.0, gt=0),
    n_spatial_domains: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    request = CosmxRunRequest(
        input_csv=input_csv,
        output_dir=output_dir,
        min_transcripts=min_transcripts,
        min_genes=min_genes,
        denoise_backend=denoise_backend,
        segmentation_backend=segmentation_backend,
        clustering_backend=clustering_backend,
        leiden_resolution=leiden_resolution,
        annotation_backend=annotation_backend,
        spatial_domain_backend=spatial_domain_backend,
        spatial_domain_resolution=spatial_domain_resolution,
        n_spatial_domains=n_spatial_domains,
    )
    return _run_cosmx(request)


@app.post("/api/cosmx/run")
def cosmx_run(request: CosmxRunRequest = Body(default_factory=CosmxRunRequest)) -> dict[str, Any]:
    return _run_cosmx(request)


@app.post("/api/benchmarks/cosmx/run")
def cosmx_benchmark(
    input_csv: str = Body(default=str(DEFAULT_INPUT_CSV)),
    output_dir: str = Body(default="outputs/cosmx_benchmark"),
    min_transcripts: int = Body(default=10),
    min_genes: int = Body(default=10),
    leiden_resolution: float = Body(default=1.0),
    spatial_domain_resolution: float = Body(default=1.0),
    n_spatial_domains: int | None = Body(default=None),
) -> dict[str, Any]:
    return run_cosmx_backend_benchmark(
        input_csv=input_csv,
        output_dir=output_dir,
        min_transcripts=min_transcripts,
        min_genes=min_genes,
        leiden_resolution=leiden_resolution,
        spatial_domain_resolution=spatial_domain_resolution,
        n_spatial_domains=n_spatial_domains,
    )


def main() -> None:
    import uvicorn

    uvicorn.run("src.api_server:app", host="0.0.0.0", port=8000, reload=False)
