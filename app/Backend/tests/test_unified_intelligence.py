import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.analysis import Analysis
from app.models.conversation import Conversation
from app.models.enums import (
    ComplaintCategory,
    Priority,
    ResolutionStatus,
    SenderType,
    Sentiment,
)
from app.models.message import Message
from app.models.threat import Threat
from app.schemas.analysis import CustomerIntelligenceOutput
from app.services.ai.customer_intelligence import CustomerIntelligenceError
from app.services.unified_intelligence import UnifiedIntelligenceService


# ==========================================
# 1. Pipeline Unit Tests (Mocks)
# ==========================================
def test_determine_final_action_normal_support():
    cust = MagicMock(priority=Priority.LOW)
    sec = MagicMock(risk_level="LOW")
    action = UnifiedIntelligenceService.determine_final_action(cust, sec)
    assert "normal support handling" in action.lower()


def test_determine_final_action_high_customer_priority_no_security():
    cust = MagicMock(priority=Priority.HIGH)
    sec = MagicMock(risk_level="LOW")
    action = UnifiedIntelligenceService.determine_final_action(cust, sec)
    assert "high priority customer issue" in action.lower()
    assert "no security threat" in action.lower()


def test_determine_final_action_critical_customer_priority_no_security():
    cust = MagicMock(priority=Priority.CRITICAL)
    sec = MagicMock(risk_level="LOW")
    action = UnifiedIntelligenceService.determine_final_action(cust, sec)
    assert "critical customer urgency" in action.lower()
    assert "senior support or engineering" in action.lower()


def test_determine_final_action_security_medium():
    cust = MagicMock(priority=Priority.LOW)
    sec = MagicMock(risk_level="MEDIUM")
    action = UnifiedIntelligenceService.determine_final_action(cust, sec)
    assert "verify sender identity" in action.lower()


def test_determine_final_action_security_high():
    cust = MagicMock(priority=Priority.LOW)
    sec = MagicMock(risk_level="HIGH")
    action = UnifiedIntelligenceService.determine_final_action(cust, sec)
    assert "escalate for security review" in action.lower()


def test_determine_final_action_security_critical():
    cust = MagicMock(priority=Priority.LOW)
    sec = MagicMock(risk_level="CRITICAL")
    action = UnifiedIntelligenceService.determine_final_action(cust, sec)
    assert "escalate immediately to the security team" in action.lower()
    assert "do not click links" in action.lower()


# ==========================================
# 2. Database & API Fixtures
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


# ==========================================
# 3. API Integration Tests
# ==========================================
@pytest.mark.asyncio
async def test_api_unified_normal_complaint(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id, subject="Refund Request", created_at=now, updated_at=now
    )
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content="I was charged twice and need a refund for the second transaction.",
        created_at=now,
    )
    conv.messages = [msg]

    # Mock DB: get_conversation_detail -> conv,
    # get_latest_analysis -> None, get_latest_threat -> None
    override_db.scalar.side_effect = [conv, None, None]

    mock_cust_output = CustomerIntelligenceOutput(
        category=ComplaintCategory.PAYMENT_BILLING,
        issue="Duplicate card charge requiring reversal",
        sentiment=Sentiment.NEGATIVE,
        emotion="Frustration",
        priority=Priority.HIGH,
        resolution_status=ResolutionStatus.UNRESOLVED,
        summary="Customer was charged twice and requests a refund.",
    )

    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation",
        return_value=mock_cust_output,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"conversation_id": str(conv_id)},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == str(conv_id)
    assert data["customer_intelligence"]["category"] == "PAYMENT_BILLING"
    assert data["customer_intelligence"]["priority"] == "HIGH"
    assert data["security_intelligence"]["risk_level"] == "LOW"
    assert data["security_intelligence"]["threat_detected"] is False
    assert "high priority customer issue" in data["recommended_action"].lower()
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_api_unified_phishing_message(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id,
        subject="Urgent Account Verification",
        created_at=now,
        updated_at=now,
    )
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content=(
            "URGENT! Microsoft Security: Verify your password at "
            "https://paypa1-security.example/login and share OTP."
        ),
        created_at=now,
    )
    conv.messages = [msg]

    override_db.scalar.side_effect = [conv, None, None]

    mock_cust_output = CustomerIntelligenceOutput(
        category=ComplaintCategory.ACCOUNT_ACCESS,
        issue="Account verification request with credentials",
        sentiment=Sentiment.NEGATIVE,
        emotion="Urgency",
        priority=Priority.HIGH,
        resolution_status=ResolutionStatus.UNRESOLVED,
        summary="Sender requesting urgent credential validation.",
    )

    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation",
        return_value=mock_cust_output,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"conversation_id": str(conv_id)},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["security_intelligence"]["threat_detected"] is True
    assert data["security_intelligence"]["threat_type"] == "PHISHING"
    assert data["security_intelligence"]["risk_level"] == "CRITICAL"
    assert "CREDENTIAL_HARVESTING" in data["security_intelligence"]["techniques"]
    assert "OTP_REQUEST" in data["security_intelligence"]["techniques"]
    assert (
        "escalate immediately to the security team"
        in data["recommended_action"].lower()
    )


