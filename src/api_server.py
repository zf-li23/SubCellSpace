from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import anndata as ad
from fastapi import Body, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .benchmark import run_cosmx_backend_benchmark
from .config import settings as _settings
from .io import get_available_platforms
from .pipelines.cosmx_minimal import run_cosmx_minimal
from .registry import get_available_backends

# ── Configurable defaults (from centralized configuration system) ─────────
DEFAULT_INPUT_CSV = Path(_settings.get("input_csv", "data/test/Mouse_brain_CosMX_1000cells.csv"))
DEFAULT_OUTPUT_DIR = Path(_settings.get("output_dir", "outputs/api_runs"))
DEFAULT_REPORT_RUN = _settings.get("report_run", "default_test")
DEFAULT_BENCHMARK_RUN = _settings.get("benchmark_run", "cosmx_benchmark_round")
DEFAULT_BENCHMARK_VALIDATION_DIR = _settings.get("benchmark_validation_dir", "outputs/backend_validation")
DEFAULT_API_HOST = _settings.get("api_host", "0.0.0.0")
DEFAULT_API_PORT = int(_settings.get("api_port", "8000"))

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = (REPO_ROOT / "outputs").resolve()

# ── Cell ID sanitisation ──────────────────────────────────────────────────
_CELL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _sanitise_cell_id(cell_id: str) -> str:
    """Reject cell IDs containing characters that could enable injection."""
    if not _CELL_ID_PATTERN.match(cell_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cell_id: '{cell_id}'. Allowed: alphanumeric, '_', '.', '-'.",
        )
    return cell_id


# ── CORS ──────────────────────────────────────────────────────────────────


def _parse_allowed_origins() -> list[str]:
    raw = _settings.get("allowed_origins", "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="SubCellSpace API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────


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
    subcellular_domain_backend: str = "hdbscan"


# ── Internal helpers ──────────────────────────────────────────────────────


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_under_repo(path_like: str | Path) -> Path:
    """Resolve a path and ensure it stays within the repository root."""
    path = Path(path_like)
    if not path.is_absolute():
        path = REPO_ROOT / path
    resolved = path.resolve()
    if REPO_ROOT not in resolved.parents and resolved != REPO_ROOT:
        raise HTTPException(status_code=400, detail="Path must be under repository root")
    return resolved


def _ensure_under_outputs(path: Path) -> Path:
    """Ensure a resolved path is within the canonical outputs directory."""
    resolved = path.resolve()
    if OUTPUTS_ROOT not in resolved.parents and resolved != OUTPUTS_ROOT:
        raise HTTPException(status_code=400, detail="Path must be under outputs/")
    return resolved


def _resolve_report_path(run_name: str) -> Path:
    return _ensure_under_outputs(OUTPUTS_ROOT / run_name / "cosmx_minimal_report.json")


def _validate_backend(name: str, value: str, all_backends: list[str]) -> None:
    if value not in all_backends:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported {name}: {value}. Allowed: {all_backends}",
        )


def _resolve_output_dir(request: CosmxRunRequest) -> Path:
    if request.output_dir:
        requested = _resolve_under_repo(request.output_dir)
        return _ensure_under_outputs(requested)

    # Deterministic hash-based subdirectory when no explicit output_dir
    token = hashlib.sha1(
        "|".join(
            [
                request.input_csv,
                request.denoise_backend,
                request.segmentation_backend,
                request.clustering_backend,
                request.annotation_backend,
                request.spatial_domain_backend,
                request.subcellular_domain_backend,
                str(request.min_transcripts),
                str(request.min_genes),
                str(request.leiden_resolution),
                str(request.spatial_domain_resolution),
                str(request.n_spatial_domains),
            ]
        ).encode("utf-8")
    ).hexdigest()[:12]
    return _ensure_under_outputs((REPO_ROOT / DEFAULT_OUTPUT_DIR / token).resolve())


