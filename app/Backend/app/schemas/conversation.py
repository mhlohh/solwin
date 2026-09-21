import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConversationChannel, ConversationStatus
from app.schemas.analysis import AnalysisRead
from app.schemas.message import MessageRead
from app.schemas.threat import ThreatRead
from app.schemas.user import UserRead


class ConversationBase(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    channel: ConversationChannel = ConversationChannel.CHAT
    subject: Optional[str] = Field(None, max_length=255)


class ConversationCreate(ConversationBase):
    initial_message: Optional[str] = Field(
        None,
        description="Optional initial customer message content",
    )


class ConversationUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    channel: Optional[ConversationChannel] = None
    subject: Optional[str] = Field(None, max_length=255)
    status: Optional[ConversationStatus] = None
    assigned_agent_id: Optional[uuid.UUID] = None


class ConversationRead(ConversationBase):
    id: uuid.UUID
    conversation_reference: str
    status: ConversationStatus
    assigned_agent_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailRead(ConversationRead):
    assigned_agent: Optional[UserRead] = None
    messages: List[MessageRead] = []
    analysis_records: List[AnalysisRead] = []
    threat_records: List[ThreatRead] = []

    model_config = ConfigDict(from_attributes=True)
