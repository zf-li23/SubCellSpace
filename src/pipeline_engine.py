# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Plugin-Style Pipeline Engine
#
# Dynamically executes pipeline steps based on YAML configuration.
# Steps are discovered via the backend registry and called through a
# uniform interface.  The engine is fully data-driven: adding a new
# step only requires adding a YAML entry and a module with
# @register_backend-decorated functions.
#
# Unified error handling wraps all step failures in ``PipelineStepError``
# and validates inter-step data contracts via ``validate_contract``.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .config import PipelineConfig, Settings
from .errors import PipelineContractError, PipelineDataError, PipelineStepError
from .evaluation import build_layer_evaluation
from .io import get_ingestor
from .io.cosmx import build_cell_level_adata, build_spatialdata_from_adata, load_cosmx_transcripts, summarize_cosmx_transcripts
from .models import PipelineResult, StepResult
from .registry import get_available_backends, get_runner, load_backends
from .validation import validate_contract

logger = logging.getLogger(__name__)


# ── Execution context ──────────────────────────────────────────────


@dataclass
class ExecutionContext:
    """Shared context passed between pipeline steps.

    Each step reads its inputs from this context and writes its outputs
    back.  The engine orchestrates the flow.
    """

    transcripts: pd.DataFrame | None = None
    denoised_df: pd.DataFrame | None = None
    segmented_df: pd.DataFrame | None = None
    adata: Any = None  # AnnData
    sdata: Any = None  # SpatialData — Phase 0+ canonical container

    # Optional: denoised expression matrix (e.g., from spARC backend)
    denoised_expression: Any = None  # np.ndarray | pd.DataFrame | None

    # Accumulated step results
    step_results: dict[str, StepResult] = field(default_factory=dict)

    # Execution metadata
    settings: Settings | None = None
    pipeline_config: PipelineConfig | None = None
    input_csv: str | Path | None = None
    output_dir: Path | None = None


# ── Step adapter helpers ───────────────────────────────────────────


def _run_step(
    step_name: str,
    backend: str,
    context: ExecutionContext,
    step_params: dict[str, Any] | None = None,
) -> StepResult:
    """Execute a single pipeline step by dispatching to its registered runner.

    Each step module registers a ``StepRunner`` via ``@register_runner``
    that encapsulates all I/O logic (reading from / writing to
    ``ExecutionContext``).  This completely eliminates the need for a
    hardcoded if/elif chain — adding a new step is purely data-driven.

    Any exception raised by the step runner is wrapped in a
    ``PipelineStepError`` with structured context.

    Parameters
    ----------
    step_name : str
        The step name (must match the YAML ``steps`` entry and the
        registered step name in the registry).
    backend : str
        The backend name to use for this step.
    context : ExecutionContext
        Current execution context; the step reads inputs from and writes
        outputs to this.
    step_params : dict or None
        Additional keyword arguments forwarded to the step runner.

    Returns
    -------
    StepResult
        The result returned by the step runner.

    Raises
    ------
    PipelineStepError
        If the step runner raises any exception; the original exception
        is preserved in the ``original`` attribute.
    ValueError
        If no runner is registered for the step.
    """
    params = dict(step_params or {})

    t0 = time.perf_counter()
    logger.info("Running step '%s' with backend '%s' …", step_name, backend)

    # Dispatch to the registered runner — no if/elif chain needed
    runner = get_runner(step_name)
    try:
        result = runner(context, backend, params)
    except Exception as exc:
        raise PipelineStepError(
            f"Step '{step_name}' (backend='{backend}') failed: {exc}",
            step_name=step_name,
            backend=backend,
            original=exc,
        ) from exc

    elapsed = time.perf_counter() - t0
    logger.info(
        "Step '%s' completed in %.2fs (backend=%s)",
        step_name,
        elapsed,
        result.backend_used,
    )

    # Add timing to summary
    result.summary["__elapsed_seconds__"] = round(elapsed, 3)
    context.step_results[step_name] = result
    return result


# ── Main pipeline runner ───────────────────────────────────────────


