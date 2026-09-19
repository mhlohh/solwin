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
    ConversationChannel,
    ConversationStatus,
    Priority,
    ResolutionStatus,
    SenderType,
    Sentiment,
)
from app.models.message import Message
from app.schemas.analysis import CustomerIntelligenceOutput
from app.services.ai.customer_intelligence import (
    CustomerIntelligenceError,
    CustomerIntelligenceService,
)
from app.services.ai.preprocessing import clean_text


# ==========================================
# 1. Text Preprocessing Tests
# ==========================================
def test_clean_text():
    dirty = (
        "   Hello \t\t world! \x00\x08 Here is an email test@example.com "
        "and url https://solwin.ai/login \n\n\n\n Please help!   "
    )
    cleaned = clean_text(dirty)
    assert "Hello world!" in cleaned
    assert "test@example.com" in cleaned
    assert "https://solwin.ai/login" in cleaned
    assert "\x00" not in cleaned
    assert "\x08" not in cleaned
    assert "\n\n\n" not in cleaned
    assert cleaned.endswith("Please help!")


# ==========================================
# 2. Customer Intelligence Unit Tests (Mocked)
# ==========================================
def test_customer_intelligence_empty_messages():
    service = CustomerIntelligenceService(api_key="fake-key")
    with pytest.raises(CustomerIntelligenceError) as exc_info:
        service.analyze_conversation([])
    assert exc_info.value.status_code == 400


def test_customer_intelligence_missing_api_key():
    service = CustomerIntelligenceService(api_key="")
    with pytest.raises(CustomerIntelligenceError) as exc_info:
        service.get_client()
    assert exc_info.value.status_code == 503


def test_customer_intelligence_successful_mock():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"category": "PAYMENT_BILLING", "issue": "Duplicate charge on card", '
        '"sentiment": "NEGATIVE", "emotion": "Frustration", "priority": "HIGH", '
        '"resolution_status": "UNRESOLVED", "summary": "Customer double charged."}'
    )
    mock_client.models.generate_content.return_value = mock_response

    service = CustomerIntelligenceService(
        api_key="fake-key",
        client=mock_client,
    )

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        sender_type=SenderType.CUSTOMER,
        sender_name="John",
        content="I was charged twice for the same renewal fee!",
        created_at=datetime.now(timezone.utc),
    )

    result = service.analyze_conversation([msg], subject="Billing Error")

    assert isinstance(result, CustomerIntelligenceOutput)
    assert result.category == ComplaintCategory.PAYMENT_BILLING
    assert result.issue == "Duplicate charge on card"
    assert result.sentiment == Sentiment.NEGATIVE
    assert result.priority == Priority.HIGH
    assert result.resolution_status == ResolutionStatus.UNRESOLVED
    assert result.emotion == "Frustration"


def test_customer_intelligence_invalid_output_json():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"invalid_json": true}'
    mock_client.models.generate_content.return_value = mock_response

    service = CustomerIntelligenceService(
        api_key="fake-key",
        client=mock_client,
    )

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        sender_type=SenderType.CUSTOMER,
        content="Testing parsing failure",
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(CustomerIntelligenceError) as exc_info:
        service.analyze_conversation([msg])
    assert exc_info.value.status_code == 502


