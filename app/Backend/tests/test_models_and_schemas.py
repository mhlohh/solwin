import uuid
from datetime import datetime, timezone

from sqlalchemy import inspect

from app.core.database import Base
from app.models import (
    Analysis,
    Conversation,
    ConversationChannel,
    ConversationStatus,
    Message,
    Priority,
    RiskLevel,
    SenderType,
    Sentiment,
    Threat,
    User,
    UserRole,
)
from app.schemas import (
    AnalysisCreate,
    AnalysisRead,
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
    ThreatCreate,
    ThreatRead,
    UserCreate,
    UserRead,
)


# ==========================================
# 1. Model Imports & Metadata Registration
# ==========================================
def test_models_registered_in_metadata():
    tables = Base.metadata.tables.keys()
    assert "users" in tables
    assert "conversations" in tables
    assert "messages" in tables
    assert "analyses" in tables
    assert "threats" in tables
    assert "attachments" in tables
    assert "campaigns" in tables


# ==========================================
# 2. Enum Values Verification
# ==========================================
def test_enum_values():
    assert set(e.value for e in UserRole) == {
        "SUPPORT_AGENT",
        "SUPPORT_MANAGER",
        "SECURITY_ANALYST",
        "ADMIN",
    }
    assert set(e.value for e in ConversationChannel) == {
        "EMAIL",
        "CHAT",
        "TICKET",
        "SOCIAL_MEDIA",
        "OTHER",
    }
    assert set(e.value for e in ConversationStatus) == {
        "OPEN",
        "IN_PROGRESS",
        "RESOLVED",
        "CLOSED",
    }
    assert set(e.value for e in SenderType) == {
        "CUSTOMER",
        "AGENT",
        "SYSTEM",
    }
    assert set(e.value for e in Sentiment) == {
        "POSITIVE",
        "NEUTRAL",
        "NEGATIVE",
    }
    assert set(e.value for e in Priority) == {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }
    assert set(e.value for e in RiskLevel) == {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }


# ==========================================
# 3. Relationship Configuration
# ==========================================
def test_relationship_configuration():
    # User -> assigned_conversations
    user_mapper = inspect(User)
    assert "assigned_conversations" in user_mapper.relationships
    user_rel = user_mapper.relationships["assigned_conversations"]
    assert user_rel.target.name == "conversations"

    # Conversation -> relationships
    conv_mapper = inspect(Conversation)
    assert "assigned_agent" in conv_mapper.relationships
    assert "messages" in conv_mapper.relationships
    assert "analysis_records" in conv_mapper.relationships
    assert "threat_records" in conv_mapper.relationships

    assert conv_mapper.relationships["assigned_agent"].target.name == "users"
    assert conv_mapper.relationships["messages"].target.name == "messages"
    assert conv_mapper.relationships["analysis_records"].target.name == "analyses"
    assert conv_mapper.relationships["threat_records"].target.name == "threats"

    # Check cascade settings
    assert conv_mapper.relationships["messages"].cascade.delete
    assert conv_mapper.relationships["messages"].cascade.delete_orphan
    assert conv_mapper.relationships["analysis_records"].cascade.delete
    assert conv_mapper.relationships["threat_records"].cascade.delete

    # Message -> conversation
    msg_mapper = inspect(Message)
    assert "conversation" in msg_mapper.relationships
    assert msg_mapper.relationships["conversation"].target.name == "conversations"

    # Analysis -> conversation
    analysis_mapper = inspect(Analysis)
    assert "conversation" in analysis_mapper.relationships
    assert analysis_mapper.relationships["conversation"].target.name == "conversations"

    # Threat -> conversation
    threat_mapper = inspect(Threat)
    assert "conversation" in threat_mapper.relationships
    assert threat_mapper.relationships["conversation"].target.name == "conversations"


