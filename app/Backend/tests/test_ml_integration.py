import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.enums import ComplaintCategory, Priority, ResolutionStatus, SenderType
from app.models.message import Message
from app.services.ai.customer_intelligence import (
    CustomerIntelligenceError,
    CustomerIntelligenceService,
)
from app.services.ml.adapter import (
    derive_sentiment_and_emotion,
    map_ml_category,
    map_ml_resolution,
    map_ml_urgency,
)
from app.services.ml.client import (
    MLClassificationResponse,
    MLClient,
    MLResolutionResponse,
    MLServiceError,
    MLUrgencyResponse,
)
from app.services.security.risk_engine import RiskEngine
from app.services.unified_intelligence import UnifiedIntelligenceService


# ==========================================
# 1. CORS Configuration Tests
# ==========================================
@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/conversations",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:5173"
        )
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_disallowed_origin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/conversations",
            headers={
                "Origin": "http://malicious-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Malicious origin must not receive Access-Control-Allow-Origin
        assert "access-control-allow-origin" not in response.headers


# ==========================================
# 2. ML Client Unit Tests (Mocked)
# ==========================================
def test_ml_client_successful_response():
    client = MLClient(base_url="http://mock-ml:8001")

    with patch("httpx.Client.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "category": "DELIVERY_SHIPPING_PROBLEM",
            "confidence": 0.89,
            "probabilities": {"DELIVERY_SHIPPING_PROBLEM": 0.89},
            "needs_review": False,
            "model_name": "complaint-classifier",
            "model_version": "1.0.0",
            "fine_grained_intent": "Delayed",
        }
        mock_post.return_value = mock_response

        res = client.classify_complaint(message="Where is my parcel?")
        assert res.category == "DELIVERY_SHIPPING_PROBLEM"
        assert res.confidence == 0.89
        assert res.fine_grained_intent == "Delayed"


def test_ml_client_connection_failure():
    import httpx

    client = MLClient(base_url="http://nonexistent:8001")

    with patch(
        "httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")
    ):
        with pytest.raises(MLServiceError) as exc_info:
            client.classify_complaint(message="Test message")
        assert exc_info.value.status_code == 503
        assert "Could not connect to ML service" in exc_info.value.message


def test_ml_client_timeout():
    import httpx

    client = MLClient(base_url="http://slow-ml:8001")

    with patch(
        "httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")
    ):
        with pytest.raises(MLServiceError) as exc_info:
            client.classify_complaint(message="Test message")
        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.message


def test_ml_client_invalid_response():
    client = MLClient(base_url="http://mock-ml:8001")

    with patch("httpx.Client.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid_key": 123}
        mock_post.return_value = mock_response

        with pytest.raises(MLServiceError) as exc_info:
            client.classify_complaint(message="Test message")
        assert exc_info.value.status_code == 502
        assert "Invalid response format" in exc_info.value.message


# ==========================================
# 3. Category & Output Mapping Tests
# ==========================================
def test_ml_category_mapping():
    # 11 ML categories mapped to 5 Solwin categories
    assert (
        map_ml_category("DELIVERY_SHIPPING_PROBLEM")
        == ComplaintCategory.SERVICE_REQUEST
    )
    assert map_ml_category("SERVICE_QUALITY") == ComplaintCategory.SERVICE_REQUEST
    assert (
        map_ml_category("PAYMENT_TRANSACTION_ISSUE")
        == ComplaintCategory.PAYMENT_BILLING
    )
    assert map_ml_category("REFUND_REQUEST") == ComplaintCategory.PAYMENT_BILLING
    assert map_ml_category("BILLING_PROBLEM") == ComplaintCategory.PAYMENT_BILLING
    assert map_ml_category("ACCOUNT_LOGIN_PROBLEM") == ComplaintCategory.ACCOUNT_ACCESS
    assert map_ml_category("SUBSCRIPTION_ISSUE") == ComplaintCategory.ACCOUNT_ACCESS
    assert map_ml_category("TECHNICAL_PROBLEM") == ComplaintCategory.TECHNICAL_ISSUE
    assert map_ml_category("PRODUCT_ISSUE") == ComplaintCategory.TECHNICAL_ISSUE
    assert map_ml_category("SECURITY_CONCERN") == ComplaintCategory.OTHER
    assert map_ml_category("OTHER") == ComplaintCategory.OTHER
    assert map_ml_category("UNKNOWN_CATEGORY") == ComplaintCategory.OTHER


