from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Ticket(Base):
    """Raw customer support / phishing record with all dataset identifiers."""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    domain = Column(String(128), nullable=True, index=True)
    channel = Column(String(64), nullable=True, index=True)
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True, index=True)
    issue = Column(String(255), nullable=True, index=True)
    technique = Column(String(255), nullable=True)
    phishing = Column(Boolean, nullable=True, index=True)
    sender = Column(String(255), nullable=True)
    label = Column(String(128), nullable=True)
    priority = Column(String(16), nullable=False, default="LOW", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    attachments = relationship(
        "Attachment",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("Ticket", back_populates="attachments")
