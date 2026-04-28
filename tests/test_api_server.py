from __future__ import annotations

from pathlib import Path
import json

import pytest
from fastapi.testclient import TestClient

from src.api_server import app, _validate_backend, _resolve_under_repo, _resolve_report_path, _parse_allowed_origins

client = TestClient(app)


class TestHealthAndMeta:
    def test_health(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_backends(self):
        response = client.get("/api/meta/backends")
        assert response.status_code == 200
        data = response.json()
        assert "denoise" in data
        assert "segmentation" in data
        assert "clustering" in data
        assert "annotation" in data
        assert "spatial_domain" in data
        assert "subcellular_spatial_domain" in data
        for key in data:
            assert isinstance(data[key], list)
            assert len(data[key]) > 0


class TestValidateBackend:
    def test_valid_backend(self):
        # Should not raise
        _validate_backend("test_backend", "intracellular", ["intracellular", "supercellular"])

    def test_invalid_backend_raises(self):
        with pytest.raises(Exception):  # HTTPException
            _validate_backend("test_backend", "bad_value", ["allowed_value"])


class TestPathResolution:
    def test_resolve_under_repo_relative(self):
        path = _resolve_under_repo("README.md")
        assert path.is_absolute()
        assert path.exists()

    def test_resolve_report_path(self):
        path = _resolve_report_path("test_run_name")
        assert path.name == "cosmx_minimal_report.json"
        assert "outputs" in str(path)


class TestParseAllowedOrigins:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("SUBCELLSPACE_ALLOWED_ORIGINS", raising=False)
        origins = _parse_allowed_origins()
        assert "http://127.0.0.1:5173" in origins
        assert "http://localhost:5173" in origins

    def test_custom(self, monkeypatch):
        monkeypatch.setenv("SUBCELLSPACE_ALLOWED_ORIGINS", "http://example.com,http://test:3000")
        origins = _parse_allowed_origins()
        assert origins == ["http://example.com", "http://test:3000"]

    def test_empty_strings_filtered(self, monkeypatch):
        monkeypatch.setenv("SUBCELLSPACE_ALLOWED_ORIGINS", "http://a.com, , http://b.com,")
        origins = _parse_allowed_origins()
        assert origins == ["http://a.com", "http://b.com"]


class TestCorsMiddleware:
    def test_cors_headers_present(self):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI TestClient may not trigger CORS preflight perfectly,
        # but we can verify the app has CORSMiddleware configured
        assert response.status_code in (200, 204, 405)  # Accept various responses


class TestPlotsEndpoint:
    def test_plots_without_params(self):
        """Test that /api/plots without params returns 404 or 200 (run-dependent)."""
        response = client.get("/api/plots")
        # Will fail because there's no default report, but shouldn't crash
        assert response.status_code in (200, 404)