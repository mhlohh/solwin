import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.security import get_current_active_user, get_current_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

# ============================================================================
# 1. Password Hashing & Verification Tests
# ============================================================================


def test_password_hashing_and_verification():
    raw_password = "SuperSecurePassword123!"
    hashed = hash_password(raw_password)

    # Must be non-empty and formatted with PBKDF2 scheme
    assert hashed != raw_password
    assert hashed.startswith("pbkdf2_sha256$")

    # Correct password verifies
    assert verify_password(raw_password, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw_password, "") is False


def test_password_hashing_unique_salts():
    raw_password = "SamePasswordAcrossUsers"
    hash1 = hash_password(raw_password)
    hash2 = hash_password(raw_password)
    assert hash1 != hash2  # Salt ensures hashes are distinct
    assert verify_password(raw_password, hash1) is True
    assert verify_password(raw_password, hash2) is True


# ============================================================================
# 2. JWT Access Token Tests
# ============================================================================


def test_jwt_token_creation_and_decoding():
    subject_id = str(uuid.uuid4())
    token = create_access_token(
        subject=subject_id,
        claims={"role": "SUPPORT_AGENT", "email": "agent@solwin.ai"},
    )
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == subject_id
    assert payload["role"] == "SUPPORT_AGENT"
    assert payload["email"] == "agent@solwin.ai"
    assert "exp" in payload
    assert "iat" in payload


def test_expired_jwt_rejected():
    subject_id = str(uuid.uuid4())
    # Create token that expired 5 minutes ago
    token = create_access_token(
        subject=subject_id,
        expires_delta=timedelta(minutes=-5),
    )
    with pytest.raises(ValueError, match="expired"):
        decode_access_token(token)


def test_invalid_jwt_rejected():
    with pytest.raises(ValueError, match="Invalid"):
        decode_access_token("this.is.not.a.valid.jwt.token")


# ============================================================================
# 3. API Login & /me Endpoints Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_login_success(override_db):
    raw_password = "CorrectAgentPassword!"
    hashed = hash_password(raw_password)
    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()
    agent_user = User(
        id=user_id,
        email="agent@solwin.ai",
        full_name="Agent Smith",
        hashed_password=hashed,
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    override_db.scalar.return_value = agent_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "agent@solwin.ai",
                "password": raw_password,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["email"] == "agent@solwin.ai"
    assert data["user"]["role"] == "SUPPORT_AGENT"
    assert "hashed_password" not in data["user"]
    assert "password" not in data["user"]


@pytest.mark.asyncio
async def test_api_login_wrong_password_returns_401(override_db):
    hashed = hash_password("CorrectPassword123!")
    now = datetime.now(timezone.utc)
    agent_user = User(
        id=uuid.uuid4(),
        email="agent@solwin.ai",
        full_name="Agent Smith",
        hashed_password=hashed,
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    override_db.scalar.return_value = agent_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "agent@solwin.ai",
                "password": "WrongPassword!",
            },
        )

    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_login_unknown_user_returns_401(override_db):
    override_db.scalar.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "unknown@solwin.ai",
                "password": "AnyPassword!",
            },
        )

    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_login_inactive_user_rejected(override_db):
    raw_password = "MyPassword!"
    hashed = hash_password(raw_password)
    now = datetime.now(timezone.utc)
    inactive_user = User(
        id=uuid.uuid4(),
        email="inactive@solwin.ai",
        full_name="Deactivated User",
        hashed_password=hashed,
        role=UserRole.SUPPORT_AGENT,
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    override_db.scalar.return_value = inactive_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@solwin.ai",
                "password": raw_password,
            },
        )

    assert response.status_code == 401
    assert "inactive" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_auth_me_returns_current_user(override_db):
    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()
    agent_user = User(
        id=user_id,
        email="me@solwin.ai",
        full_name="Me Myself",
        hashed_password="hashed_pw",
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_current_user] = lambda: agent_user
    app.dependency_overrides[get_current_active_user] = lambda: agent_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["email"] == "me@solwin.ai"
    assert data["role"] == "SUPPORT_AGENT"
    assert data["is_active"] is True
    assert "hashed_password" not in data


# ============================================================================
# 4. Authentication Middleware & Security Exceptions
# ============================================================================


@pytest.mark.asyncio
async def test_missing_token_returns_401():
    # Remove authentication dependency overrides to test raw endpoint protection
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/v1/auth/me without headers
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert "missing" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_token_header_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer totally-invalid-token"},
        )

    assert response.status_code == 401


