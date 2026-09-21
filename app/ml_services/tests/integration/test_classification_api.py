from fastapi.testclient import TestClient

from ml_service.main import create_app


def test_classify_endpoint_success() -> None:
    client = TestClient(create_app())
    payload = {
        "subject": "Delayed order",
        "message": "I ordered 10 days ago and the package has not arrived. Track ID #12345.",
    }
    response = client.post("/api/v1/classify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "category" in data
    assert "confidence" in data
    assert "probabilities" in data
    assert "needs_review" in data
    assert len(data["probabilities"]) == 11


def test_classify_endpoint_with_custom_threshold() -> None:
    client = TestClient(create_app())
    payload = {
        "message": "Refund enquiry for cancelled order",
    }
    # Force abstention by requiring 0.99 confidence
    response = client.post("/api/v1/classify?threshold=0.99", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_review"] is True


def test_classify_endpoint_validation_error_on_empty() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/classify", json={})
    assert response.status_code == 422


def test_ready_is_now_available_with_production_model() -> None:
    client = TestClient(create_app())
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["models_ready"] is True
