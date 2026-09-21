import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.enums import SenderType
from app.models.message import Message
from app.models.threat import Threat
from app.services.security.email_analyzer import EmailAnalyzer
from app.services.security.phishing_detector import PhishingDetector
from app.services.security.risk_engine import RiskEngine
from app.services.security.social_engineering import SocialEngineeringDetector
from app.services.security.url_analyzer import URLAnalyzer


# ==========================================
# 1. URL Analysis Tests
# ==========================================
def test_url_normal():
    analyzer = URLAnalyzer()
    res = analyzer.analyze_text("Visit our official docs at https://solwin.ai/docs")
    assert len(res) == 1
    assert res[0].url == "https://solwin.ai/docs"
    assert res[0].domain == "solwin.ai"
    assert res[0].is_https is True
    assert res[0].is_ip_address is False
    assert res[0].suspicious is False


def test_url_http_scheme():
    analyzer = URLAnalyzer()
    res = analyzer.analyze_text("See http://insecure-site.org")
    assert len(res) == 1
    assert res[0].is_https is False
    assert "Insecure HTTP scheme used" in res[0].signals


def test_url_ip_based():
    analyzer = URLAnalyzer()
    res = analyzer.analyze_text("Connect to http://192.168.1.1/admin")
    assert len(res) == 1
    assert res[0].is_ip_address is True
    assert res[0].suspicious is True
    assert any("IP address" in s for s in res[0].signals)


def test_url_lookalike_domain():
    analyzer = URLAnalyzer()
    res = analyzer.analyze_text("Verify here: https://paypa1-security.example/login")
    assert len(res) == 1
    assert res[0].lookalike_detected is True
    assert res[0].suspicious is True


def test_url_shortener():
    analyzer = URLAnalyzer()
    res = analyzer.analyze_text("Click this link: https://bit.ly/secure-token")
    assert len(res) == 1
    assert res[0].is_shortener is True
    assert res[0].suspicious is True


def test_url_suspicious_credential_path():
    analyzer = URLAnalyzer()
    res = analyzer.analyze_text("http://customer-portal.xyz/verify-account-password")
    assert len(res) == 1
    assert any("Credential/security lure" in s for s in res[0].signals)


def test_url_multiple_urls():
    analyzer = URLAnalyzer()
    res = analyzer.analyze_text(
        "First check https://solwin.ai then visit http://paypa1-login.com"
    )
    assert len(res) == 2
    assert res[0].suspicious is False
    assert res[1].suspicious is True


# ==========================================
# 2. Email Analysis Tests
# ==========================================
def test_email_normal():
    analyzer = EmailAnalyzer()
    res = analyzer.analyze_text("Contact us at support@solwin.ai")
    assert len(res) == 1
    assert res[0].email == "support@solwin.ai"
    assert res[0].is_free_mail is False
    assert res[0].suspicious is False


def test_email_suspicious_lookalike():
    analyzer = EmailAnalyzer()
    res = analyzer.analyze_text("Sent from security@micros0ft-support.example")
    assert len(res) == 1
    assert res[0].lookalike_detected is True
    assert res[0].suspicious is True


def test_email_freemail_contextual_signal():
    analyzer = EmailAnalyzer()
    res = analyzer.analyze_text("Email me at agent.smith@gmail.com")
    assert len(res) == 1
    assert res[0].is_free_mail is True
    assert res[0].suspicious is False


def test_email_spoofed_display_name():
    analyzer = EmailAnalyzer()
    res = analyzer.analyze_email(
        "billing-update@suspicious-domain.xyz",
        display_name="PayPal Support",
    )
    assert res.suspicious is True
    assert any("Display name claims" in s for s in res.signals)


# ==========================================
# 3. Social Engineering Tests
# ==========================================
def test_social_engineering_urgency():
    detector = SocialEngineeringDetector()
    res = detector.detect("URGENT! Your account will be suspended within 24 hours.")
    assert res.detected is True
    assert "URGENCY" in res.techniques


def test_social_engineering_credential_harvesting():
    detector = SocialEngineeringDetector()
    res = detector.detect("Please enter your password and update your credentials.")
    assert res.detected is True
    assert "CREDENTIAL_HARVESTING" in res.techniques


def test_social_engineering_otp_request():
    detector = SocialEngineeringDetector()
    res = detector.detect("Forward the 6-digit verification code OTP immediately.")
    assert res.detected is True
    assert "OTP_REQUEST" in res.techniques


def test_social_engineering_impersonation():
    detector = SocialEngineeringDetector()
    res = detector.detect("This is an alert from Microsoft Security team.")
    assert res.detected is True
    assert "IMPERSONATION" in res.techniques


def test_social_engineering_combination():
    detector = SocialEngineeringDetector()
    res = detector.detect(
        "URGENT: Microsoft Security here. Your account is compromised! "
        "Enter your password and share your OTP right now."
    )
    assert res.detected is True
    assert set(res.techniques) == {
        "URGENCY",
        "IMPERSONATION",
        "CREDENTIAL_HARVESTING",
        "OTP_REQUEST",
    }


# ==========================================
# 4. Phishing Detection Tests
# ==========================================
def test_phishing_clear_attack():
    detector = PhishingDetector()
    res = detector.analyze(
        "URGENT! Click https://paypa1-security.example/login to verify password."
    )
    assert res.threat_detected is True
    assert res.threat_type == "PHISHING"
    assert len(res.suspicious_urls) == 1


