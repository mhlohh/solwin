import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_active_user, get_current_user
from app.main import app
from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, RiskLevel, UserRole
from app.models.threat import Threat
from app.models.user import User
from app.schemas.campaign import (
    CampaignSummary,
)
from app.services.campaign.campaign_service import CampaignService
from app.services.campaign.correlation import (
    ThreatIndicators,
    calculate_threat_correlation,
    derive_campaign_risk,
)


# 1. Campaign model creation
def test_campaign_model_creation():
    now = datetime.now(timezone.utc)
    camp_id = uuid.uuid4()
    camp = Campaign(
        id=camp_id,
        name="PayPal Lookalike Activity Cluster",
        description="Correlated phishing incidents",
        risk_level=RiskLevel.HIGH,
        status=CampaignStatus.ACTIVE,
        correlation_score=80,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    assert camp.id == camp_id
    assert camp.name == "PayPal Lookalike Activity Cluster"
    assert camp.risk_level == RiskLevel.HIGH
    assert camp.status == CampaignStatus.ACTIVE
    assert camp.correlation_score == 80


# 2. Campaign schema validation
def test_campaign_schema_validation():
    now = datetime.now(timezone.utc)
    camp_id = uuid.uuid4()
    summary = CampaignSummary(
        id=camp_id,
        name="Billing Phishing Cluster",
        risk_level=RiskLevel.CRITICAL,
        status=CampaignStatus.ACTIVE,
        correlation_score=90,
        threat_count=3,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    assert summary.id == camp_id
    assert summary.threat_count == 3
    assert summary.risk_level == RiskLevel.CRITICAL


# 3. Exact URL correlation
def test_exact_url_correlation():
    t1 = ThreatIndicators(
        threat_id="1",
        urls=["https://paypa1-security.com/login"],
        threat_type="PHISHING",
    )
    t2 = ThreatIndicators(
        threat_id="2",
        urls=["https://paypa1-security.com/login"],
        threat_type="PHISHING",
    )
    res = calculate_threat_correlation(t1, t2)
    # URL (+50) + Domain (+40) + Same type (+10) = 100
    assert res.score >= 50
    assert "https://paypa1-security.com/login" in res.shared_urls


# 4. Exact domain correlation
def test_exact_domain_correlation():
    t1 = ThreatIndicators(
        threat_id="1",
        urls=["https://paypa1-security.com/page1"],
        domains=["paypa1-security.com"],
        threat_type="PHISHING",
    )
    t2 = ThreatIndicators(
        threat_id="2",
        urls=["https://paypa1-security.com/verify"],
        domains=["paypa1-security.com"],
        threat_type="PHISHING",
    )
    res = calculate_threat_correlation(t1, t2)
    assert "paypa1-security.com" in res.shared_domains
    assert res.score >= 40


# 5. Email domain correlation
def test_email_domain_correlation():
    t1 = ThreatIndicators(
        threat_id="1",
        emails=["billing@fake-bank.com"],
        email_domains=["fake-bank.com"],
        threat_type="PHISHING",
    )
    t2 = ThreatIndicators(
        threat_id="2",
        emails=["support@fake-bank.com"],
        email_domains=["fake-bank.com"],
        threat_type="PHISHING",
    )
    res = calculate_threat_correlation(t1, t2)
    assert "fake-bank.com" in res.shared_email_domains
    assert res.score >= 30


# 6. Shared technique contributes weak correlation
def test_shared_technique_contributes_weak_correlation():
    t1 = ThreatIndicators(
        threat_id="1",
        techniques=["URGENCY"],
    )
    t2 = ThreatIndicators(
        threat_id="2",
        techniques=["URGENCY"],
    )
    res = calculate_threat_correlation(t1, t2)
    # Only 10 points for generic technique
    assert res.score == 10


# 7. Shared threat type contributes weak correlation
def test_shared_threat_type_contributes_weak_correlation():
    t1 = ThreatIndicators(
        threat_id="1",
        threat_type="PHISHING",
    )
    t2 = ThreatIndicators(
        threat_id="2",
        threat_type="PHISHING",
    )
    res = calculate_threat_correlation(t1, t2)
    assert res.score == 10
    assert res.shared_threat_type is True


# 8. Generic similarity does not create campaign
def test_generic_similarity_does_not_create_campaign():
    t1 = ThreatIndicators(
        threat_id="1",
        threat_type="PHISHING",
        techniques=["URGENCY"],
    )
    t2 = ThreatIndicators(
        threat_id="2",
        threat_type="PHISHING",
        techniques=["URGENCY"],
    )
    res = calculate_threat_correlation(t1, t2)
    # Total score = 10 (type) + 10 (tech) = 20, strictly < 40 threshold
    assert res.score < 40


# 9. Single threat does not create campaign
def test_single_threat_does_not_create_campaign(override_db):
    threat = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="PHISHING",
        suspicious_urls=["https://lonely-threat.com/login"],
    )
    override_db.scalars.return_value.all.return_value = []
    override_db.scalar.return_value = None

    camp = CampaignService.correlate_threat(override_db, threat)
    assert camp is None


# 10. Two strongly related threats create campaign
def test_two_strongly_related_threats_create_campaign(override_db):
    now = datetime.now(timezone.utc)
    t1 = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="PHISHING",
        suspicious_urls=["https://paypa1-security.com/login"],
        risk_level="HIGH",
        created_at=now,
    )
    t2 = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="PHISHING",
        suspicious_urls=["https://paypa1-security.com/verify"],
        risk_level="HIGH",
        created_at=now,
    )
    override_db.scalars.return_value.all.return_value = [t1]
    override_db.scalar.return_value = None

    camp = CampaignService.correlate_threat(override_db, t2)
    assert camp is not None
    assert "Paypa1 Security" in camp.name or "Activity Cluster" in camp.name
    assert t1.campaign_id == camp.id
    assert t2.campaign_id == camp.id
    assert camp.correlation_score >= 40


