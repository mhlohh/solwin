from fastapi.testclient import TestClient

from ml_service.main import create_app


def test_url_analyze_endpoint_with_text() -> None:
    client = TestClient(create_app())
    payload = {
        "text": "Your account is locked. Reset password immediately at: http://192.168.0.1/verify.php",
    }
    response = client.post("/api/v1/url/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] >= 1
    first = data["results"][0]
    assert first["domain"] == "192.168.0.1"
    assert "ip_address_host" in first["signals"]
    assert first["risk_score"] > 0.0


def test_email_analyze_endpoint_with_email() -> None:
    client = TestClient(create_app())
    payload = {
        "email": "security-alert@amaz0n.com",
    }
    response = client.post("/api/v1/email/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 1
    first = data["results"][0]
    assert first["risk_level"] in {"HIGH", "MEDIUM"}
    assert any("typosquatting" in r for r in first["reasons"])
