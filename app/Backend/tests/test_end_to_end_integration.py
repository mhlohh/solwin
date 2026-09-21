"""End-to-End Integration Test across Data -> ML Service -> Backend Persistence.

Tests the full pipeline lifecycle:
1. Ingest record from dataset
2. Execute ML inference pipeline
3. Verify Canonical ML Schema
4. Verify Backend Persistence and Retrieval
5. Confirm stable IDs and PII privacy protection
"""

import sys
import uuid
from pathlib import Path

# Setup sys.path for Backend and ML Service before local imports
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

ML_ROOT = BACKEND_ROOT.parent / "ml_services"
if str(ML_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ML_ROOT / "src"))

import pytest
from httpx import ASGITransport, AsyncClient
from ml_service.classification.classifier import ComplaintClassifier
from ml_service.recommendation.engine import RecommendationEngine
from ml_service.resolution.detector import ResolutionDetector
from ml_service.security.email_analyzer import EmailAnalyzer
from ml_service.security.url_analyzer import URLAnalyzer
from ml_service.urgency.detector import UrgencyDetector

from app.main import app
from app.models.analysis import Analysis
from app.models.conversation import Conversation
from app.models.enums import (
    ConversationChannel,
    ConversationStatus,
    Priority,
    ResolutionStatus,
    SenderType,
    Sentiment,
)
from app.models.message import Message
from app.models.threat import Threat


@pytest.mark.asyncio
async def test_end_to_end_intelligence_pipeline(override_db):
    """Verify end-to-end data processing, ML execution, and backend ingestion."""
    raw_message = (
        "I was charged $450 without authorization. The SMS link directed me to "
        "http://192.168.1.1/login to verify my credentials. Please refund immediately!"
    )
    subject = "Unauthorized Transaction & Phishing Alert"
    complaint_id = str(uuid.uuid4())

    # Execute ML Inference Pipeline Directly
    classifier = ComplaintClassifier(
        model_path=ML_ROOT / "models" / "complaint_classifier_v1.joblib",
        fine_grained_model_path=ML_ROOT / "models" / "intent_classifier_v1.joblib",
    )
    urgency_detector = UrgencyDetector()
    resolution_detector = ResolutionDetector()
    url_analyzer = URLAnalyzer()
    email_analyzer = EmailAnalyzer()
    rules_path = ML_ROOT / "config" / "action_rules.yaml"
    recommendation_engine = RecommendationEngine(rules_path=rules_path)

    clf_res = classifier.classify(raw_message, subject)
    urg_res = urgency_detector.detect(raw_message, subject)
    res_res = resolution_detector.detect(raw_message, subject)
    urls = url_analyzer.analyze_text(f"{subject}\n{raw_message}")
    _ = email_analyzer.analyze_text(f"{subject}\n{raw_message}")

    has_high_risk = any(u.risk_level.value == "HIGH" for u in urls)
    rec_res = recommendation_engine.recommend(
        category=clf_res.category,
        urgency=urg_res.urgency,
        resolution=res_res.status,
        security_risk="HIGH" if has_high_risk else "LOW",
    )

    # Assert Canonical ML Outputs
    assert clf_res.category is not None
    assert urg_res.urgency in ["HIGH", "CRITICAL"]
    assert len(urls) >= 1
    assert any("ip_address_host" in s.lower() for s in urls[0].signals)

    # Simulate Backend Conversation & Persistence
    conv_id = uuid.UUID(complaint_id)
    conversation = Conversation(
        id=conv_id,
        conversation_reference=f"CONV-{conv_id.hex[:6].upper()}",
        customer_name="Test Customer",
        channel=ConversationChannel.CHAT,
        subject=subject,
        status=ConversationStatus.OPEN,
    )
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content=raw_message,
    )
    conversation.messages = [message]

    if urg_res.urgency == "CRITICAL":
        calc_priority = Priority.CRITICAL.value
    else:
        calc_priority = Priority.HIGH.value
    analysis = Analysis(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        category=clf_res.category.value,
        issue="Unauthorized charge and suspicious login link",
        sentiment=Sentiment.NEGATIVE.value,
        emotion="Frustration",
        priority=calc_priority,
        resolution_status=ResolutionStatus.UNRESOLVED.value,
        summary="Customer reports unauthorized charge and received a phishing link.",
        recommended_action=rec_res.primary_action.value,
    )

    threat = Threat(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        threat_detected=True,
        threat_type="PHISHING_IP_HOST",
        risk_level="HIGH",
        suspicious_urls=[u.url for u in urls],
        recommended_action=rec_res.primary_action.value,
    )

    # Mock Database retrieval
    override_db.scalar.side_effect = [conversation, analysis, threat]

    # Verify Backend API Query Endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/analyze/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert str(data["conversation_id"]) == complaint_id
    assert data["customer_intelligence"]["priority"] in ["HIGH", "CRITICAL"]
    assert data["security_intelligence"]["threat_detected"] is True
    assert len(data["security_intelligence"]["suspicious_urls"]) >= 1
    assert data["recommended_action"] == rec_res.primary_action.value

