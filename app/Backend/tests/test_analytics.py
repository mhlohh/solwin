import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.analysis import Analysis
from app.models.conversation import Conversation
from app.models.enums import ConversationChannel, ConversationStatus
from app.models.threat import Threat


@pytest.fixture
def test_db_session():
    """Create an isolated, lightweight in-memory SQLite database session."""
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
        SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def override_db(test_db_session):
    """Override FastAPI get_db dependency with test database session."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    yield test_db_session
    app.dependency_overrides.clear()


# ============================================================================
# 1. Empty Dashboard & Analytics
# ============================================================================


@pytest.mark.asyncio
async def test_empty_dashboard_overview(override_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["total_conversations"] == 0
    assert data["open_conversations"] == 0
    assert data["in_progress_conversations"] == 0
    assert data["resolved_conversations"] == 0
    assert data["unresolved_conversations"] == 0
    assert data["urgent_conversations"] == 0
    assert data["threats_detected"] == 0
    assert data["critical_threats"] == 0
    assert data["sentiment_distribution"] == {}
    assert data["category_distribution"] == {}
    assert data["risk_distribution"] == {}


@pytest.mark.asyncio
async def test_empty_customer_analytics(override_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/customer")

    assert response.status_code == 200
    data = response.json()
    assert data["total_conversations"] == 0
    assert data["category_distribution"] == {}
    assert data["sentiment_distribution"] == {}
    assert data["priority_distribution"] == {}
    assert data["resolution_status_distribution"] == {}
    assert data["most_frequently_reported_issues"] == []
    assert data["unresolved_complaint_count"] == 0
    assert data["urgent_complaint_count"] == 0


@pytest.mark.asyncio
async def test_empty_security_analytics(override_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/security")

    assert response.status_code == 200
    data = response.json()
    assert data["total_threats"] == 0
    assert data["threats_detected"] == 0
    assert data["risk_distribution"] == {}
    assert data["threat_type_distribution"] == {}
    assert data["technique_frequency"] == {}
    assert data["suspicious_url_count"] == 0
    assert data["suspicious_email_count"] == 0
    assert data["recent_critical_threats"] == []


# ============================================================================
# 2. Overview Metrics with Real Seed Data
# ============================================================================


@pytest.mark.asyncio
async def test_dashboard_overview_metrics(override_db):
    now = datetime.now(timezone.utc)

    # Conversations: 2 OPEN, 1 IN_PROGRESS, 1 RESOLVED
    c1 = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-001",
        channel=ConversationChannel.CHAT,
        status=ConversationStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    c2 = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-002",
        channel=ConversationChannel.EMAIL,
        status=ConversationStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    c3 = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-003",
        channel=ConversationChannel.TICKET,
        status=ConversationStatus.IN_PROGRESS,
        created_at=now,
        updated_at=now,
    )
    c4 = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-004",
        channel=ConversationChannel.CHAT,
        status=ConversationStatus.RESOLVED,
        created_at=now,
        updated_at=now,
    )
    override_db.add_all([c1, c2, c3, c4])

    # Analyses: 1 High priority (urgent), 1 Medium priority
    a1 = Analysis(
        id=uuid.uuid4(),
        conversation_id=c1.id,
        category="ACCOUNT_ACCESS",
        issue="Password Reset Locked",
        sentiment="NEGATIVE",
        emotion="Frustration",
        priority="HIGH",
        resolution_status="UNRESOLVED",
        created_at=now,
        updated_at=now,
    )
    a2 = Analysis(
        id=uuid.uuid4(),
        conversation_id=c2.id,
        category="PAYMENT_BILLING",
        issue="Refund Request",
        sentiment="NEUTRAL",
        emotion="Neutral",
        priority="MEDIUM",
        resolution_status="IN_PROGRESS",
        created_at=now,
        updated_at=now,
    )
    override_db.add_all([a1, a2])

    # Threats: 1 Critical detected, 1 Low not detected
    t1 = Threat(
        id=uuid.uuid4(),
        conversation_id=c1.id,
        threat_detected=True,
        threat_type="PHISHING",
        risk_level="CRITICAL",
        created_at=now,
        updated_at=now,
    )
    t2 = Threat(
        id=uuid.uuid4(),
        conversation_id=c2.id,
        threat_detected=False,
        threat_type="NONE",
        risk_level="LOW",
        created_at=now,
        updated_at=now,
    )
    override_db.add_all([t1, t2])
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["total_conversations"] == 4
    assert data["open_conversations"] == 2
    assert data["in_progress_conversations"] == 1
    assert data["resolved_conversations"] == 1
    assert data["unresolved_conversations"] == 3
    assert data["urgent_conversations"] == 1
    assert data["threats_detected"] == 1
    assert data["critical_threats"] == 1
    assert data["sentiment_distribution"] == {"NEGATIVE": 1, "NEUTRAL": 1}
    assert data["category_distribution"] == {
        "ACCOUNT_ACCESS": 1,
        "PAYMENT_BILLING": 1,
    }
    assert data["risk_distribution"] == {"CRITICAL": 1, "LOW": 1}


# ============================================================================
# 3. Customer Analytics Distributions
# ============================================================================


@pytest.mark.asyncio
async def test_customer_analytics_distributions(override_db):
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-CUST-1",
        status=ConversationStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    override_db.add(conv)

    a1 = Analysis(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        category="TECHNICAL_ISSUE",
        issue="500 Gateway Timeout",
        sentiment="NEGATIVE",
        priority="CRITICAL",
        resolution_status="UNRESOLVED",
        created_at=now,
        updated_at=now,
    )
    override_db.add(a1)
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/customer")

    assert response.status_code == 200
    data = response.json()
    assert data["total_conversations"] == 1
    assert data["category_distribution"] == {"TECHNICAL_ISSUE": 1}
    assert data["sentiment_distribution"] == {"NEGATIVE": 1}
    assert data["priority_distribution"] == {"CRITICAL": 1}
    assert data["resolution_status_distribution"] == {"UNRESOLVED": 1}
    assert len(data["most_frequently_reported_issues"]) == 1
    assert data["most_frequently_reported_issues"][0]["issue"] == "500 Gateway Timeout"
    assert data["most_frequently_reported_issues"][0]["count"] == 1
    assert data["unresolved_complaint_count"] == 1
    assert data["urgent_complaint_count"] == 1


# ============================================================================
# 4. Security Analytics & JSON Techniques Frequency
# ============================================================================


@pytest.mark.asyncio
async def test_security_analytics_with_techniques_and_links(override_db):
    now = datetime.now(timezone.utc)
    t = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="PHISHING",
        risk_level="CRITICAL",
        social_engineering_detected=True,
        techniques=["CREDENTIAL_HARVESTING", "URGENCY"],
        suspicious_urls=["https://phish1.com", "https://phish2.com"],
        suspicious_emails=["attacker@bad.org"],
        risk_reasons=["Lookalike domain"],
        created_at=now,
        updated_at=now,
    )
    override_db.add(t)
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/security")

    assert response.status_code == 200
    data = response.json()
    assert data["total_threats"] == 1
    assert data["threats_detected"] == 1
    assert data["risk_distribution"] == {"CRITICAL": 1}
    assert data["threat_type_distribution"] == {"PHISHING": 1}
    assert data["technique_frequency"] == {
        "CREDENTIAL_HARVESTING": 1,
        "URGENCY": 1,
    }
    assert data["suspicious_url_count"] == 2
    assert data["suspicious_email_count"] == 1
    assert len(data["recent_critical_threats"]) == 1
    assert data["recent_critical_threats"][0]["threat_type"] == "PHISHING"
    assert data["recent_critical_threats"][0]["risk_level"] == "CRITICAL"


# ============================================================================
# 5. Top Issues Endpoint
# ============================================================================


@pytest.mark.asyncio
async def test_get_top_issues(override_db):
    now = datetime.now(timezone.utc)
    c = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-TOP-1",
        created_at=now,
        updated_at=now,
    )
    override_db.add(c)

    # Add 2 analyses with "Duplicate billing" and 1 with "Login loop"
    a1 = Analysis(
        id=uuid.uuid4(),
        conversation_id=c.id,
        issue="Duplicate billing",
        created_at=now,
        updated_at=now,
    )
    a2 = Analysis(
        id=uuid.uuid4(),
        conversation_id=c.id,
        issue="Duplicate billing",
        created_at=now,
        updated_at=now,
    )
    a3 = Analysis(
        id=uuid.uuid4(),
        conversation_id=c.id,
        issue="Login loop",
        created_at=now,
        updated_at=now,
    )
    override_db.add_all([a1, a2, a3])
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/customer/top-issues?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["issue"] == "Duplicate billing"
    assert data[0]["count"] == 2
    assert data[1]["issue"] == "Login loop"
    assert data[1]["count"] == 1


# ============================================================================
# 6. Recent Threats Endpoint
# ============================================================================


@pytest.mark.asyncio
async def test_get_recent_threats(override_db):
    now = datetime.now(timezone.utc)
    t = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="SOCIAL_ENGINEERING",
        risk_level="HIGH",
        risk_reasons=["Impersonating Helpdesk"],
        created_at=now,
        updated_at=now,
    )
    override_db.add(t)
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/security/recent-threats?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["threat_type"] == "SOCIAL_ENGINEERING"
    assert data[0]["risk_level"] == "HIGH"
    assert "Impersonating Helpdesk" in data[0]["risk_reasons"]


# ============================================================================
# 7. Customer & Security Trends & Parameter Validation
# ============================================================================


@pytest.mark.asyncio
async def test_customer_trends_success(override_db):
    now = datetime.now(timezone.utc)
    c = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-TREND-1",
        created_at=now,
        updated_at=now,
    )
    override_db.add(c)
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/customer/trends?days=7")

    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert data["total_count"] == 1
    assert len(data["trends"]) == 1
    assert data["trends"][0]["count"] == 1


@pytest.mark.asyncio
async def test_security_trends_success(override_db):
    now = datetime.now(timezone.utc)
    t = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        risk_level="CRITICAL",
        created_at=now,
        updated_at=now,
    )
    override_db.add(t)
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/security/trends?days=14")

    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 14
    assert data["total_count"] == 1
    assert len(data["trends"]) == 1
    assert data["trends"][0]["count"] == 1


@pytest.mark.asyncio
async def test_trends_invalid_days_rejection(override_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # days < 1
        resp_zero = await client.get("/api/v1/analytics/customer/trends?days=0")
        assert resp_zero.status_code == 422

        # days > 90
        resp_large = await client.get("/api/v1/analytics/security/trends?days=365")
        assert resp_large.status_code == 422


# ============================================================================
# 8. Independence of Priority and Risk
# ============================================================================


@pytest.mark.asyncio
async def test_priority_and_risk_independent_in_analytics(override_db):
    now = datetime.now(timezone.utc)
    c1 = Conversation(
        id=uuid.uuid4(),
        conversation_reference="CONV-INDEP-1",
        created_at=now,
        updated_at=now,
    )
    override_db.add(c1)

    # HIGH customer priority, LOW security risk
    a1 = Analysis(
        id=uuid.uuid4(),
        conversation_id=c1.id,
        priority="HIGH",
        created_at=now,
        updated_at=now,
    )
    t1 = Threat(
        id=uuid.uuid4(),
        conversation_id=c1.id,
        threat_detected=False,
        risk_level="LOW",
        created_at=now,
        updated_at=now,
    )
    override_db.add_all([a1, t1])
    override_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/dashboard/overview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["urgent_conversations"] == 1
    assert data["threats_detected"] == 0
    assert data["risk_distribution"] == {"LOW": 1}


# ============================================================================
# 9. Verification that Analytics Does NOT Invoke AI or Security Engines
# ============================================================================


@pytest.mark.asyncio
async def test_analytics_endpoints_do_not_invoke_ai_or_security(override_db):
    with (
        patch(
            "app.services.ai.customer_intelligence.CustomerIntelligenceService.analyze_conversation"
        ) as mock_ai,
        patch("app.services.security.risk_engine.RiskEngine.evaluate") as mock_sec,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/v1/dashboard/overview")
            await client.get("/api/v1/analytics/customer")
            await client.get("/api/v1/analytics/security")
            await client.get("/api/v1/analytics/customer/trends")
            await client.get("/api/v1/analytics/security/trends")
            await client.get("/api/v1/analytics/customer/top-issues")
            await client.get("/api/v1/analytics/security/recent-threats")

        assert not mock_ai.called
        assert not mock_sec.called


# ============================================================================
# 10. Ingested feedback dataset stats (Data API bridge)
# ============================================================================


@pytest.mark.asyncio
async def test_dashboard_overview_merges_ingested_feedback_stats(override_db):
    """Stats from the Data API are surfaced under ingested_feedback."""
    fake = {
        "total_records": 20862,
        "phishing_flagged": 100,
        "priority_counts": {"CRITICAL": 126, "HIGH": 1020, "MEDIUM": 2356, "LOW": 17360},
        "top_intents": [
            {"issue": "General Enquiry", "count": 900},
            {"issue": "Damaged", "count": 700},
        ],
    }
    with patch(
        "app.services.analytics_service.get_ingested_feedback_stats",
        return_value=fake,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["ingested_feedback"]["total_records"] == 20862
    assert data["ingested_feedback"]["phishing_flagged"] == 100
    assert data["ingested_feedback"]["priority_counts"]["CRITICAL"] == 126
    assert data["ingested_feedback"]["top_intents"][0]["issue"] == "General Enquiry"


@pytest.mark.asyncio
async def test_dashboard_overview_degrades_without_data_api(override_db):
    """When the Data API is unreachable, ingested_feedback is None and the
    dashboard still returns the full overview (graceful degradation)."""
    with patch(
        "app.services.analytics_service.get_ingested_feedback_stats",
        return_value=None,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["ingested_feedback"] is None
    assert "total_conversations" in data
    assert "urgent_conversations" in data