# ============================================================================
# 5. Role-Based Access Control (RBAC) Tests
# ============================================================================


@pytest.mark.asyncio
async def test_support_agent_permissions(override_db):
    now = datetime.now(timezone.utc)
    agent_user = User(
        id=uuid.uuid4(),
        email="agent@solwin.ai",
        full_name="Support Agent",
        hashed_password="pw",
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: agent_user
    app.dependency_overrides[get_current_active_user] = lambda: agent_user

    override_db.execute.return_value.scalars.return_value.all.return_value = []
    override_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Can access conversations
        conv_resp = await client.get("/api/v1/conversations")
        assert conv_resp.status_code == 200

        # Cannot access customer analytics (requires SUPPORT_MANAGER or ADMIN)
        analytics_resp = await client.get("/api/v1/analytics/customer")
        assert analytics_resp.status_code == 403
        assert "forbidden" in analytics_resp.json()["detail"].lower()

        # Cannot access security analytics (requires SECURITY_ANALYST or ADMIN)
        sec_analytics_resp = await client.get("/api/v1/analytics/security")
        assert sec_analytics_resp.status_code == 403

        # Cannot access dashboard overview (requires manager/analyst/admin)
        dash_resp = await client.get("/api/v1/dashboard/overview")
        assert dash_resp.status_code == 403


@pytest.mark.asyncio
async def test_support_manager_permissions(override_db):
    now = datetime.now(timezone.utc)
    manager_user = User(
        id=uuid.uuid4(),
        email="manager@solwin.ai",
        full_name="Support Manager",
        hashed_password="pw",
        role=UserRole.SUPPORT_MANAGER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: manager_user
    app.dependency_overrides[get_current_active_user] = lambda: manager_user

    # Mock empty stats for analytics and dashboard
    override_db.scalar.return_value = 0
    override_db.execute.return_value.all.return_value = []
    override_db.execute.return_value.one.side_effect = [
        type(
            "Stats",
            (),
            {
                "total": 0,
                "open_count": 0,
                "in_progress_count": 0,
                "resolved_count": 0,
            },
        )(),
        type("ThreatStats", (), {"detected_count": 0, "critical_count": 0})(),
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Can access customer analytics
        cust_resp = await client.get("/api/v1/analytics/customer")
        assert cust_resp.status_code == 200

        # Can access dashboard overview
        dash_resp = await client.get("/api/v1/dashboard/overview")
        assert dash_resp.status_code == 200

        # Cannot access security analytics (requires SECURITY_ANALYST or ADMIN)
        sec_resp = await client.get("/api/v1/analytics/security")
        assert sec_resp.status_code == 403


@pytest.mark.asyncio
async def test_security_analyst_permissions(override_db):
    now = datetime.now(timezone.utc)
    security_user = User(
        id=uuid.uuid4(),
        email="security@solwin.ai",
        full_name="Security Analyst",
        hashed_password="pw",
        role=UserRole.SECURITY_ANALYST,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: security_user
    app.dependency_overrides[get_current_active_user] = lambda: security_user

    override_db.scalar.return_value = 0
    override_db.execute.return_value.all.return_value = []

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Can access security analytics
        sec_resp = await client.get("/api/v1/analytics/security")
        assert sec_resp.status_code == 200

        # Can access recent threats
        recent_resp = await client.get("/api/v1/analytics/security/recent-threats")
        assert recent_resp.status_code == 200

        # Cannot access customer analytics
        cust_resp = await client.get("/api/v1/analytics/customer")
        assert cust_resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_permissions_can_access_all(override_db):
    now = datetime.now(timezone.utc)
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@solwin.ai",
        full_name="Admin User",
        hashed_password="pw",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_active_user] = lambda: admin_user

    override_db.scalar.return_value = 0
    override_db.execute.return_value.all.return_value = []
    override_db.execute.return_value.scalars.return_value.all.return_value = []

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Admin can access conversations
        conv_resp = await client.get("/api/v1/conversations")
        assert conv_resp.status_code == 200

        # Admin can access customer analytics
        cust_resp = await client.get("/api/v1/analytics/customer")
        assert cust_resp.status_code == 200

        # Admin can access security analytics
        sec_resp = await client.get("/api/v1/analytics/security")
        assert sec_resp.status_code == 200
