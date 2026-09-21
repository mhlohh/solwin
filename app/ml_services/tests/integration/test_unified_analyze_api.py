from fastapi.testclient import TestClient

from ml_service.api.schemas import ActionType, BusinessCategory, SecurityRiskLevel
from ml_service.main import create_app


def test_unified_analyze_end_to_end_benign() -> None:
    app = create_app()
    client = TestClient(app)

    payload = {
        "complaint": {
            "message": (
                "I ordered a shirt last week with order #ORD-99881 and paid $45.00, "
                "but the delivery is delayed. Please provide an update."
            ),
            "subject": "Delivery delay",
        },
        "complaint_id": "CMP-1001",
        "include_cluster": True,
        "include_urgency": True,
        "include_resolution": True,
        "include_recommendation": True,
        "include_security": True,
        "include_summary": True,
        "prefer_llm": False,
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Core identification & latency
    assert data["complaint_id"] == "CMP-1001"
    assert data["processing_time_ms"] > 0
    assert data["warnings"] == []

    # 1. Classification
    assert "classification" in data
    assert data["classification"]["category"] in [c.value for c in BusinessCategory]
    assert 0.0 <= data["classification"]["confidence"] <= 1.0

    # 2. Clustering
    assert data["cluster"] is not None
    assert "cluster_id" in data["cluster"]
    assert "cluster_name" in data["cluster"]

    # 3. Urgency
    assert data["urgency"] is not None
    assert "urgency" in data["urgency"]

    # 4. Resolution
    assert data["resolution"] is not None
    assert "status" in data["resolution"]

    # 5. Recommendation
    assert data["recommendation"] is not None
    assert "primary_action" in data["recommendation"]

    # 6. Security
    assert data["security"] is not None
    assert data["security"]["aggregate_risk"] == SecurityRiskLevel.SAFE.value
    assert data["security"]["requires_quarantine"] is False

    # 7. Summary
    assert data["summary"] is not None
    assert "ORD-99881" in data["summary"]["entities_extracted"].get("order_ids", [])
    assert data["summary"]["summary_mode"] == "extractive"


def test_unified_analyze_phishing_quarantine() -> None:
    app = create_app()
    client = TestClient(app)

    payload = {
        "complaint": {
            "message": (
                "URGENT: Your account was suspended! Verify immediately at "
                "http://192.168.1.50/login or email security@amaz0n-alerts.com"
            ),
            "subject": "Account Suspension Alert",
        },
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    sec = data["security"]
    assert sec is not None
    assert sec["aggregate_risk"] == SecurityRiskLevel.HIGH.value
    assert sec["requires_quarantine"] is True
    assert len(sec["urls"]) >= 1
    assert len(sec["emails"]) >= 1

    # Recommendation should trigger security escalation
    rec = data["recommendation"]
    assert rec is not None
    assert rec["primary_action"] == ActionType.ESCALATE_TO_SECURITY_TEAM.value


def test_unified_analyze_selective_flags() -> None:
    app = create_app()
    client = TestClient(app)

    payload = {
        "complaint": {
            "message": "Where is my refund for the returned sneakers?",
            "subject": "Refund inquiry",
        },
        "include_cluster": False,
        "include_urgency": False,
        "include_resolution": False,
        "include_recommendation": False,
        "include_security": False,
        "include_summary": False,
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["classification"] is not None
    assert data["cluster"] is None
    assert data["urgency"] is None
    assert data["resolution"] is None
    assert data["recommendation"] is None
    assert data["security"] is None
    assert data["summary"] is None


def test_unified_analyze_empty_complaint_fails() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post("/api/v1/analyze", json={"complaint": {"message": "", "subject": ""}})
    assert response.status_code == 422


def test_capabilities_all_complete() -> None:
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/v1/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert "unified_analysis" in data["available"]
    assert data["planned"] == []


def test_unified_analyze_batch() -> None:
    app = create_app()
    client = TestClient(app)

    batch_payload = {
        "items": [
            {
                "complaint": {
                    "message": "Payment failed on invoice #INV-12345.",
                    "subject": "Billing issue",
                },
                "complaint_id": "CMP-1",
            },
            {
                "complaint": {
                    "message": "URGENT: Verify your account immediately at http://192.168.1.50/login or email security@amaz0n-alerts.com",
                    "subject": "Account Suspension Alert",
                },
                "complaint_id": "CMP-2",
            },
        ]
    }

    res = client.post("/api/v1/analyze/batch", json=batch_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_processed"] == 2
    assert len(data["results"]) == 2
    assert data["results"][0]["complaint_id"] == "CMP-1"
    assert data["results"][1]["complaint_id"] == "CMP-2"
    assert data["results"][1]["security"]["aggregate_risk"] == SecurityRiskLevel.HIGH.value


def test_analyze_review_canonical_schema() -> None:
    app = create_app()
    client = TestClient(app)

    payload = {
        "review_id": "REV-000123",
        "source_type": "KAGGLE",
        "source_record_id": "12345",
        "domain": "E-commerce/Retail",
        "channel": "Email",
        "subject": "Unauthorized charge on my card",
        "message": "I noticed an unauthorized charge of $350 on my card. Please reverse it immediately.",
        "include_cluster": True,
        "include_urgency": True,
        "include_resolution": True,
        "include_recommendation": True,
        "include_security": True,
        "include_summary": True,
        "include_sentiment": True,
        "prefer_llm": False,
    }

    res = client.post("/api/v1/analyze/review", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Verify all top-level keys match canonical schema
    expected_top_keys = {
        "review_id",
        "source",
        "content",
        "classification",
        "sentiment",
        "keywords",
        "summary",
        "clustering",
        "urgency",
        "resolution",
        "security",
        "overall_risk",
        "recommendation",
        "model_metadata",
        "processing",
    }
    assert expected_top_keys.issubset(set(data.keys()))

    assert data["review_id"] == "REV-000123"
    assert data["source"]["source_type"] == "KAGGLE"
    assert data["source"]["domain"] == "E-commerce/Retail"
    assert data["content"]["subject"] == "Unauthorized charge on my card"

    assert "category" in data["classification"]
    assert "confidence" in data["classification"]
    assert "label" in data["sentiment"]
    assert "score" in data["sentiment"]
    assert isinstance(data["keywords"], list)
    assert "text" in data["summary"]
    assert "cluster_id" in data["clustering"]
    assert "cluster_name" in data["clustering"]
    assert "level" in data["urgency"]
    assert "score" in data["urgency"]
    assert "status" in data["resolution"]
    assert "risk_level" in data["security"]
    assert "risk_score" in data["security"]
    assert "phishing" in data["security"]
    assert "urls" in data["security"]
    assert "email_addresses" in data["security"]
    assert "social_engineering" in data["security"]
    assert "level" in data["overall_risk"]
    assert "score" in data["overall_risk"]
    assert "primary_action" in data["recommendation"]
    assert "priority" in data["recommendation"]
    assert "rationale" in data["recommendation"]
    assert "processed_at" in data["processing"]
    assert "processing_time_ms" in data["processing"]


