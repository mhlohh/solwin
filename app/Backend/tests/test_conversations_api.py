import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.enums import ConversationChannel, ConversationStatus, SenderType
from app.models.message import Message


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
async def test_create_conversation_success(override_db):
    # Mock count and uniqueness checks for reference generator
    override_db.scalar.side_effect = [0, None]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/conversations",
            json={
                "customer_name": "Alice Smith",
                "customer_email": "alice@example.com",
                "channel": "CHAT",
                "subject": "Login issue",
                "initial_message": "Cannot log in to portal",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["conversation_reference"] == "CONV-000001"
    assert data["customer_name"] == "Alice Smith"
    assert data["status"] == "OPEN"
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_list_conversations_paginated(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id,
        conversation_reference="CONV-000001",
        customer_name="Alice Smith",
        customer_email="alice@example.com",
        channel=ConversationChannel.CHAT,
        subject="Login issue",
        status=ConversationStatus.OPEN,
        created_at=now,
        updated_at=now,
    )

    # First scalar returns total count (1), scalars().all() returns items
    override_db.scalar.return_value = 1
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [conv]
    override_db.scalars.return_value = mock_scalars

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/conversations?page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total"] == 1
    assert data["total_pages"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["conversation_reference"] == "CONV-000001"


@pytest.mark.asyncio
async def test_get_conversation_detail(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id,
        conversation_reference="CONV-000001",
        customer_name="Alice Smith",
        customer_email="alice@example.com",
        channel=ConversationChannel.CHAT,
        subject="Login issue",
        status=ConversationStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    conv.messages = []
    conv.analysis_records = []
    conv.threat_records = []
    conv.assigned_agent = None

    override_db.scalar.return_value = conv

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/conversations/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(conv_id)
    assert data["conversation_reference"] == "CONV-000001"
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_update_conversation(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id,
        conversation_reference="CONV-000001",
        customer_name="Alice Smith",
        customer_email="alice@example.com",
        channel=ConversationChannel.CHAT,
        subject="Login issue",
        status=ConversationStatus.OPEN,
        created_at=now,
        updated_at=now,
    )

    override_db.scalar.return_value = conv

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/conversations/{conv_id}",
            json={
                "status": "RESOLVED",
                "subject": "Resolved Login Issue",
            },
        )

    assert response.status_code == 200
    assert conv.status == ConversationStatus.RESOLVED
    assert conv.subject == "Resolved Login Issue"
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_delete_conversation(override_db):
    conv_id = uuid.uuid4()
    conv = Conversation(id=conv_id)
    override_db.scalar.return_value = conv

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/conversations/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert override_db.delete.called
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_create_message_for_conversation(override_db):
    conv_id = uuid.uuid4()

    # Conversation existence check
    override_db.scalar.return_value = conv_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "sender_type": "CUSTOMER",
                "sender_name": "Alice",
                "content": "Please verify my account token.",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["conversation_id"] == str(conv_id)
    assert data["content"] == "Please verify my account token."
    assert data["sender_type"] == "CUSTOMER"
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_list_messages_for_conversation(override_db):
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    msg = Message(
        id=msg_id,
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        sender_name="Alice",
        content="Please verify my account token.",
        created_at=now,
    )

    override_db.scalar.return_value = conv_id
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [msg]
    override_db.scalars.return_value = mock_scalars

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/conversations/{conv_id}/messages")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(msg_id)
    assert data[0]["conversation_id"] == str(conv_id)


@pytest.mark.asyncio
async def test_conversation_not_found(override_db):
    random_id = uuid.uuid4()
    override_db.scalar.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/conversations/{random_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_conversation_uuid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/conversations/not-a-valid-uuid")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_request_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # channel is invalid enum
        response = await client.post(
            "/api/v1/conversations",
            json={
                "channel": "NON_EXISTENT_CHANNEL",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_pagination_parameters():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # page must be >= 1
        response = await client.get("/api/v1/conversations?page=0")

    assert response.status_code == 422