# ==========================================
# 3. API Integration Tests (Mocked DB & AI)
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
async def test_api_analyze_conversation_success(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id,
        conversation_reference="CONV-000001",
        customer_name="Bob Jones",
        customer_email="bob@example.com",
        channel=ConversationChannel.CHAT,
        subject="Locked out of account",
        status=ConversationStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        sender_name="Bob",
        content="I entered my password 5 times and now my account is locked.",
        created_at=now,
    )
    conv.messages = [msg]

    override_db.scalar.side_effect = [conv, None]

    mock_output = CustomerIntelligenceOutput(
        category=ComplaintCategory.ACCOUNT_ACCESS,
        issue="Account locked after multiple failed password attempts",
        sentiment=Sentiment.NEGATIVE,
        emotion="Anxiety",
        priority=Priority.HIGH,
        resolution_status=ResolutionStatus.UNRESOLVED,
        summary="Customer is locked out of account and needs access.",
    )

    with patch(
        "app.api.v1.analysis.CustomerIntelligenceService.analyze_conversation",
        return_value=mock_output,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/analysis/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == str(conv_id)
    analysis = data["analysis"]
    assert analysis["category"] == "ACCOUNT_ACCESS"
    assert analysis["sentiment"] == "NEGATIVE"
    assert analysis["priority"] == "HIGH"
    assert analysis["resolution_status"] == "UNRESOLVED"
    assert override_db.add.called
    assert override_db.commit.called


@pytest.mark.asyncio
async def test_api_analyze_conversation_not_found(override_db):
    conv_id = uuid.uuid4()
    override_db.scalar.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/analysis/conversation/{conv_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_analyze_empty_conversation(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=conv_id,
        conversation_reference="CONV-000002",
        created_at=now,
        updated_at=now,
    )
    conv.messages = []
    override_db.scalar.return_value = conv

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/analysis/conversation/{conv_id}")

    assert response.status_code == 400
    assert "empty conversation" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_get_analysis_success(override_db):
    conv_id = uuid.uuid4()
    analysis_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    conv = Conversation(id=conv_id, created_at=now, updated_at=now)
    analysis = Analysis(
        id=analysis_id,
        conversation_id=conv_id,
        category="TECHNICAL_ISSUE",
        issue="500 Internal Server Error on checkout",
        sentiment="NEGATIVE",
        emotion="Frustration",
        priority="CRITICAL",
        resolution_status="UNRESOLVED",
        summary="Customer reports payment gateway crash.",
        created_at=now,
        updated_at=now,
    )

    override_db.scalar.side_effect = [conv, analysis]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/analysis/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == str(conv_id)
    assert data["analysis"]["id"] == str(analysis_id)
    assert data["analysis"]["priority"] == "CRITICAL"


@pytest.mark.asyncio
async def test_api_get_analysis_none_exists(override_db):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    conv = Conversation(id=conv_id, created_at=now, updated_at=now)

    override_db.scalar.side_effect = [conv, None]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/analysis/conversation/{conv_id}")

    assert response.status_code == 404
    assert "no analysis found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reanalysis_updates_existing_record(override_db):
    conv_id = uuid.uuid4()
    analysis_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    conv = Conversation(
        id=conv_id,
        conversation_reference="CONV-000003",
        created_at=now,
        updated_at=now,
    )
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        content="Thank you, it is resolved now!",
        created_at=now,
    )
    conv.messages = [msg]

    existing_analysis = Analysis(
        id=analysis_id,
        conversation_id=conv_id,
        category="ACCOUNT_ACCESS",
        issue="Old issue",
        sentiment="NEGATIVE",
        emotion="Frustration",
        priority="HIGH",
        resolution_status="UNRESOLVED",
        summary="Old summary",
        created_at=now,
        updated_at=now,
    )

    override_db.scalar.side_effect = [conv, existing_analysis]

    new_output = CustomerIntelligenceOutput(
        category=ComplaintCategory.SERVICE_REQUEST,
        issue="Resolved inquiry",
        sentiment=Sentiment.POSITIVE,
        emotion="Satisfaction",
        priority=Priority.LOW,
        resolution_status=ResolutionStatus.RESOLVED,
        summary="Customer confirmed issue resolution.",
    )

    with patch(
        "app.api.v1.analysis.CustomerIntelligenceService.analyze_conversation",
        return_value=new_output,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/analysis/conversation/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["analysis"]["id"] == str(analysis_id)
    assert data["analysis"]["resolution_status"] == "RESOLVED"
    assert data["analysis"]["sentiment"] == "POSITIVE"
    assert existing_analysis.resolution_status == "RESOLVED"
    assert override_db.commit.called
