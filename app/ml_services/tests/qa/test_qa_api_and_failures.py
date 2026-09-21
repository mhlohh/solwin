from pathlib import Path
from fastapi.testclient import TestClient

from ml_service.classification.classifier import ComplaintClassifier
from ml_service.main import create_app


# SECTION 24: API TESTING & BOUNDARY CODES
def test_all_endpoints_status_codes() -> None:
    app = create_app()
    client = TestClient(app)

    # 1. Health
    res_health = client.get("/health")
    assert res_health.status_code == 200

    # 2. Ready
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200

    # 3. Models
    res_models = client.get("/api/v1/models")
    assert res_models.status_code == 200

    # 4. Capabilities
    res_cap = client.get("/api/v1/capabilities")
    assert res_cap.status_code == 200

    # 5. Classify
    res_cls = client.post("/api/v1/classify", json={"message": "Payment failed"})
    assert res_cls.status_code == 200

    # 6. Cluster
    res_cluster = client.post("/api/v1/cluster", json={"message": "Payment failed"})
    assert res_cluster.status_code == 200

    # 7. Urgency
    res_urg = client.post("/api/v1/urgency", json={"message": "Payment failed"})
    assert res_urg.status_code == 200

    # 8. Resolution
    res_res = client.post("/api/v1/resolution", json={"message": "Payment failed"})
    assert res_res.status_code == 200

    # 9. Recommend
    res_rec = client.post(
        "/api/v1/recommend",
        json={"complaint": {"message": "Payment failed"}},
    )
    assert res_rec.status_code == 200

    # 10. Summarize
    res_sum = client.post(
        "/api/v1/summarize",
        json={"complaint": {"message": "Order was not delivered"}},
    )
    assert res_sum.status_code == 200

    # 11. URL analyze
    res_url = client.post("/api/v1/url/analyze", json={"url": "https://google.com"})
    assert res_url.status_code == 200

    # 12. Email analyze
    res_em = client.post("/api/v1/email/analyze", json={"email": "support@google.com"})
    assert res_em.status_code == 200

    # 13. Unified analyze
    res_unified = client.post(
        "/api/v1/analyze",
        json={"complaint": {"message": "Payment failed"}},
    )
    assert res_unified.status_code == 200


def test_api_malformed_input_returns_422() -> None:
    app = create_app()
    client = TestClient(app)

    # Missing required body or invalid type
    res = client.post("/api/v1/classify", json={"invalid_field": 12345})
    assert res.status_code == 422

    # Malformed non-JSON body
    res_text = client.post(
        "/api/v1/classify",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert res_text.status_code == 422


# SECTION 25: MODEL FAILURE TEST
def test_missing_model_fails_safely_503() -> None:
    app = create_app()
    # Simulate missing model on classifier
    app.state.classifier = ComplaintClassifier(model_path=Path("non_existent_model.joblib"))
    client = TestClient(app)

    # Readiness should return 503
    res_ready = client.get("/ready")
    assert res_ready.status_code == 503

    # Inference should return 503, never 500 or fabricated predictions
    res_inf = client.post("/api/v1/classify", json={"message": "Payment failed"})
    assert res_inf.status_code == 503


# SECTION 27: MODEL LOADING TEST (REUSE CONFIRMATION)
def test_model_is_reused_across_requests() -> None:
    app = create_app()
    client = TestClient(app)

    # Record instance id of loaded model pipeline
    first_instance = id(app.state.classifier.pipeline)

    for _ in range(5):
        client.post("/api/v1/classify", json={"message": "Payment failed"})
        assert id(app.state.classifier.pipeline) == first_instance
