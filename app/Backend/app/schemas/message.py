import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SenderType
from app.schemas.attachment import AttachmentRead


class MessageBase(BaseModel):
    sender_type: SenderType = SenderType.CUSTOMER
    sender_name: Optional[str] = Field(None, max_length=255)
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    sender_name: Optional[str] = Field(None, max_length=255)


class MessageRead(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime
    attachments: list[AttachmentRead] = []

    model_config = ConfigDict(from_attributes=True)
