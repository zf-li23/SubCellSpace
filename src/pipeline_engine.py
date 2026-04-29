# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Plugin-Style Pipeline Engine
#
# Dynamically executes pipeline steps based on YAML configuration.
# Steps are discovered via the backend registry and called through a
# uniform interface.  The engine is fully data-driven: adding a new
# step only requires adding a YAML entry and a module with
# @register_backend-decorated functions.
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
from .evaluation import build_layer_evaluation
from .io.cosmx import (
    build_cell_level_adata,
    build_spatialdata,
    load_cosmx_transcripts,
    summarize_cosmx_transcripts,
)
from .models import PipelineResult, StepResult
from .registry import get_available_backends, get_runner, load_backends

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
    sdata: Any = None  # SpatialData

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
    ValueError
        If no runner is registered for the step.
    """
    params = dict(step_params or {})

    t0 = time.perf_counter()
    logger.info("Running step '%s' with backend '%s' …", step_name, backend)

    # Dispatch to the registered runner — no if/elif chain needed
    runner = get_runner(step_name)
    result = runner(context, backend, params)

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
    **overrides: Any,
) -> PipelineResult:
    """Run the full pipeline with plugin-style step execution.

    Parameters
    ----------
    settings : Settings or None
        Configuration settings.  If None, the global ``settings``
        singleton is used.
    **overrides
        Any keyword argument overrides the corresponding configuration
        value (highest priority).  Supported keys match the pipeline
        function parameters in ``cosmx_minimal.py``:
        ``input_csv``, ``output_dir``, ``min_transcripts``,
        ``min_genes``, ``denoise_backend``, ``segmentation_backend``,
        ``clustering_backend``, ``leiden_resolution``,
        ``annotation_backend``, ``spatial_domain_backend``,
        ``spatial_domain_resolution``, ``n_spatial_domains``,
        ``subcellular_domain_backend``.
    """
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
    input_csv = Path(str(settings.get("input_csv", "data/sample_transcripts.csv")))
    output_dir = Path(str(settings.get("output_dir", "outputs")))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ensure backends are loaded
    load_backends()

    # ── Initialise execution context ────────────────────────────────
    ctx = ExecutionContext(
        settings=settings,
        pipeline_config=cfg,
        input_csv=input_csv,
        output_dir=output_dir,
    )

    # ── Data loading (always the first step) ─────────────────────────
    logger.info("Loading transcripts from %s", input_csv)
    ctx.transcripts = load_cosmx_transcripts(input_csv)
    summary_ds = summarize_cosmx_transcripts(ctx.transcripts, input_csv)

    # ── Dynamic step execution ───────────────────────────────────────
    for step_cfg in cfg.steps:
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

        _run_step(step_cfg.name, backend, ctx, step_params)

        # Build AnnData right after segmentation so downstream steps
        # (spatial_domain, subcellular_spatial_domain, analysis,
        #  annotation) have access to it.
        if step_cfg.name == "segmentation" and ctx.adata is None and ctx.segmented_df is not None:
            ctx.adata = build_cell_level_adata(ctx.segmented_df)

    # ── Build final outputs ──────────────────────────────────────────
    if ctx.adata is None:
        ctx.adata = build_cell_level_adata(ctx.segmented_df)
    sdata = build_spatialdata(ctx.adata)

    layer_evaluation = build_layer_evaluation(
        raw_df=ctx.transcripts,
        denoised_df=ctx.denoised_df,
        segmented_df=ctx.segmented_df,
        adata=ctx.adata,
    )

    adata_path = output_dir / "cosmx_minimal.h5ad"
    report_path = output_dir / "cosmx_minimal_report.json"
    transcripts_path = output_dir / "cosmx_minimal_transcripts.parquet"

    ctx.adata.write_h5ad(adata_path)
    if ctx.segmented_df is not None:
        ctx.segmented_df.to_parquet(transcripts_path)

    # Build report
    report = {
        "input_csv": str(input_csv),
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
            "spatialdata_points": list(sdata.points.keys()),
            "spatialdata_tables": list(sdata.tables.keys()),
        },
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
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