# 11. Third related threat joins existing campaign
def test_third_related_threat_joins_existing_campaign(override_db):
    camp_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=camp_id,
        name="Paypa1 Activity Cluster",
        risk_level=RiskLevel.HIGH,
        status=CampaignStatus.ACTIVE,
        correlation_score=50,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    camp.threats = []

    t1 = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="PHISHING",
        suspicious_urls=["https://paypa1-security.com/login"],
        campaign_id=camp_id,
        risk_level="HIGH",
        created_at=now,
    )
    camp.threats.append(t1)

    t3 = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="PHISHING",
        suspicious_urls=["https://paypa1-security.com/billing"],
        risk_level="HIGH",
        created_at=now,
    )

    override_db.scalars.return_value.all.return_value = [t1]
    override_db.scalar.return_value = camp

    res_camp = CampaignService.correlate_threat(override_db, t3)
    assert res_camp.id == camp_id
    assert t3.campaign_id == camp_id


# 12. Correlation score bounded at 100
def test_correlation_score_bounded_at_100():
    t1 = ThreatIndicators(
        threat_id="1",
        urls=["https://evil.com/1", "https://evil.com/2"],
        domains=["evil.com"],
        emails=["admin@evil.com"],
        email_domains=["evil.com"],
        threat_type="PHISHING",
        techniques=["URGENCY", "CREDENTIAL_HARVESTING", "OTP_REQUEST"],
    )
    t2 = ThreatIndicators(
        threat_id="2",
        urls=["https://evil.com/1", "https://evil.com/2"],
        domains=["evil.com"],
        emails=["admin@evil.com"],
        email_domains=["evil.com"],
        threat_type="PHISHING",
        techniques=["URGENCY", "CREDENTIAL_HARVESTING", "OTP_REQUEST"],
    )
    res = calculate_threat_correlation(t1, t2)
    assert res.score == 100


# 13. Campaign risk derived correctly
def test_campaign_risk_derived_correctly():
    t_crit = Threat(risk_level="CRITICAL")
    t_high = Threat(risk_level="HIGH")
    t_med = Threat(risk_level="MEDIUM")
    t_low = Threat(risk_level="LOW")

    assert derive_campaign_risk([t_crit, t_low]) == RiskLevel.CRITICAL
    assert derive_campaign_risk([t_high, t_high]) == RiskLevel.CRITICAL
    assert derive_campaign_risk([t_high, t_low]) == RiskLevel.HIGH
    assert derive_campaign_risk([t_med, t_med]) == RiskLevel.MEDIUM
    assert derive_campaign_risk([t_low, t_low]) == RiskLevel.LOW


# 14. Campaign status update works
def test_campaign_status_update(override_db):
    camp_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=camp_id,
        name="Test Campaign",
        status=CampaignStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    override_db.scalar.return_value = camp

    updated = CampaignService.update_campaign_status(
        override_db, camp_id, CampaignStatus.RESOLVED
    )
    assert updated.status == CampaignStatus.RESOLVED


# 15. Unauthorized campaign access rejected
@pytest.mark.asyncio
async def test_unauthorized_campaign_access_rejected(override_db):
    user = User(
        id=uuid.uuid4(),
        email="agent@solwin.ai",
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/campaigns")
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_active_user, None)


# 16. Support Manager can read campaigns
@pytest.mark.asyncio
async def test_support_manager_can_read_campaigns(override_db):
    user = User(
        id=uuid.uuid4(),
        email="manager@solwin.ai",
        role=UserRole.SUPPORT_MANAGER,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user

    override_db.scalar.return_value = 0
    override_db.scalars.return_value.all.return_value = []

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/campaigns")
            assert res.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_active_user, None)


