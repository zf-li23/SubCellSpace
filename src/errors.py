# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Unified Error Handling
#
# All pipeline-level exceptions inherit from ``PipelineError``, which
# carries structured context (step name, backend, original exception)
# so that callers (API, CLI, tests) can format meaningful error messages.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Any

# ── Base exception ──────────────────────────────────────────────────


class PipelineError(Exception):
    """Base exception for all SubCellSpace pipeline errors.

    Attributes
    ----------
    message : str
        Human-readable error description.
    step_name : str or None
        The step during which the error occurred (if applicable).
    backend : str or None
        The backend that was being used (if applicable).
    original : BaseException or None
        The original exception that caused this error (if any).
    context : dict
        Additional structured context for debugging / API responses.
    """

    def __init__(
        self,
        message: str,
        *,
        step_name: str | None = None,
        backend: str | None = None,
        original: BaseException | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.step_name = step_name
        self.backend = backend
        self.original = original
        self.context = context or {}
        super().__init__(message)

    @property
    def summary(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict for API responses."""
        d: dict[str, Any] = {
            "error_type": type(self).__name__,
            "message": str(self.args[0]) if self.args else "",
        }
        if self.step_name:
            d["step_name"] = self.step_name
        if self.backend:
            d["backend"] = self.backend
        if self.context:
            d["context"] = self.context
        return d


# ── Concrete exception types ────────────────────────────────────────


class PipelineConfigError(PipelineError):
    """Invalid pipeline configuration (YAML, env vars, programmatic)."""
    pass


class PipelineStepError(PipelineError):
    """A step runner raised an exception during execution."""
    pass


class PipelineContractError(PipelineError):
    """Data contract validation failed between pipeline steps.

    Raised when the output of one step does not satisfy the input
    requirements of the next step.
    """
    pass


class PipelineDataError(PipelineError):
    """Data loading or transformation error (file not found, bad format)."""
    pass


class PipelineRuntimeError(PipelineError):
    """Unexpected runtime error that doesn't fit other categories."""
    pass
