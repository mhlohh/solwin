from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ml_service.core.model_registry import ModelRegistry
from ml_service.main import create_app


def test_health_is_available() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_readiness_is_controlled_without_a_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Point registry to non-existent path to verify 503 behavior
    app = create_app()
    app.state.model_registry = ModelRegistry(tmp_path / "empty_registry.yaml")
    response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert response.json()["models_ready"] is False


def test_capabilities_reports_available_classification() -> None:
    response = TestClient(create_app()).get("/api/v1/capabilities")
    assert response.status_code == 200
    assert "classification" in response.json()["available"]

