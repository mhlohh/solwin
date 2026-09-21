from fastapi.testclient import TestClient

from ml_service.main import create_app


def test_summarize_endpoint() -> None:
    app = create_app()
    client = TestClient(app)

    payload = {
        "complaint": {
            "message": (
                "My order #ORD-98765 was billed $250.00 on 2026-01-15. "
                "I already contacted my bank. Please refund."
            ),
            "subject": "Unauthorized charge",
        },
        "prefer_llm": False,
    }

    response = client.post("/api/v1/summarize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "customer_issue" in data
    assert "actions_taken" in data
    assert (
        "Contacted support team" in data["actions_taken"]
        or "Reported to financial institution" in data["actions_taken"]
    )
    assert "pending_actions" in data
    assert "entities_extracted" in data
    assert "ORD-98765" in data["entities_extracted"].get("order_ids", [])
    assert data["summary_mode"] == "extractive"


def test_capabilities_includes_summary() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data["available"]
