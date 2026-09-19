from fastapi.testclient import TestClient

from ml_service.main import create_app


def test_health_is_available_and_returns_request_id() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_readiness_is_controlled_when_no_model_is_registered() -> None:
    response = TestClient(create_app()).get("/ready")

    assert response.status_code == 503
    assert response.json()["models_ready"] is False


def test_complaint_schema_requires_text() -> None:
    response = TestClient(create_app()).post("/api/v1/analyze", json={})

    assert response.status_code == 404
