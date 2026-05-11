from __future__ import annotations

"""
Legacy pipeline module — preserved for backward compatibility.

The canonical entry point is now ``src.pipeline_engine.run_pipeline``.
This module re-exports ``run_pipeline`` under the old name for any
external code that imports from ``src.pipeline``.
"""

from .models import PipelineResult
from .pipeline_engine import run_pipeline

# Re-export under legacy name for backward compatibility
run_cosmx_minimal = run_pipeline

__all__ = ["PipelineResult", "run_pipeline", "run_cosmx_minimal"]
