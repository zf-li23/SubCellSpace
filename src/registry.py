# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Backend Registry
# Central registry for all pipeline step backends.
# Steps register their backends via the @register_backend decorator,
# and consumers query available backends and defaults through this
# module instead of importing step-specific constants.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from .models import StepResult
    from .pipeline_engine import ExecutionContext

# ── type aliases ────────────────────────────────────────────────────
BackendFunc = Callable[..., Any]
StepRunner = Callable[["ExecutionContext", str, dict[str, Any]], "StepResult"]
StepName = str
BackendName = str


# ── Singleton Registry ──────────────────────────────────────────────


class _BackendRegistry:
    """Central registry that maps step names → backend names → callables.

    Usage:
        @registry.register_backend("denoise", "intracellular")
        def my_denoise_func(df, **kwargs): ...
    """

    def __init__(self) -> None:
        self._backends: dict[StepName, dict[BackendName, BackendFunc]] = {}
        self._defaults: dict[StepName, BackendName] = {}
        self._capabilities: dict[StepName, dict[BackendName, list[str]]] = {}
        self._config: dict[str, Any] = {}
        self._config_loaded = False
        self._runners: dict[StepName, StepRunner] = {}

    # ── Public API ──────────────────────────────────────────────

    def register_backend(self, step_name: str, backend_name: str) -> Callable[[BackendFunc], BackendFunc]:
        """Decorator that registers *backend_name* for *step_name*.

        The decorated function is added to the registry and returned
        unchanged so that normal imports / tests still work.
        """

        def decorator(func: BackendFunc) -> BackendFunc:
            self._backends.setdefault(step_name, {})[backend_name] = func
            return func

        return decorator

    def get_available_backends(self, step_name: str) -> list[str]:
        """Return list of registered backend names for *step_name*."""
        self._ensure_config_loaded()
        return list(self._backends.get(step_name, {}))

    def check_backend_available(self, step_name: str, backend_name: str) -> bool:
        """Check whether a specific backend's runtime dependencies are installed.

        This works by importing the step module and reading its
        ``_<BACKEND>_AVAILABLE`` flag.  If no such flag exists, the
        backend is assumed available (since it has been registered).

        Parameters
        ----------
        step_name : str
            The pipeline step name (e.g. ``"segmentation"``).
        backend_name : str
            The backend name to check (e.g. ``"cellpose"``).

        Returns
        -------
        bool
            ``True`` if the backend's dependencies are available,
            ``False`` otherwise.
        """
        # Build the expected flag name: _<BACKEND>_AVAILABLE
        flag_name = f"_{backend_name.upper()}_AVAILABLE"
        step_cfg = self.get_step_config(step_name)
        module_path = step_cfg.get("module", f"src.steps.{step_name}")
        try:
            import importlib
            mod = importlib.import_module(module_path)
            if hasattr(mod, flag_name):
                return getattr(mod, flag_name)
            # No flag → assume available
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def get_backend_func(self, step_name: str, backend_name: str) -> BackendFunc:
        """Return the callable for a specific step+backend combination."""
        self._ensure_config_loaded()
        step_backends = self._backends.get(step_name)
        if step_backends is None:
            raise ValueError(f"Unknown step: {step_name}")
        func = step_backends.get(backend_name)
        if func is None:
            raise ValueError(
                f"Unknown backend '{backend_name}' for step '{step_name}'. Available: {list(step_backends)}"
            )
        return func

    def get_default_backend(self, step_name: str) -> str:
        """Return the default backend name for *step_name* from pipeline.yaml."""
        self._ensure_config_loaded()
        if step_name not in self._defaults:
            raise ValueError(f"No default backend configured for step: {step_name}")
        return self._defaults[step_name]

    def get_step_order(self) -> list[str]:
        """Return the ordered list of step names from pipeline.yaml."""
        self._ensure_config_loaded()
        return list(self._config.get("pipeline", {}).get("steps", []))

    def get_step_config(self, step_name: str) -> dict[str, Any]:
        """Return the full config dict for a step (module, default_backend, etc.)."""
        self._ensure_config_loaded()
        steps_config = self._config.get("pipeline", {}).get("steps_config", {})
        return dict(steps_config.get(step_name, {}))

    def load_backends(self) -> None:
        """Auto-discover and register all backends by importing step modules.

        Each step module is imported, which triggers any ``@register_backend``
        decorators and populates the registry.
        """
        self._ensure_config_loaded()
        for step_name in self.get_step_order():
            step_cfg = self.get_step_config(step_name)
            module_path = step_cfg.get("module")
            if module_path:
                importlib.import_module(module_path)
            default = step_cfg.get("default_backend")
            if default:
                self._defaults[step_name] = default

        # ── Internal helpers ────────────────────────────────────────

    # ── Step runner API ──────────────────────────────────────────

    def register_runner(self, step_name: str) -> Callable[[StepRunner], StepRunner]:
        """Decorator that registers a runner function for *step_name*.

        The runner function encapsulates all step-specific I/O logic
        (reading from and writing to ``ExecutionContext``).  It has
        signature::

            def runner(ctx: ExecutionContext, backend: str,
                       params: dict[str, Any]) -> StepResult

        The engine uses this to eliminate the hardcoded if/elif chain.
        """

        def decorator(func: StepRunner) -> StepRunner:
            self._runners[step_name] = func
            return func

        return decorator

    def get_runner(self, step_name: str) -> StepRunner:
        """Return the registered runner for *step_name*."""
        self._ensure_config_loaded()
        runner = self._runners.get(step_name)
        if runner is None:
            raise ValueError(f"No runner registered for step '{step_name}'. Available runners: {list(self._runners)}")
        return runner

    def get_available_runners(self) -> list[str]:
        """Return list of step names that have registered runners."""
        return list(self._runners)

    # ── Capabilities API ─────────────────────────────────────────

    def declare_capabilities(self, step_name: str, backend_name: str, caps: list[str]) -> None:
        """Declare the analysis capabilities of a backend.

        Called inside step modules to register what analyses a backend
        can perform.  Used by the frontend to dynamically render UI.

        Example::

            registry.declare_capabilities("spatial_analysis", "squidpy",
                                         ["svg", "neighborhood", "co_occurrence"])
        """
        self._capabilities.setdefault(step_name, {})[backend_name] = list(caps)

    def get_capabilities(self, step_name: str) -> dict[str, list[str]]:
        """Return ``{backend_name: [capability, ...]}`` for *step_name*."""
        return dict(self._capabilities.get(step_name, {}))

    def get_all_capabilities(self) -> dict[str, dict[str, list[str]]]:
        """Return all capabilities: ``{step: {backend: [caps]}}``."""
        return {s: dict(b) for s, b in self._capabilities.items()}

    # ── Internal helpers ────────────────────────────────────────

    def _ensure_config_loaded(self) -> None:
        if self._config_loaded:
            return
        # Try using the new Settings singleton first (Phase 1)
        try:
            from .config import settings as _settings

            pipeline_cfg = _settings.pipeline
            self._config = _settings.as_dict()
            for step in pipeline_cfg.steps:
                if step.default_backend:
                    self._defaults[step.name] = step.default_backend
            self._config_loaded = True
            return
        except ImportError:
            pass

        # Fallback: load from YAML file directly
        config_path = Path(__file__).resolve().parent.parent / "config" / "pipeline.yaml"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        self._config_loaded = True


# Module-level singleton
registry = _BackendRegistry()

# Convenience aliases so callers can write:
#   from .registry import registry, register_backend, get_available_backends, ...
register_backend = registry.register_backend
get_available_backends = registry.get_available_backends
check_backend_available = registry.check_backend_available
get_backend_func = registry.get_backend_func
get_default_backend = registry.get_default_backend
get_step_order = registry.get_step_order
get_step_config = registry.get_step_config
load_backends = registry.load_backends
register_runner = registry.register_runner
get_runner = registry.get_runner
get_available_runners = registry.get_available_runners
declare_capabilities = registry.declare_capabilities
get_capabilities = registry.get_capabilities
get_all_capabilities = registry.get_all_capabilities