# ==========================================
# 4. Pydantic Schema Validation
# ==========================================
def test_pydantic_schema_validation():
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # UserCreate
    user_create = UserCreate(
        email="agent@solwin.test",
        full_name="Alice Agent",
        password="SuperSecretPassword123!",
        role=UserRole.SUPPORT_AGENT,
    )
    assert user_create.email == "agent@solwin.test"
    assert user_create.password == "SuperSecretPassword123!"

    # UserRead
    user_read = UserRead(
        id=user_id,
        email="agent@solwin.test",
        full_name="Alice Agent",
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    assert user_read.id == user_id

    # Conversation schemas
    conv_id = uuid.uuid4()
    conv_create = ConversationCreate(
        customer_name="John Doe",
        customer_email="john@example.com",
        channel=ConversationChannel.EMAIL,
        subject="Urgent Account Verification",
        initial_message="Initial inquiry",
    )
    assert conv_create.customer_name == "John Doe"
    assert conv_create.channel == ConversationChannel.EMAIL

    conv_read = ConversationRead(
        id=conv_id,
        conversation_reference="CONV-000001",
        customer_name="John Doe",
        customer_email="john@example.com",
        channel=ConversationChannel.EMAIL,
        subject="Urgent Account Verification",
        status=ConversationStatus.OPEN,
        assigned_agent_id=user_id,
        created_at=now,
        updated_at=now,
    )
    assert conv_read.id == conv_id

    # Message schemas
    msg_id = uuid.uuid4()
    msg_create = MessageCreate(
        sender_type=SenderType.CUSTOMER,
        sender_name="John Doe",
        content="Please verify my account immediately at http://phish.example",
    )
    assert msg_create.content.startswith("Please verify")

    msg_read = MessageRead(
        id=msg_id,
        conversation_id=conv_id,
        sender_type=SenderType.CUSTOMER,
        sender_name="John Doe",
        content="Please verify my account immediately at http://phish.example",
        created_at=now,
    )
    assert msg_read.id == msg_id

    # Analysis schemas
    analysis_id = uuid.uuid4()
    analysis_create = AnalysisCreate(
        conversation_id=conv_id,
        category="Account Security",
        issue="Password Reset Request",
        sentiment=Sentiment.NEGATIVE.value,
        emotion="Frustrated",
        priority=Priority.HIGH.value,
        resolution_status="PENDING",
        summary="Customer asking for urgent credential verification",
        recommended_action="Validate identity before responding",
    )
    assert analysis_create.sentiment == "NEGATIVE"

    analysis_read = AnalysisRead(
        id=analysis_id,
        conversation_id=conv_id,
        category="Account Security",
        issue="Password Reset Request",
        sentiment="NEGATIVE",
        emotion="Frustrated",
        priority="HIGH",
        resolution_status="PENDING",
        summary="Customer asking for urgent credential verification",
        recommended_action="Validate identity before responding",
        created_at=now,
        updated_at=now,
    )
    assert analysis_read.id == analysis_id

    # Threat schemas
    threat_id = uuid.uuid4()
    threat_create = ThreatCreate(
        conversation_id=conv_id,
        threat_detected=True,
        threat_type="Phishing",
        social_engineering_detected=True,
        techniques=["Urgency Prompting", "Credential Harvesting"],
        risk_level=RiskLevel.CRITICAL.value,
        suspicious_urls=["http://phish.example/login"],
        suspicious_emails=["fake-security@bank-verify.com"],
        risk_reasons=["External domain mimicking security portal"],
        recommended_action="Block sender and do not click links",
    )
    assert threat_create.threat_detected is True
    assert len(threat_create.suspicious_urls) == 1

    threat_read = ThreatRead(
        id=threat_id,
        conversation_id=conv_id,
        threat_detected=True,
        threat_type="Phishing",
        social_engineering_detected=True,
        techniques=["Urgency Prompting", "Credential Harvesting"],
        risk_level="CRITICAL",
        suspicious_urls=["http://phish.example/login"],
        suspicious_emails=["fake-security@bank-verify.com"],
        risk_reasons=["External domain mimicking security portal"],
        recommended_action="Block sender and do not click links",
        created_at=now,
        updated_at=now,
    )
    assert threat_read.id == threat_id


# ==========================================
# 5. Security: Sensitive Password Excluded
# ==========================================
def test_user_read_schema_excludes_password():
    fields = UserRead.model_fields.keys()
    assert "hashed_password" not in fields
    assert "password" not in fields

    user_data = {
        "id": uuid.uuid4(),
        "email": "analyst@solwin.test",
        "full_name": "Bob Analyst",
        "role": UserRole.SECURITY_ANALYST,
        "is_active": True,
        "hashed_password": "super-hashed-password-string",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    # Instantiating UserRead with extra field should ignore it
    # or exclude it from dumped response dictionary
    user_read = UserRead.model_validate(user_data)
    dumped = user_read.model_dump()
    assert "hashed_password" not in dumped
    assert "password" not in dumped