def test_ml_urgency_and_resolution_mapping():
    assert map_ml_urgency("CRITICAL") == Priority.CRITICAL
    assert map_ml_urgency("HIGH") == Priority.HIGH
    assert map_ml_urgency("MEDIUM") == Priority.MEDIUM
    assert map_ml_urgency("LOW") == Priority.LOW

    assert map_ml_resolution("RESOLVED") == ResolutionStatus.RESOLVED
    assert map_ml_resolution("PARTIALLY_RESOLVED") == ResolutionStatus.IN_PROGRESS
    assert map_ml_resolution("UNRESOLVED") == ResolutionStatus.UNRESOLVED


def test_derive_sentiment_and_emotion():
    sent, emo = derive_sentiment_and_emotion(
        category=ComplaintCategory.SERVICE_REQUEST,
        priority=Priority.HIGH,
        is_resolved=False,
    )
    assert sent.value == "NEGATIVE"
    assert emo == "Frustration"

    sent_res, emo_res = derive_sentiment_and_emotion(
        category=ComplaintCategory.SERVICE_REQUEST,
        priority=Priority.LOW,
        is_resolved=True,
    )
    assert sent_res.value == "POSITIVE"
    assert emo_res == "Satisfaction"


# ==========================================
# 4. Customer Intelligence with ML Service
# ==========================================
def test_customer_intelligence_using_ml_service():
    mock_ml_client = MagicMock()
    mock_ml_client.classify_complaint.return_value = MLClassificationResponse(
        category="DELIVERY_SHIPPING_PROBLEM",
        confidence=0.92,
        probabilities={"DELIVERY_SHIPPING_PROBLEM": 0.92},
        needs_review=False,
        model_name="complaint-classifier",
        model_version="1.0.0",
        fine_grained_intent="Delayed",
    )
    mock_ml_client.detect_urgency.return_value = MLUrgencyResponse(
        urgency="HIGH",
        confidence=0.85,
        signals=["time_critical"],
        reasons=["Customer parcel delayed"],
    )
    mock_ml_client.detect_resolution.return_value = MLResolutionResponse(
        status="UNRESOLVED",
        confidence=0.9,
        signals=["not_arrived"],
        pending_items=["parcel tracking"],
    )

    service = CustomerIntelligenceService(
        provider="ml",
        ml_client=mock_ml_client,
    )

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        sender_type=SenderType.CUSTOMER,
        content="My parcel has been delayed for 4 days! Please help.",
    )

    output = service.analyze_conversation([msg], subject="Delivery Inquiry")

    assert output.category == ComplaintCategory.SERVICE_REQUEST
    assert output.priority == Priority.HIGH
    assert output.resolution_status == ResolutionStatus.UNRESOLVED
    assert "Delayed" in output.issue
    assert "DELIVERY_SHIPPING_PROBLEM" in output.summary


def test_customer_intelligence_ml_failure_raises_error():
    mock_ml_client = MagicMock()
    mock_ml_client.classify_complaint.side_effect = MLServiceError(
        "Could not connect to ML service", status_code=503
    )

    service = CustomerIntelligenceService(
        provider="ml",
        ml_client=mock_ml_client,
    )

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        sender_type=SenderType.CUSTOMER,
        content="Testing error handling",
    )

    with pytest.raises(CustomerIntelligenceError) as exc_info:
        service.analyze_conversation([msg])
    assert exc_info.value.status_code == 503


