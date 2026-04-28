# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Backend Registry
# Central registry for all pipeline step backends.
# Steps register their backends via the @register_backend decorator,
# and consumers query available backends and defaults through this
# module instead of importing step-specific constants.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

import yaml

# ── type aliases ────────────────────────────────────────────────────
BackendFunc = Callable[..., Any]
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
        self._config: dict[str, Any] = {}
        self._config_loaded = False

    # ── Public API ──────────────────────────────────────────────

    def register_backend(
        self, step_name: str, backend_name: str
    ) -> Callable[[BackendFunc], BackendFunc]:
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

    def get_backend_func(self, step_name: str, backend_name: str) -> BackendFunc:
        """Return the callable for a specific step+backend combination."""
        self._ensure_config_loaded()
        step_backends = self._backends.get(step_name)
        if step_backends is None:
            raise ValueError(f"Unknown step: {step_name}")
        func = step_backends.get(backend_name)
        if func is None:
            raise ValueError(
                f"Unknown backend '{backend_name}' for step '{step_name}'. "
                f"Available: {list(step_backends)}"
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
        config_path = (
            Path(__file__).resolve().parent.parent / "config" / "pipeline.yaml"
        )
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
get_backend_func = registry.get_backend_func
get_default_backend = registry.get_default_backend
get_step_order = registry.get_step_order
get_step_config = registry.get_step_config
load_backends = registry.load_backends
