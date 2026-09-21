import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ComplaintCategory,
    Priority,
    ResolutionStatus,
    Sentiment,
)


class CustomerIntelligenceOutput(BaseModel):
    category: ComplaintCategory = Field(
        ...,
        description=(
            "Complaint category: ACCOUNT_ACCESS, PAYMENT_BILLING, "
            "TECHNICAL_ISSUE, SERVICE_REQUEST, or OTHER"
        ),
    )
    issue: str = Field(
        ...,
        description="Concise description of the customer issue",
        max_length=255,
    )
    sentiment: Sentiment = Field(
        ...,
        description="Customer sentiment: POSITIVE, NEUTRAL, or NEGATIVE",
    )
    emotion: str = Field(
        ...,
        description=(
            "Dominant emotion (e.g. Frustration, Anger, Confusion, "
            "Satisfaction, Neutral)"
        ),
        max_length=50,
    )
    priority: Priority = Field(
        ...,
        description="Support priority: LOW, MEDIUM, HIGH, or CRITICAL",
    )
    resolution_status: ResolutionStatus = Field(
        ...,
        description="Resolution status: UNRESOLVED, IN_PROGRESS, or RESOLVED",
    )
    summary: str = Field(
        ...,
        description=(
            "Concise support-agent-friendly summary answering what happened "
            "and what customer needs"
        ),
    )


class AnalysisBase(BaseModel):
    category: Optional[str] = None
    issue: Optional[str] = None
    sentiment: Optional[str] = None
    emotion: Optional[str] = None
    priority: Optional[str] = None
    resolution_status: Optional[str] = None
    summary: Optional[str] = None
    recommended_action: Optional[str] = None


class AnalysisCreate(AnalysisBase):
    conversation_id: uuid.UUID


class AnalysisUpdate(BaseModel):
    category: Optional[str] = None
    issue: Optional[str] = None
    sentiment: Optional[str] = None
    emotion: Optional[str] = None
    priority: Optional[str] = None
    resolution_status: Optional[str] = None
    summary: Optional[str] = None
    recommended_action: Optional[str] = None


class AnalysisRead(AnalysisBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationAnalysisResponse(BaseModel):
    conversation_id: uuid.UUID
    analysis: AnalysisRead
