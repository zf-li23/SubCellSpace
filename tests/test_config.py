from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.config import (
    Settings,
    PipelineConfig,
    StepConfig,
    _load_env_config,
    _parse_env_value,
    deep_merge,
    CONFIG_SEARCH_PATHS,
)


class TestParseEnvValue:
    def test_none_values(self):
        assert _parse_env_value("") is None
        assert _parse_env_value("null") is None
        assert _parse_env_value("None") is None
        assert _parse_env_value("none") is None

    def test_boolean_values(self):
        assert _parse_env_value("true") is True
        assert _parse_env_value("True") is True
        assert _parse_env_value("yes") is True
        assert _parse_env_value("1") is True
        assert _parse_env_value("false") is False
        assert _parse_env_value("False") is False
        assert _parse_env_value("no") is False
        assert _parse_env_value("0") is False

    def test_numeric_values(self):
        assert _parse_env_value("42") == 42
        assert _parse_env_value("-1") == -1
        assert _parse_env_value("3.14") == 3.14
        assert _parse_env_value("-0.5") == -0.5

    def test_list_values(self):
        assert _parse_env_value("a,b,c") == ["a", "b", "c"]
        assert _parse_env_value(" one , two ") == ["one", "two"]
        # Single trailing comma → split yields single item → treated as string
        assert _parse_env_value("single,") == "single,"

    def test_string_values(self):
        assert _parse_env_value("hello") == "hello"
        assert _parse_env_value("some_value") == "some_value"


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"pipeline": {"name": "test", "steps": ["a"]}}
        override = {"pipeline": {"steps": ["a", "b"]}}
        result = deep_merge(base, override)
        assert result["pipeline"]["name"] == "test"
        assert result["pipeline"]["steps"] == ["a", "b"]

    def test_override_not_dict(self):
        base = {"pipeline": {"name": "test"}}
        override = {"pipeline": "simple"}
        result = deep_merge(base, override)
        assert result["pipeline"] == "simple"

    def test_empty_overrides(self):
        base = {"a": 1}
        assert deep_merge(base, {}) == base

    def test_empty_base(self):
        override = {"a": 1}
        assert deep_merge({}, override) == override