def run_pipeline(
    settings: Settings | None = None,
    sdata: Any = None,   # ← NEW: pre-ingested SpatialData (Phase 0)
    **overrides: Any,
) -> PipelineResult:
    """Run the full pipeline with plugin-style step execution.

    Parameters
    ----------
    settings : Settings or None
        Configuration settings.
    sdata : SpatialData or None
        Pre-ingested spatial data object (from Phase 0).  If provided,
        the pipeline skips data loading and uses this directly.
    **overrides
        Any keyword argument overrides configuration values.

    Raises
    ------
    PipelineContractError
        If inter-step data contract validation fails.
    PipelineStepError
        If any step runner raises an exception.
    PipelineDataError
        If data loading fails.
    """
    from .constants import KEY_RAW_TRANSCRIPTS
    from .config import settings as default_settings

    settings = settings or default_settings

    # Apply overrides
    if overrides:
        settings.update(overrides)

    cfg = settings.pipeline
    logger.info(
        "Starting pipeline '%s' v%s (%d steps)",
        cfg.name,
        cfg.version,
        len(cfg.steps),
    )

    # Resolve input / output
    output_dir = Path(str(settings.get("output_dir", "outputs")))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ensure backends are loaded
    load_backends()

    # ── Initialise execution context ────────────────────────────────
    ctx = ExecutionContext(
        settings=settings,
        pipeline_config=cfg,
        output_dir=output_dir,
        sdata=sdata,
    )

    # ── Data loading (Phase 0 or legacy) ────────────────────────────
    if sdata is not None:
        # ── Phase 0+ path: data already ingested as SpatialData ────
        logger.info("Using pre-ingested SpatialData (Phase 0 path)")
        ctx.sdata = sdata

        # Extract transcripts from SpatialData points layer
        points_key = sdata.attrs.get("raw_transcripts_key", KEY_RAW_TRANSCRIPTS)
        if points_key not in sdata.points:
            raise PipelineDataError(
                f"SpatialData does not contain '{points_key}' in points layer.",
                context={"available_points": list(sdata.points.keys())},
            )
        ctx.transcripts = sdata.points[points_key].compute()

        # Build summary from attrs
        summary_dict = sdata.attrs.get("ingestion_summary", {})
        from .models import DatasetSummary
        summary_ds = DatasetSummary(
            source_path=Path(str(settings.get("input_csv", "unknown"))),
            n_transcripts=summary_dict.get("n_transcripts", len(ctx.transcripts)),
            n_cells=summary_dict.get("n_cells", 0),
            n_genes=summary_dict.get("n_genes", 0),
            n_fovs=summary_dict.get("n_fovs", 1),
            extra={k: v for k, v in summary_dict.items()
                   if k not in ("n_transcripts", "n_cells", "n_genes", "n_fovs")},
        )
    else:
        # ── Legacy path: load CSV directly (backward compat) ────────
        input_csv = Path(str(settings.get("input_csv", "data/sample_transcripts.csv")))
        ctx.input_csv = input_csv
        logger.info("Loading transcripts from %s (legacy path)", input_csv)
        platform = str(settings.get("platform", "cosmx"))
        try:
            if platform == "cosmx":
                ctx.transcripts = load_cosmx_transcripts(input_csv)
                summary_ds = summarize_cosmx_transcripts(ctx.transcripts, input_csv)
            else:
                sd = get_ingestor(platform).ingest(input_csv)
                ctx.sdata = sd
                pts_key = sd.attrs.get("raw_transcripts_key", KEY_RAW_TRANSCRIPTS)
                ctx.transcripts = sd.points[pts_key].compute()
                summary_dict = sd.attrs.get("ingestion_summary", {})
                from .models import DatasetSummary
                summary_ds = DatasetSummary(
                    source_path=input_csv,
                    n_transcripts=summary_dict.get("n_transcripts", 0),
                    n_cells=summary_dict.get("n_cells", 0),
                    n_genes=summary_dict.get("n_genes", 0),
                    n_fovs=summary_dict.get("n_fovs", 1),
                    extra={},
                )
        except Exception as exc:
            raise PipelineDataError(
                f"Failed to load data for platform '{platform}' from {input_csv}: {exc}",
                original=exc,
                context={"platform": platform, "path": str(input_csv)},
            ) from exc

    # ── Dynamic step execution ───────────────────────────────────────
    step_names = cfg.get_step_names()
    for idx, step_cfg in enumerate(cfg.steps):
        if not step_cfg.enabled:
            logger.info("Skipping disabled step '%s'", step_cfg.name)
            continue

        backend = overrides.get(f"{step_cfg.name}_backend")
        if backend is None:
            backend = step_cfg.default_backend

        # Check if the backend is available; if not, fall back to default
        available = get_available_backends(step_cfg.name)
        if backend not in available:
            fallback = step_cfg.default_backend
            logger.warning(
                "Backend '%s' not available for step '%s'. Available: %s. Falling back to '%s'.",
                backend,
                step_cfg.name,
                available,
                fallback,
            )
            backend = fallback

        # Build per-step params from overrides
        step_params: dict[str, Any] = dict(step_cfg.params)
        for key, value in overrides.items():
            if key.startswith(step_cfg.name + "_"):
                param_name = key[len(step_cfg.name) + 1 :]
                step_params[param_name] = value
        # Generic pipeline-level params that map to the analysis step
        if step_cfg.name == "analysis":
            for generic_param in ("min_transcripts", "min_genes"):
                if generic_param in overrides and generic_param not in step_params:
                    step_params[generic_param] = overrides[generic_param]
                elif generic_param not in step_params:
                    # Also check settings overrides (not just kwargs)
                    val = settings.get(generic_param)
                    if val is not None:
                        step_params[generic_param] = val

        # ── Run the step (with unified error wrapping) ────────────────
        _run_step(step_cfg.name, backend, ctx, step_params)

        # Build AnnData right after segmentation so downstream steps
        # (spatial_domain, subcellular_spatial_domain, analysis,
        #  annotation) have access to it.
        if step_cfg.name == "segmentation" and ctx.adata is None and ctx.segmented_df is not None:
            ctx.adata = build_cell_level_adata(ctx.segmented_df)

        # ── Inter-step contract validation ──────────────────────────
        # Determine the next step for contract validation
        next_step = step_names[idx + 1] if idx + 1 < len(step_names) else "__pipeline_end__"
        contract_msgs = validate_contract(step_cfg.name, next_step, ctx)
        if contract_msgs:
            error_detail = "; ".join(contract_msgs)
            logger.error("Contract violation: %s", error_detail)
            raise PipelineContractError(
                f"Data contract violation after step '{step_cfg.name}': {error_detail}",
                step_name=step_cfg.name,
                backend=backend,
                context={"contract_errors": contract_msgs, "next_step": next_step},
            )

    # ── Build final outputs ──────────────────────────────────────────
    if ctx.adata is None:
        ctx.adata = build_cell_level_adata(ctx.segmented_df)

    # Use existing SpatialData if available (Phase 0+), otherwise build
    if ctx.sdata is not None:
        sdata = ctx.sdata
    else:
        sdata = build_spatialdata_from_adata(ctx.adata)
        ctx.sdata = sdata

    layer_evaluation = build_layer_evaluation(
        raw_df=ctx.transcripts,
        denoised_df=ctx.denoised_df,
        segmented_df=ctx.segmented_df,
        adata=ctx.adata,
    )

    cfg_name = cfg.name or "pipeline"
    adata_path = output_dir / f"{cfg_name}.h5ad"
    report_path = output_dir / f"{cfg_name}_report.json"
    transcripts_path = output_dir / f"{cfg_name}_transcripts.parquet"

    ctx.adata.write_h5ad(adata_path)
    if ctx.segmented_df is not None:
        # Strip non-JSON-serializable attrs before writing parquet
        clean_df = ctx.segmented_df.copy()
        clean_df.attrs = {}
        clean_df.to_parquet(transcripts_path)

    # Build report
    report = {
        "input_csv": str(ctx.input_csv or settings.get("input_csv", "unknown")),
        "pipeline_name": cfg.name,
        "pipeline_version": cfg.version,
        "n_obs": int(ctx.adata.n_obs),
        "n_vars": int(ctx.adata.n_vars),
        "clusters": (
            ctx.adata.obs["cluster"].value_counts().sort_index().to_dict() if "cluster" in ctx.adata.obs else {}
        ),
        "summary": {
            "n_transcripts": summary_ds.n_transcripts,
            "n_cells": summary_ds.n_cells,
            "n_genes": summary_ds.n_genes,
            "n_fovs": summary_ds.n_fovs,
            **summary_ds.extra,
        },
        "step_summary": {name: result.summary for name, result in ctx.step_results.items()},
        "step_order": cfg.get_step_names(),
        "layer_evaluation": layer_evaluation,
        "outputs": {
            "adata": str(adata_path),
            "report": str(report_path),
            "transcripts": str(transcripts_path),
            "spatialdata_points": list(sdata.points.keys()) if sdata.points else [],
            "spatialdata_tables": list(sdata.tables.keys()) if sdata.tables else [],
            "spatialdata_images": list(sdata.images.keys()) if sdata.images else [],
            "spatialdata_shapes": list(sdata.shapes.keys()) if sdata.shapes else [],
        },
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    logger.info(
        "Pipeline finished — %d transcripts, %d cells, %d genes",
        summary_ds.n_transcripts,
        summary_ds.n_cells,
        summary_ds.n_genes,
    )

    return PipelineResult(
        adata=ctx.adata,
        summary=summary_ds,
        sdata=sdata,
        adata_path=adata_path,
        report_path=report_path,
    )
