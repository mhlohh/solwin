import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ConversationChannel, ConversationStatus

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.attachment import Attachment
    from app.models.message import Message
    from app.models.threat import Threat
    from app.models.user import User


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_reference: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    customer_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(ConversationChannel, name="conversation_channel", native_enum=True),
        nullable=False,
        default=ConversationChannel.CHAT,
    )
    subject: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status", native_enum=True),
        nullable=False,
        default=ConversationStatus.OPEN,
    )
    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assigned_agent: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_conversations",
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    analysis_records: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Analysis.created_at.desc()",
    )
    threat_records: Mapped[List["Threat"]] = relationship(
        "Threat",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Threat.created_at.desc()",
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Attachment.created_at.desc()",
    )