def _run_cosmx(request: CosmxRunRequest) -> dict[str, Any]:
    _validate_backend("denoise_backend", request.denoise_backend, get_available_backends("denoise"))
    _validate_backend("segmentation_backend", request.segmentation_backend, get_available_backends("segmentation"))
    _validate_backend("clustering_backend", request.clustering_backend, get_available_backends("analysis"))
    _validate_backend("annotation_backend", request.annotation_backend, get_available_backends("annotation"))
    _validate_backend(
        "spatial_domain_backend", request.spatial_domain_backend, get_available_backends("spatial_domain")
    )
    _validate_backend(
        "subcellular_domain_backend",
        request.subcellular_domain_backend,
        get_available_backends("subcellular_spatial_domain"),
    )

    input_csv_path = _resolve_under_repo(request.input_csv)
    if not input_csv_path.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found: {input_csv_path}")

    result = run_cosmx_minimal(
        input_csv=str(input_csv_path),
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
        subcellular_domain_backend=request.subcellular_domain_backend,
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    report["api"] = {
        "input_csv": request.input_csv,
        "output_dir": str(result.adata_path.parent),
        "parameters": request.model_dump(),
    }
    return report


# ── Endpoints ─────────────────────────────────────────────────────────────


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "SubCellSpace API", "docs": "/docs", "health": "/api/health"}


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta/backends")
def backends() -> dict[str, list[str]]:
    return {
        "denoise": get_available_backends("denoise"),
        "segmentation": get_available_backends("segmentation"),
        "clustering": get_available_backends("analysis"),
        "annotation": get_available_backends("annotation"),
        "spatial_domain": get_available_backends("spatial_domain"),
        "subcellular_spatial_domain": get_available_backends("subcellular_spatial_domain"),
    }


@app.get("/api/meta/platforms")
def platforms() -> dict[str, list[str]]:
    """Return the list of supported data platforms (CosMx, Xenium, MERFISH, Stereo-seq, …)."""
    return {"platforms": get_available_platforms()}



@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    """List available run reports under outputs/ with metadata.

    Only relative paths are returned to avoid leaking server filesystem layout.
    """
    runs: list[dict[str, Any]] = []
    if not OUTPUTS_ROOT.exists():
        return runs

    for child in sorted(OUTPUTS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        report_path = child / "cosmx_minimal_report.json"
        if not report_path.is_file():
            continue

        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        params = report.get("parameters", {})
        analysis = report.get("analysis_summary", {}) or report.get("metadata", {}) or {}

        # Build relative paths to avoid leaking absolute filesystem paths
        try:
            rel_report_path = report_path.relative_to(REPO_ROOT)
        except ValueError:
            rel_report_path = Path("outputs") / child.name / "cosmx_minimal_report.json"

        runs.append(
            {
                "run_name": child.name,
                "report_path": str(rel_report_path),
                "created_at": params.get("created_at") or params.get("timestamp"),
                "n_cells": analysis.get("n_cells") or report.get("n_cells") or 0,
                "n_genes": analysis.get("n_genes") or report.get("n_genes") or 0,
                "denoise_backend": params.get("denoise_backend"),
                "segmentation_backend": params.get("segmentation_backend"),
                "clustering_backend": params.get("clustering_backend"),
                "annotation_backend": params.get("annotation_backend"),
                "spatial_domain_backend": params.get("spatial_domain_backend"),
                "input_csv": params.get("input_csv"),
            }
        )

    return runs


@app.get("/api/reports/{run_name}")
def get_report(run_name: str) -> dict[str, Any]:
    return _load_json(_resolve_report_path(run_name))


@app.get("/api/plots/{run_name}")
def get_plots(run_name: str) -> dict[str, Any]:
    return _get_plot_payload(run_name=run_name)


@app.get("/api/plots")
def get_plots_by_report(
    report_path: str | None = Query(default=None),
    output_dir: str | None = Query(default=None),
) -> dict[str, Any]:
    if report_path:
        report_path_obj = _resolve_under_repo(report_path)
        report = _load_json(report_path_obj)
        return _plot_payload_from_report(report, fallback_label=report_path_obj.parent.name)

    if output_dir:
        output_dir_obj = _ensure_under_outputs(_resolve_under_repo(output_dir))
        report = _load_json(output_dir_obj / "cosmx_minimal_report.json")
        return _plot_payload_from_report(report, fallback_label=output_dir_obj.name)

    return _get_plot_payload(run_name=DEFAULT_REPORT_RUN)


@app.get("/api/benchmarks/{run_name}")
def get_benchmark(run_name: str) -> dict[str, Any]:
    """Get benchmark summary for a given run.

    Uses path-sanitised resolution to prevent path traversal.
    """
    # Sanitise run_name: only allow safe characters
    if not re.match(r"^[A-Za-z0-9_\-]+$", run_name):
        raise HTTPException(status_code=400, detail=f"Invalid run_name: '{run_name}'")

    benchmark_dir = _ensure_under_outputs(OUTPUTS_ROOT / run_name)
    benchmark_path = benchmark_dir / "benchmark_summary.json"

    if benchmark_path.exists():
        benchmark = _load_json(benchmark_path)
        summary_csv = benchmark_dir / "benchmark_summary.csv"
        # Return relative path to avoid leaking absolute filesystem paths
        try:
            rel_csv_path = str(summary_csv.relative_to(REPO_ROOT))
        except ValueError:
            rel_csv_path = str(summary_csv)
        return {
            "summary": benchmark,
            "summary_csv": rel_csv_path if summary_csv.exists() else None,
        }

    # Fallback: construct rows from individual cosmx_minimal_report.json files in subdirectories
    rows: list[dict[str, Any]] = []
    if benchmark_dir.is_dir():
        for child in sorted(benchmark_dir.iterdir()):
            if not child.is_dir():
                continue
            report_path = child / "cosmx_minimal_report.json"
            if not report_path.exists():
                continue
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                rows.append(report)
            except (json.JSONDecodeError, OSError):
                continue

    if not rows:
        raise HTTPException(status_code=404, detail=f"Benchmark not found for run: {run_name}")

    return {"rows": rows}


@app.get("/api/benchmark-validation")
def get_benchmark_validation() -> dict[str, Any]:
    """Return the backend validation benchmark results and per-run reports.

    Reads benchmark_results.json and individual per-run reports under
    DEFAULT_BENCHMARK_VALIDATION_DIR.
    """
    validation_dir = OUTPUTS_ROOT / "backend_validation"
    if not validation_dir.is_dir():
        raise HTTPException(status_code=404, detail="No backend validation directory found")

    # Load the summary results file
    results_path = validation_dir / "benchmark_results.json"
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="benchmark_results.json not found")

    results = _load_json(results_path)

    # Build per-run details by reading individual report files
    runs: dict[str, Any] = {}
    for key in results:
        run_dir = validation_dir / key
        report_path = run_dir / "cosmx_minimal_report.json"
        report_data = None
        if report_path.exists():
            try:
                report_data = _load_json(report_path)
            except (json.JSONDecodeError, OSError):
                pass
        runs[key] = {
            "status": results[key].get("status"),
            "elapsed_seconds": results[key].get("elapsed_seconds"),
            "n_cells": results[key].get("n_cells"),
            "n_genes": results[key].get("n_genes"),
            "n_clusters": results[key].get("n_clusters"),
            "n_spatial_domains": results[key].get("n_spatial_domains"),
            "n_subcellular_domains": results[key].get("n_subcellular_domains"),
            "error": results[key].get("error"),
            "report": report_data,
        }

    # Compute aggregate stats
    passed = sum(1 for r in results.values() if r.get("status") == "PASS")
    failed = sum(1 for r in results.values() if r.get("status") == "FAIL")
    total = len(results)
    total_elapsed = sum(r.get("elapsed_seconds", 0) for r in results.values())

    return {
        "total_runs": total,
        "passed": passed,
        "failed": failed,
        "total_elapsed_seconds": round(total_elapsed, 1),
        "results": runs,
    }


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
    subcellular_domain_backend: str = Query(default="hdbscan"),
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
        subcellular_domain_backend=subcellular_domain_backend,
    )
    return _run_cosmx(request)