class TestLoadEnvConfig:
    def test_no_env_vars(self, monkeypatch):
        monkeypatch.delenv("SUBCELLSPACE_PIPELINE__STEPS", raising=False)
        monkeypatch.delenv("SUBCELLSPACE_PIPELINE__NAME", raising=False)
        result = _load_env_config()
        assert isinstance(result, dict)

    def test_single_env_var(self, monkeypatch):
        monkeypatch.setenv("SUBCELLSPACE_PIPELINE__NAME", "test_pipeline")
        result = _load_env_config()
        assert result.get("pipeline", {}).get("name") == "test_pipeline"

    def test_nested_env_var(self, monkeypatch):
        monkeypatch.setenv("SUBCELLSPACE_PIPELINE__STEPS", "denoise,segmentation")
        result = _load_env_config()
        steps = result.get("pipeline", {}).get("steps")
        assert steps == ["denoise", "segmentation"]

    def test_non_prefixed_var_ignored(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.delenv("SUBCELLSPACE_PIPELINE__NAME", raising=False)
        result = _load_env_config()
        assert "HOME" not in result


class TestStepConfig:
    def test_basic_construction(self):
        cfg = StepConfig(
            name="denoise",
            module="src.steps.denoise",
            default_backend="intracellular",
        )
        assert cfg.name == "denoise"
        assert cfg.default_backend == "intracellular"
        assert cfg.enabled is True

    def test_disabled(self):
        cfg = StepConfig(name="test", enabled=False)
        assert cfg.enabled is False


class TestPipelineConfig:
    def test_from_dict_minimal(self):
        data = {
            "pipeline": {
                "name": "test",
                "steps": ["denoise", "segmentation"],
                "steps_config": {},
            }
        }
        cfg = PipelineConfig.from_dict(data)
        assert cfg.name == "test"
        assert len(cfg.steps) == 2
        assert cfg.steps[0].name == "denoise"
        assert cfg.steps[1].name == "segmentation"

    def test_from_dict_with_config(self):
        data = {
            "pipeline": {
                "name": "test",
                "steps": ["denoise"],
                "steps_config": {
                    "denoise": {
                        "module": "src.steps.denoise",
                        "default_backend": "intracellular",
                        "enabled": True,
                    }
                },
            }
        }
        cfg = PipelineConfig.from_dict(data)
        assert cfg.steps[0].default_backend == "intracellular"

    def test_get_step_names_respects_enabled(self):
        data = {
            "pipeline": {
                "steps": ["a", "b"],
                "steps_config": {
                    "a": {"enabled": True},
                    "b": {"enabled": False},
                },
            }
        }
        cfg = PipelineConfig.from_dict(data)
        assert cfg.get_step_names() == ["a"]

    def test_get_step_config_found(self):
        data = {
            "pipeline": {
                "steps": ["a"],
                "steps_config": {"a": {"default_backend": "test"}},
            }
        }
        cfg = PipelineConfig.from_dict(data)
        step = cfg.get_step_config("a")
        assert step is not None
        assert step.default_backend == "test"

    def test_get_step_config_not_found(self):
        cfg = PipelineConfig.from_dict({"pipeline": {"steps": []}})
        assert cfg.get_step_config("nonexistent") is None


class TestSettings:
    def test_default_config(self):
        """Settings() without a config file should load the hardcoded default."""
        settings = Settings(config_path="/nonexistent/path.yaml")
        cfg = settings.pipeline
        assert cfg.name == "cosmx_minimal"
        assert len(cfg.steps) == 6
        step_names = cfg.get_step_names()
        assert "denoise" in step_names
        assert "segmentation" in step_names
        assert "spatial_domain" in step_names
        assert "subcellular_spatial_domain" in step_names
        assert "analysis" in step_names
        assert "annotation" in step_names

    def test_get_method(self):
        settings = Settings(config_path="/nonexistent/path.yaml")
        assert settings.get("pipeline.name") == "cosmx_minimal"
        assert settings.get("nonexistent", "default") == "default"
        assert settings.get("pipeline.nonexistent", 42) == 42

    def test_update_overrides(self):
        settings = Settings(config_path="/nonexistent/path.yaml")
        settings.update({"input_csv": "/custom/path.csv"})
        assert settings.get("input_csv") == "/custom/path.csv"
        # Original defaults still there
        assert settings.get("pipeline.name") == "cosmx_minimal"

    def test_as_dict(self):
        settings = Settings(config_path="/nonexistent/path.yaml")
        d = settings.as_dict()
        assert isinstance(d, dict)
        assert "pipeline" in d

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("SUBCELLSPACE_PIPELINE__NAME", "env_pipeline")
        settings = Settings(config_path="/nonexistent/path.yaml")
        assert settings.get("pipeline.name") == "env_pipeline"

    def test_programmatic_override_highest_priority(self, monkeypatch):
        monkeypatch.setenv("SUBCELLSPACE_INPUT_CSV", "env_path.csv")
        settings = Settings(config_path="/nonexistent/path.yaml")
        assert settings.get("input_csv") == "env_path.csv"
        # Programmatic override should win
        settings.update({"input_csv": "prog_path.csv"})
        assert settings.get("input_csv") == "prog_path.csv"


class TestSettingsWithConfigFile:
    def test_yaml_config_loaded(self, tmp_path):
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(
            "pipeline:\n"
            "  name: custom_pipeline\n"
            "  steps:\n"
            "    - denoise\n"
            "  steps_config:\n"
            "    denoise:\n"
            "      default_backend: nuclear_only\n"
        )
        settings = Settings(config_path=str(config_path))
        assert settings.get("pipeline.name") == "custom_pipeline"
        step = settings.pipeline.steps[0]
        assert step.default_backend == "nuclear_only"

    def test_env_overrides_yaml(self, monkeypatch, tmp_path):
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(
            "pipeline:\n"
            "  name: yaml_name\n"
            "  version: '1.0'\n"
        )
        monkeypatch.setenv("SUBCELLSPACE_PIPELINE__NAME", "env_name")
        settings = Settings(config_path=str(config_path))
        # Env should override YAML
        assert settings.get("pipeline.name") == "env_name"
        # Non-overridden YAML values should remain
        assert settings.get("pipeline.version") == "1.0"

    def test_invalid_yaml_path(self):
        """Non-existent path should fall back to defaults gracefully."""
        settings = Settings(config_path="/tmp/__nonexistent_subcellspace_config.yaml")
        assert settings.pipeline.name == "cosmx_minimal"


class TestSearchPaths:
    def test_search_paths_exist(self):
        assert len(CONFIG_SEARCH_PATHS) == 3
        assert all(isinstance(p, Path) for p in CONFIG_SEARCH_PATHS)