# ==========================================
# 5. Unified Analysis with ML Service & Security
# ==========================================
def test_unified_analysis_using_ml_service():
    mock_ml_client = MagicMock()
    mock_ml_client.classify_complaint.return_value = MLClassificationResponse(
        category="DELIVERY_SHIPPING_PROBLEM",
        confidence=0.95,
        fine_grained_intent="Delayed",
    )
    mock_ml_client.detect_urgency.return_value = MLUrgencyResponse(
        urgency="HIGH",
        confidence=0.8,
    )
    mock_ml_client.detect_resolution.return_value = MLResolutionResponse(
        status="UNRESOLVED",
        confidence=0.8,
    )

    # Patch CustomerIntelligenceService in unified_intelligence
    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService"
    ) as mock_cust_cls:
        instance = mock_cust_cls.return_value
        instance.analyze_conversation.return_value = CustomerIntelligenceService(
            provider="ml", ml_client=mock_ml_client
        ).analyze_conversation(
            [
                Message(
                    id=uuid.uuid4(),
                    conversation_id=uuid.uuid4(),
                    sender_type=SenderType.CUSTOMER,
                    content="My parcel is very delayed!",
                )
            ]
        )

        resp = UnifiedIntelligenceService.analyze_direct_message(
            message_text="My parcel is very delayed!"
        )

        assert resp.customer_intelligence.category == "SERVICE_REQUEST"
        assert resp.customer_intelligence.priority == "HIGH"
        assert resp.security_intelligence.risk_level == "LOW"
        assert "high priority customer issue" in resp.recommended_action.lower()


def test_security_risk_engine_works_independently():
    # Security RiskEngine evaluates deterministic indicators independently of ML
    engine = RiskEngine()
    phishing_text = (
        "URGENT: Your account is suspended. Verify password at "
        "http://paypa1-security.com/login"
    )
    res = engine.evaluate(text=phishing_text)
    assert res.threat_detected is True
    assert res.risk_level == "CRITICAL"
    assert "CREDENTIAL_HARVESTING" in res.techniques
    assert "URGENCY" in res.techniques


def test_phishing_does_not_override_security_with_ml():
    # Security RiskEngine remains authoritative even with customer ML classification
    mock_ml_client = MagicMock()
    mock_ml_client.classify_complaint.return_value = MLClassificationResponse(
        category="ACCOUNT_LOGIN_PROBLEM",
        confidence=0.90,
        fine_grained_intent="Login Issue",
    )
    mock_ml_client.detect_urgency.return_value = MLUrgencyResponse(urgency="CRITICAL")
    mock_ml_client.detect_resolution.return_value = MLResolutionResponse(
        status="UNRESOLVED"
    )

    phishing_msg = (
        "URGENT! Microsoft Security: Verify your password at "
        "https://paypa1-security.example/login and share OTP."
    )

    with patch(
        "app.services.unified_intelligence.CustomerIntelligenceService"
    ) as mock_cust_cls:
        instance = mock_cust_cls.return_value
        instance.analyze_conversation.return_value = CustomerIntelligenceService(
            provider="ml", ml_client=mock_ml_client
        ).analyze_conversation(
            [
                Message(
                    id=uuid.uuid4(),
                    conversation_id=uuid.uuid4(),
                    sender_type=SenderType.CUSTOMER,
                    content=phishing_msg,
                )
            ]
        )

        resp = UnifiedIntelligenceService.analyze_direct_message(
            message_text=phishing_msg
        )

        # Customer intelligence identified account login
        assert resp.customer_intelligence.category == "ACCOUNT_ACCESS"
        # Authoritative security intelligence identified critical threat
        assert resp.security_intelligence.threat_detected is True
        assert resp.security_intelligence.risk_level == "CRITICAL"
        assert resp.security_intelligence.threat_type == "PHISHING"
        assert "CREDENTIAL_HARVESTING" in resp.security_intelligence.techniques
        assert (
            "escalate immediately to the security team"
            in resp.recommended_action.lower()
        )
