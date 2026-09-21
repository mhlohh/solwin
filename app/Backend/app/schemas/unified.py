import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import (
    ComplaintCategory,
    Priority,
    ResolutionStatus,
    Sentiment,
)


class UnifiedAnalysisRequest(BaseModel):
    conversation_id: uuid.UUID = Field(
        ...,
        description="UUID of the conversation to analyze",
    )


class DirectMessageAnalysisRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Raw message text to analyze without saving",
    )
    expected_domain: Optional[str] = Field(
        None,
        description="Expected company/organization domain for spoofing checks",
    )


class CustomerIntelligenceSummary(BaseModel):
    category: ComplaintCategory
    issue: str
    sentiment: Sentiment
    emotion: str
    priority: Priority
    resolution_status: ResolutionStatus
    summary: str


class SecurityIntelligenceSummary(BaseModel):
    threat_detected: bool
    threat_type: str
    suspicious_urls: List[str] = Field(default_factory=list)
    suspicious_emails: List[str] = Field(default_factory=list)
    social_engineering_detected: bool
    techniques: List[str] = Field(default_factory=list)
    risk_level: str
    risk_reasons: List[str] = Field(default_factory=list)


class UnifiedAnalysisResponse(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    customer_intelligence: CustomerIntelligenceSummary
    security_intelligence: SecurityIntelligenceSummary
    recommended_action: str