@app.post("/api/cosmx/run")
def cosmx_run(request: CosmxRunRequest | None = None) -> dict[str, Any]:
    if request is None:
        request = CosmxRunRequest()
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
    """Run the CosMx benchmark (grid search over all backend combinations).

    Both input_csv and output_dir are validated for path security.
    """
    # Validate input_csv path
    input_csv_path = _resolve_under_repo(input_csv)
    if not input_csv_path.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found: {input_csv_path}")

    # Validate output_dir and ensure it's under outputs/
    output_dir_path = _resolve_under_repo(output_dir)
    output_dir_path = _ensure_under_outputs(output_dir_path)

    return run_cosmx_backend_benchmark(
        input_csv=str(input_csv_path),
        output_dir=str(output_dir_path),
        min_transcripts=min_transcripts,
        min_genes=min_genes,
        leiden_resolution=leiden_resolution,
        spatial_domain_resolution=spatial_domain_resolution,
        n_spatial_domains=n_spatial_domains,
    )


@app.get("/api/cells/{cell_id}/transcripts")
def get_cell_transcripts(
    cell_id: str,
    run_name: str = Query(default=DEFAULT_REPORT_RUN),
    gene_filter: str | None = None,
) -> dict[str, Any]:
    """Get transcript-level data for a single cell.

    cell_id is sanitised to prevent injection attacks.
    """
    # Sanitise cell_id before using it in queries
    _sanitise_cell_id(cell_id)

    report = _load_json(_resolve_report_path(run_name))
    transcripts_path = report.get("outputs", {}).get("transcripts")
    if not transcripts_path:
        raise HTTPException(status_code=404, detail=f"No transcripts file for run: {run_name}")

    path = _resolve_under_repo(transcripts_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Transcripts file not found: {path}")

    import pandas as pd

    df = pd.read_parquet(path)
    cell_mask = df["cell"] == str(cell_id)
    cell_df = df[cell_mask].copy()

    if gene_filter:
        gene_mask = cell_df["target"].astype(str) == str(gene_filter)
        cell_df = cell_df[gene_mask]

    points = []
    hull_x_vals: list[float] = []
    hull_y_vals: list[float] = []
    for _, row in cell_df.iterrows():
        x = float(row["x_global_px"])
        y = float(row["y_global_px"])
        points.append(
            {
                "x": x,
                "y": y,
                "subcellular_domain": str(row.get("subcellular_domain", "0")),
                "gene": str(row.get("target", "unknown")),
                "cellcomp": str(row.get("CellComp", "unknown")),
                "fov": int(row.get("fov", -1)),
            }
        )
        hull_x_vals.append(x)
        hull_y_vals.append(y)

    hull = _compute_convex_hull(hull_x_vals, hull_y_vals)

    return {
        "cell_id": cell_id,
        "n_transcripts": len(points),
        "genes": sorted(cell_df["target"].astype(str).unique().tolist()),
        "points": points,
        "hull": hull,
        "bounds": {
            "min_x": min(hull_x_vals) if hull_x_vals else 0,
            "max_x": max(hull_x_vals) if hull_x_vals else 0,
            "min_y": min(hull_y_vals) if hull_y_vals else 0,
            "max_y": max(hull_y_vals) if hull_y_vals else 0,
        },
    }


# ── Internal utilities ────────────────────────────────────────────────────


def _compute_convex_hull(xs: list[float], ys: list[float]) -> list[dict[str, float]]:
    """Compute the 2D convex hull of points using Andrew's monotone chain algorithm.

    Returns a list of {x, y} dicts in counter-clockwise order forming the hull polygon.
    """
    if len(xs) < 3:
        return [{"x": x, "y": y} for x, y in zip(xs, ys, strict=False)]

    points = list(zip(xs, ys, strict=False))
    # Remove duplicates and sort by x then y
    points = sorted(set(points))

    # Build lower hull
    lower: list[tuple[float, float]] = []
    for p in points:
        while len(lower) >= 2:
            x1, y1 = lower[-2]
            x2, y2 = lower[-1]
            px, py = p
            if (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1) <= 0:
                lower.pop()
            else:
                break
        lower.append(p)

    # Build upper hull
    upper: list[tuple[float, float]] = []
    for p in reversed(points):
        while len(upper) >= 2:
            x1, y1 = upper[-2]
            x2, y2 = upper[-1]
            px, py = p
            if (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1) <= 0:
                upper.pop()
            else:
                break
        upper.append(p)

    # Remove last point of each half because it's duplicated
    hull_points = lower[:-1] + upper[:-1]
    return [{"x": x, "y": y} for x, y in hull_points]


def _adata_points_payload(adata: ad.AnnData, embedding_key: str, color_key: str) -> dict[str, Any]:
    if embedding_key not in adata.obsm:
        raise HTTPException(status_code=404, detail=f"Embedding not found: {embedding_key}")

    coords = adata.obsm[embedding_key]
    xs = [float(value) for value in coords[:, 0]]
    ys = [float(value) for value in coords[:, 1]]
    colors = [str(value) for value in adata.obs.get(color_key, ["unknown"] * adata.n_obs)]

    return {
        "embedding_key": embedding_key,
        "color_key": color_key,
        "points": [
            {
                "x": x,
                "y": y,
                "color": color,
                "cell_id": str(adata.obs_names[idx]),
            }
            for idx, (x, y, color) in enumerate(zip(xs, ys, colors, strict=False))
        ],
        "stats": {
            "count": int(adata.n_obs),
            "min_x": min(xs),
            "max_x": max(xs),
            "min_y": min(ys),
            "max_y": max(ys),
            "unique_colors": len(set(colors)),
        },
    }


def _get_plot_payload(run_name: str) -> dict[str, Any]:
    report = _load_json(_resolve_report_path(run_name))
    return _plot_payload_from_report(report, fallback_label=run_name)


def _plot_payload_from_report(report: dict[str, Any], fallback_label: str) -> dict[str, Any]:
    adata_path = report.get("outputs", {}).get("adata")
    if not adata_path:
        raise HTTPException(status_code=404, detail=f"Missing adata path for run: {fallback_label}")

    path = _resolve_under_repo(adata_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    adata = ad.read_h5ad(path)
    return {
        "run_name": fallback_label,
        "report_path": report.get("outputs", {}).get("report"),
        "adata_path": str(path),
        "points": {
            "spatial": _adata_points_payload(adata, embedding_key="spatial", color_key="spatial_domain"),
            "umap": _adata_points_payload(adata, embedding_key="X_umap", color_key="cluster"),
        },
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "src.api_server:app",
        host=DEFAULT_API_HOST,
        port=DEFAULT_API_PORT,
        reload=False,
    )