# 17. Security Analyst can manage campaigns
@pytest.mark.asyncio
async def test_security_analyst_can_manage_campaigns(override_db):
    user = User(
        id=uuid.uuid4(),
        email="sec@solwin.ai",
        role=UserRole.SECURITY_ANALYST,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user

    camp_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=camp_id,
        name="Phishing Wave",
        status=CampaignStatus.ACTIVE,
        risk_level=RiskLevel.HIGH,
        correlation_score=60,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    camp.threats = []
    override_db.scalar.return_value = camp

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.patch(
                f"/api/v1/campaigns/{camp_id}/status",
                json={"status": "MONITORED"},
            )
            assert res.status_code == 200
            assert res.json()["status"] == "MONITORED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_active_user, None)


# 18. Support Agent cannot manage campaigns
@pytest.mark.asyncio
async def test_support_agent_cannot_manage_campaigns(override_db):
    user = User(
        id=uuid.uuid4(),
        email="agent@solwin.ai",
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.patch(
                f"/api/v1/campaigns/{uuid.uuid4()}/status",
                json={"status": "RESOLVED"},
            )
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_active_user, None)


# 19. Admin can manage campaigns
@pytest.mark.asyncio
async def test_admin_can_manage_campaigns(override_db):
    camp_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=camp_id,
        name="Admin Managed Campaign",
        status=CampaignStatus.ACTIVE,
        risk_level=RiskLevel.CRITICAL,
        correlation_score=80,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    camp.threats = []
    override_db.scalar.return_value = camp

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.patch(
            f"/api/v1/campaigns/{camp_id}/status",
            json={"status": "RESOLVED"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "RESOLVED"


# 20. Campaign list pagination works
@pytest.mark.asyncio
async def test_campaign_list_pagination(override_db):
    camp_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=camp_id,
        name="Pagination Campaign",
        status=CampaignStatus.ACTIVE,
        risk_level=RiskLevel.MEDIUM,
        correlation_score=50,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    camp.threats = []

    override_db.scalar.return_value = 1
    override_db.scalars.return_value.all.return_value = [camp]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/campaigns?page=1&page_size=10")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1


# 21. Campaign filtering works
@pytest.mark.asyncio
async def test_campaign_filtering(override_db):
    override_db.scalar.return_value = 0
    override_db.scalars.return_value.all.return_value = []

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get(
            "/api/v1/campaigns?status=ACTIVE&risk_level=HIGH&search=PayPal"
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0


# 22. Campaign detail returns related threats
@pytest.mark.asyncio
async def test_campaign_detail_returns_related_threats(override_db):
    camp_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    threat_id = uuid.uuid4()
    threat = Threat(
        id=threat_id,
        threat_type="PHISHING",
        risk_level="HIGH",
        suspicious_urls=["https://fake-login.com"],
        suspicious_emails=["scam@fake-login.com"],
        techniques=["URGENCY"],
        created_at=now,
    )

    camp = Campaign(
        id=camp_id,
        name="Detail Campaign",
        status=CampaignStatus.ACTIVE,
        risk_level=RiskLevel.HIGH,
        correlation_score=75,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    camp.threats = [threat]

    override_db.scalar.return_value = camp

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get(f"/api/v1/campaigns/{camp_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(camp_id)
        assert len(data["threats"]) == 1
        assert data["threats"][0]["id"] == str(threat_id)
        assert "fake-login.com" in data["shared_indicators"]["domains"]


# 23. Radar summary works with empty database
@pytest.mark.asyncio
async def test_radar_summary_empty_database(override_db):
    override_db.scalar.side_effect = [0, 0, 0, 0]
    override_db.scalars.return_value.all.side_effect = [[], []]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/campaigns/radar")
        assert res.status_code == 200
        data = res.json()
        assert data["total_campaigns"] == 0
        assert data["active_campaigns"] == 0
        assert data["critical_campaigns"] == 0
        assert data["top_shared_domains"] == []


# 24. Radar summary works with populated data
@pytest.mark.asyncio
async def test_radar_summary_populated_data(override_db):
    now = datetime.now(timezone.utc)
    threat = Threat(
        id=uuid.uuid4(),
        suspicious_urls=["https://phish.net/login"],
        suspicious_emails=["scam@phish.net"],
        techniques=["CREDENTIAL_HARVESTING"],
    )
    camp = Campaign(
        id=uuid.uuid4(),
        name="PhishNet Wave",
        status=CampaignStatus.ACTIVE,
        risk_level=RiskLevel.CRITICAL,
        correlation_score=85,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    camp.threats = [threat]

    override_db.scalar.side_effect = [1, 1, 1, 0]
    override_db.scalars.return_value.all.side_effect = [[camp], [camp]]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/campaigns/radar")
        assert res.status_code == 200
        data = res.json()
        assert data["total_campaigns"] == 1
        assert data["active_campaigns"] == 1
        assert data["critical_campaigns"] == 1
        assert len(data["top_shared_domains"]) >= 1
        assert data["top_shared_domains"][0]["domain"] == "phish.net"


# 25. Existing threat records remain valid
def test_existing_threat_records_remain_valid():
    now = datetime.now(timezone.utc)
    threat = Threat(
        id=uuid.uuid4(),
        threat_detected=True,
        threat_type="PHISHING",
        risk_level="HIGH",
        created_at=now,
        updated_at=now,
    )
    # campaign_id defaults to None safely
    assert threat.campaign_id is None
    assert threat.campaign is None
