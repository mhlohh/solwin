from fastapi.testclient import TestClient

from ml_service.main import create_app


def test_urgency_endpoint() -> None:
    client = TestClient(create_app())
    payload = {
        "subject": "Unauthorized access",
        "message": "My credit card was charged without my authorization.",
    }
    response = client.post("/api/v1/urgency", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["urgency"] == "CRITICAL"
    assert "unauthorized_transaction_indicator" in data["signals"]
    assert len(data["reasons"]) > 0


def test_resolution_endpoint() -> None:
    client = TestClient(create_app())
    payload = {
        "message": "Thanks Shopzilla, my refund was received and ticket is resolved.",
    }
    response = client.post("/api/v1/resolution", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RESOLVED"


def test_recommend_endpoint_inferred() -> None:
    client = TestClient(create_app())
    payload = {
        "complaint": {
            "subject": "Hacked account",
            "message": "Someone hacked into my account and changed my password. Stolen access!",
        }
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "primary_action" in data
    assert "rationale" in data
    assert "matched_rule_id" in data


def test_recommend_endpoint_explicit_attributes() -> None:
    client = TestClient(create_app())
    payload = {
        "complaint": {"message": "Need refund"},
        "category": "REFUND_REQUEST",
        "urgency": "MEDIUM",
        "resolution": "UNRESOLVED",
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["primary_action"] == "INITIATE_REFUND_REVIEW"