def test_phishing_normal_support_message():
    detector = PhishingDetector()
    res = detector.analyze(
        "Hello, can you please tell me when the new feature release is scheduled?"
    )
    assert res.threat_detected is False
    assert res.threat_type == "NONE"


def test_phishing_suspicious_message():
    detector = PhishingDetector()
    res = detector.analyze("URGENT notice from official administrator team.")
    assert res.threat_detected is True
    assert res.threat_type == "SUSPICIOUS_MESSAGE"


# ==========================================
# 5. Risk Engine Tests
# ==========================================
def test_risk_low():
    engine = RiskEngine()
    res = engine.evaluate("Can you help me reset my preferred dashboard timezone?")
    assert res.risk_level == "LOW"
    assert res.threat_detected is False
    assert "normal support handling" in res.recommended_action.lower()


def test_risk_medium():
    engine = RiskEngine()
    res = engine.evaluate(
        "This is an urgent message regarding our upcoming system renewal."
    )
    assert res.risk_level in ["LOW", "MEDIUM"]


def test_risk_high():
    engine = RiskEngine()
    res = engine.evaluate("Please enter your password at http://192.168.1.100/login")
    assert res.risk_level in ["HIGH", "CRITICAL"]
    assert res.threat_detected is True


def test_risk_critical():
    engine = RiskEngine()
    res = engine.evaluate(
        "URGENT! Microsoft Security: Account suspended. "
        "Visit https://paypa1-login.com to submit your password and OTP code!"
    )
    assert res.risk_level == "CRITICAL"
    assert res.threat_detected is True
    assert len(res.risk_reasons) >= 3
    assert "escalate to the security team" in res.recommended_action.lower()


# ==========================================
# 6. Adversarial & Benign Inputs
# ==========================================
def test_adversarial_empty_and_whitespace():
    engine = RiskEngine()
    res = engine.evaluate("   \n\t  ")
    assert res.risk_level == "LOW"
    assert res.threat_detected is False


def test_adversarial_punctuated_and_encoded_urls():
    engine = RiskEngine()
    res = engine.evaluate(
        "Check link: (https://solwin.ai/path?arg=1&token=xyz), "
        "and email: <support@solwin.ai>."
    )
    assert res.threat_detected is False
    assert res.risk_level == "LOW"


# ==========================================
# 7. Security API Endpoint Tests
# ==========================================
@pytest.fixture
def mock_db():
    session = MagicMock()
    return session


@pytest.fixture
def override_db(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_direct_security_analyze():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/security/analyze",
            json={
                "message": (
                    "URGENT! Your account is blocked. Verify at "
                    "https://paypa1-security.example/login and share OTP."
                ),
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["threat_detected"] is True
    assert data["threat_type"] == "PHISHING"
    assert data["social_engineering_detected"] is True
    assert "OTP_REQUEST" in data["techniques"]
    assert len(data["suspicious_urls"]) == 1


@pytest.mark.asyncio
async def test_api_conversation_security_analyze_success(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id,
        conversation_reference="CONV-000001",
        subject="Urgent Security Alert",
        created_at=now,
        updated_at=now,
    )
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content="Please verify credentials at https://micros0ft-login.com",
        created_at=now,
    )
    conv.messages = [msg]

    override_db.scalar.side_effect = [conv, None]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/security/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == str(conv_id)
    assert data["threat"]["threat_detected"] is True
    assert override_db.add.called
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_api_conversation_security_not_found(override_db):
    conv_id = uuid.uuid4()
    override_db.scalar.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/security/conversation/{conv_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_get_security_success(override_db):
    conv_id = uuid.uuid4()
    threat_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    conv = Conversation(id=conv_id, created_at=now, updated_at=now)
    threat = Threat(
        id=threat_id,
        conversation_id=conv_id,
        threat_detected=True,
        threat_type="PHISHING",
        social_engineering_detected=True,
        techniques=["CREDENTIAL_HARVESTING"],
        risk_level="HIGH",
        suspicious_urls=["https://paypa1.com"],
        suspicious_emails=[],
        risk_reasons=["Lookalike brand domain"],
        recommended_action="Escalate for security review.",
        created_at=now,
        updated_at=now,
    )

    override_db.scalar.side_effect = [conv, threat]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/security/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == str(conv_id)
    assert data["threat"]["id"] == str(threat_id)
    assert data["threat"]["threat_type"] == "PHISHING"


@pytest.mark.asyncio
async def test_api_get_security_none_exists(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(id=conv_id, created_at=now, updated_at=now)

    override_db.scalar.side_effect = [conv, None]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/security/conversation/{conv_id}")

    assert response.status_code == 404
    assert "no security analysis found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reanalysis_threat_updates_existing(override_db):
    conv_id = uuid.uuid4()
    threat_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    conv = Conversation(id=conv_id, created_at=now, updated_at=now)
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content="Normal update message with no links.",
        created_at=now,
    )
    conv.messages = [msg]

    existing_threat = Threat(
        id=threat_id,
        conversation_id=conv_id,
        threat_detected=True,
        threat_type="PHISHING",
        risk_level="CRITICAL",
        created_at=now,
        updated_at=now,
    )

    override_db.scalar.side_effect = [conv, existing_threat]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/security/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["threat"]["id"] == str(threat_id)
    assert existing_threat.risk_level == "LOW"
    assert override_db.commit.called
