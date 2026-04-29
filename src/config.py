# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Configuration System
# Centralised configuration with three-layer override:
#   1. YAML config file  (lowest priority)
#   2. Environment variables  (medium priority)
#   3. Programmatic / CLI overrides  (highest priority)
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ── Environment variable prefix ─────────────────────────────────────
ENV_PREFIX = "SUBCELLSPACE_"

# ── Default config search paths ─────────────────────────────────────
CONFIG_SEARCH_PATHS = [
    Path("config/pipeline.yaml"),
    Path("~/.subcellspace/config.yaml").expanduser(),
    Path("/etc/subcellspace/config.yaml"),
]

# ── regex to match env var name ─────────────────────────────────────
_ENV_KEY_PATTERN = re.compile(r"^" + ENV_PREFIX)


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Load a YAML config file, returning an empty dict if it doesn't exist."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_env_config() -> dict[str, Any]:
    """Load configuration from environment variables.

    Environment variables with ``SUBCELLSPACE_`` prefix are parsed into
    a nested dict using ``__`` as a separator.

    Examples
    --------
    ``SUBCELLSPACE_PIPELINE__STEPS`` → ``{"pipeline": {"steps": ...}}``
    ``SUBCELLSPACE_PIPELINE__NAME`` → ``{"pipeline": {"name": ...}}``
    """
    config: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        # Remove prefix and split on __ (double underscore)
        rest = key[len(ENV_PREFIX) :]
        parts = rest.lower().split("__")

        # Try to parse as YAML scalar (int, float, bool, None, or string)
        parsed_value = _parse_env_value(value)

        # Walk into nested dict
        current = config
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = parsed_value
    return config


def _parse_env_value(value: str) -> Any:
    """Parse an environment variable string into a Python value.

    Supports int, float, bool, None, comma-separated lists, and raw strings.
    """
    # Try None
    if value.lower() in ("", "null", "none"):
        return None
    # Try bool
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    # Try int
    try:
        return int(value)
    except ValueError:
        pass
    # Try float
    try:
        return float(value)
    except ValueError:
        pass
    # Comma-separated list ?
    if "," in value and not value.startswith("["):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) > 1:
            return parts
    return value


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge two dictionaries (override wins)."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


# ── Configuration dataclasses ───────────────────────────────────────


@dataclass
class StepConfig:
    """Configuration for a single pipeline step."""

    name: str
    module: str = ""
    default_backend: str = ""
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class PipelineConfig:
    """Full pipeline configuration."""

    name: str = "cosmx_minimal"
    description: str = ""
    version: str = "0.1.0"
    steps: list[StepConfig] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> PipelineConfig:
        pipeline = data.get("pipeline", {})
        steps_config_raw = pipeline.get("steps_config", {})
        step_names = pipeline.get("steps", [])

        steps: list[StepConfig] = []
        for name in step_names:
            cfg = steps_config_raw.get(name, {})
            steps.append(
                StepConfig(
                    name=name,
                    module=cfg.get("module", f"src.steps.{name}"),
                    default_backend=cfg.get("default_backend", ""),
                    description=cfg.get("description", ""),
                    params=cfg.get("params", {}),
                    enabled=cfg.get("enabled", True),
                )
            )

        return cls(
            name=pipeline.get("name", "cosmx_minimal"),
            description=pipeline.get("description", ""),
            version=pipeline.get("version", "0.1.0"),
            steps=steps,
            env=data.get("env", {}),
        )

    def get_step_names(self) -> list[str]:
        return [s.name for s in self.steps if s.enabled]

    def get_step_config(self, name: str) -> StepConfig | None:
        for s in self.steps:
            if s.name == name:
                return s
        return None


# ── Main configuration resolver ─────────────────────────────────────


class Settings:
    """Three-layer configuration resolver.

    1. Load YAML from ``config_path`` (or a list of default search paths)
    2. Overlay environment variables (``SUBCELLSPACE_*``)
    3. Allow programmatic overrides via ``update()``
    """

    def __init__(self, config_path: Path | str | None = None) -> None:
        self._raw: dict[str, Any] = {}
        self._overrides: dict[str, Any] = {}

        # Load YAML
        paths = [Path(config_path)] if config_path is not None else CONFIG_SEARCH_PATHS

        loaded = False
        for p in paths:
            data = _load_yaml_config(p)
            if data:
                self._raw = data
                loaded = True
                break
        if not loaded:
            # Fallback to default minimal config
            self._raw = {
                "pipeline": {
                    "name": "cosmx_minimal",
                    "description": "Minimal CosMx spatial transcriptomics analysis pipeline",
                    "version": "0.1.0",
                    "steps": [
                        "denoise",
                        "segmentation",
                        "spatial_domain",
                        "subcellular_spatial_domain",
                        "analysis",
                        "annotation",
                    ],
                    "steps_config": {
                        "denoise": {
                            "module": "src.steps.denoise",
                            "default_backend": "intracellular",
                            "description": "Filter transcripts based on cell compartment",
                        },
                        "segmentation": {
                            "module": "src.steps.segmentation",
                            "default_backend": "provided_cells",
                            "description": "Assign transcripts to cells",
                        },
                        "spatial_domain": {
                            "module": "src.steps.spatial_domain",
                            "default_backend": "spatial_leiden",
                            "description": "Identify tissue-level spatial domains",
                        },
                        "subcellular_spatial_domain": {
                            "module": "src.steps.subcellular_spatial_domain",
                            "default_backend": "hdbscan",
                            "description": "Identify subcellular spatial domains within each cell",
                        },
                        "analysis": {
                            "module": "src.steps.analysis",
                            "default_backend": "leiden",
                            "description": "Clustering & expression analysis",
                        },
                        "annotation": {
                            "module": "src.steps.annotation",
                            "default_backend": "rank_marker",
                            "description": "Cell-type annotation",
                        },
                    },
                }
            }

        # Overlay environment variables
        env_config = _load_env_config()
        if env_config:
            self._raw = deep_merge(self._raw, env_config)

    @property
    def pipeline(self) -> PipelineConfig:
        """Return the resolved pipeline configuration."""
        return PipelineConfig.from_dict(self._raw)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a raw config value by dot-separated key (e.g. ``pipeline.name``)."""
        parts = key.split(".")
        current = {**self._raw, **self._overrides}
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def update(self, overrides: dict[str, Any]) -> None:
        """Apply programmatic overrides (highest priority)."""
        self._overrides = deep_merge(self._overrides, overrides)

    def as_dict(self) -> dict[str, Any]:
        """Return the full resolved config as a dictionary."""
        return deep_merge(self._raw, self._overrides)


# ── Module-level singleton ──────────────────────────────────────────
settings = Settings()