@pytest.mark.asyncio
async def test_api_unified_independent_priority_and_risk(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(id=conv_id, created_at=now, updated_at=now)
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content="Our primary billing checkout is broken across the entire platform!",
        created_at=now,
    )
    conv.messages = [msg]

    override_db.scalar.side_effect = [conv, None, None]

    mock_cust_output = CustomerIntelligenceOutput(
        category=ComplaintCategory.TECHNICAL_ISSUE,
        issue="Platform-wide billing gateway outage",
        sentiment=Sentiment.NEGATIVE,
        emotion="Frustration",
        priority=Priority.CRITICAL,
        resolution_status=ResolutionStatus.UNRESOLVED,
        summary="Customer reports platform checkout outage.",
    )

    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation",
        return_value=mock_cust_output,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"conversation_id": str(conv_id)},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["customer_intelligence"]["priority"] == "CRITICAL"
    assert data["security_intelligence"]["risk_level"] == "LOW"
    assert data["security_intelligence"]["threat_detected"] is False
    assert "senior support or engineering" in data["recommended_action"].lower()


@pytest.mark.asyncio
async def test_api_unified_empty_conversation(override_db):
    conv_id = uuid.uuid4()
    conv = Conversation(id=conv_id)
    conv.messages = []
    override_db.scalar.return_value = conv

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/analyze",
            json={"conversation_id": str(conv_id)},
        )

    assert response.status_code == 400
    assert "empty conversation" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_unified_conversation_not_found(override_db):
    conv_id = uuid.uuid4()
    override_db.scalar.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/analyze",
            json={"conversation_id": str(conv_id)},
        )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_unified_reanalysis_updates_existing(override_db):
    conv_id = uuid.uuid4()
    analysis_id = uuid.uuid4()
    threat_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    conv = Conversation(id=conv_id, created_at=now, updated_at=now)
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content="Update: our technical issue is now resolved, thank you.",
        created_at=now,
    )
    conv.messages = [msg]

    existing_analysis = Analysis(
        id=analysis_id, conversation_id=conv_id, created_at=now, updated_at=now
    )
    existing_threat = Threat(
        id=threat_id, conversation_id=conv_id, created_at=now, updated_at=now
    )

    # 1. get_conversation_detail -> conv
    # 2. save_or_update_analysis -> get_latest_analysis -> existing_analysis
    # 3. save_or_update_threat -> get_latest_threat -> existing_threat
    override_db.scalar.side_effect = [conv, existing_analysis, existing_threat]

    mock_cust_output = CustomerIntelligenceOutput(
        category=ComplaintCategory.TECHNICAL_ISSUE,
        issue="Resolved issue",
        sentiment=Sentiment.POSITIVE,
        emotion="Satisfaction",
        priority=Priority.LOW,
        resolution_status=ResolutionStatus.RESOLVED,
        summary="Customer resolved issue.",
    )

    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation",
        return_value=mock_cust_output,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"conversation_id": str(conv_id)},
            )

    assert response.status_code == 200
    assert existing_analysis.resolution_status == "RESOLVED"
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_api_get_unified_analysis_success(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(id=conv_id, created_at=now, updated_at=now)
    analysis = Analysis(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        category="ACCOUNT_ACCESS",
        issue="MFA Reset",
        sentiment="NEUTRAL",
        emotion="Neutral",
        priority="HIGH",
        resolution_status="IN_PROGRESS",
        summary="Customer requests MFA reset.",
        recommended_action="Expedite support response and resolution.",
        created_at=now,
        updated_at=now,
    )
    threat = Threat(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        threat_detected=False,
        threat_type="NONE",
        risk_level="LOW",
        recommended_action="Expedite support response and resolution.",
        created_at=now,
        updated_at=now,
    )

    # get_conversation_detail, get_latest_analysis, get_latest_threat
    override_db.scalar.side_effect = [conv, analysis, threat]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/analyze/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == str(conv_id)
    assert data["customer_intelligence"]["category"] == "ACCOUNT_ACCESS"
    assert data["security_intelligence"]["risk_level"] == "LOW"


@pytest.mark.asyncio
async def test_api_get_unified_analysis_none_exists(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(id=conv_id, created_at=now, updated_at=now)

    override_db.scalar.side_effect = [conv, None, None]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/analyze/conversation/{conv_id}")

    assert response.status_code == 404
    assert "no analysis found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_unified_gemini_failure(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(id=conv_id, created_at=now, updated_at=now)
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content="Testing AI failure handling.",
        created_at=now,
    )
    conv.messages = [msg]

    override_db.scalar.return_value = conv

    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation",
        side_effect=CustomerIntelligenceError(
            "Gemini API quota exceeded.", status_code=503
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"conversation_id": str(conv_id)},
            )

    assert response.status_code == 503
    assert "quota exceeded" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_direct_message_unified():
    mock_cust_output = CustomerIntelligenceOutput(
        category=ComplaintCategory.ACCOUNT_ACCESS,
        issue="Urgent password reset",
        sentiment=Sentiment.NEGATIVE,
        emotion="Anxiety",
        priority=Priority.HIGH,
        resolution_status=ResolutionStatus.UNRESOLVED,
        summary="Direct customer needs password reset immediately.",
    )

    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation",
        return_value=mock_cust_output,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze/message",
                json={
                    "message": (
                        "URGENT! Enter your password at "
                        "https://paypa1-security.example/login to verify your account!"
                    ),
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] is None
    assert data["customer_intelligence"]["category"] == "ACCOUNT_ACCESS"
    assert data["security_intelligence"]["threat_detected"] is True
    assert data["security_intelligence"]["threat_type"] == "PHISHING"
    assert data["security_intelligence"]["risk_level"] == "CRITICAL"
    assert (
        "escalate immediately to the security team"
        in data["recommended_action"].lower()
    )
