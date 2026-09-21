import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SecurityAnalysisRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, description="Raw message content to analyze"
    )
    expected_domain: Optional[str] = Field(
        None,
        description="Expected organization domain, e.g. 'solwin.ai' or 'bank.com'",
    )
    display_name: Optional[str] = Field(
        None,
        description="Optional sender display name for spoofing checks",
    )


class ThreatBase(BaseModel):
    threat_detected: bool = False
    threat_type: Optional[str] = None
    social_engineering_detected: bool = False
    techniques: Optional[List[str]] = Field(default_factory=list)
    risk_level: Optional[str] = None
    suspicious_urls: Optional[List[str]] = Field(default_factory=list)
    suspicious_emails: Optional[List[str]] = Field(default_factory=list)
    risk_reasons: Optional[List[str]] = Field(default_factory=list)
    recommended_action: Optional[str] = None


class ThreatCreate(ThreatBase):
    conversation_id: Optional[uuid.UUID] = None


class ThreatUpdate(BaseModel):
    threat_detected: Optional[bool] = None
    threat_type: Optional[str] = None
    social_engineering_detected: Optional[bool] = None
    techniques: Optional[List[str]] = None
    risk_level: Optional[str] = None
    suspicious_urls: Optional[List[str]] = None
    suspicious_emails: Optional[List[str]] = None
    risk_reasons: Optional[List[str]] = None
    recommended_action: Optional[str] = None


class ThreatRead(ThreatBase):
    id: uuid.UUID
    conversation_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSecurityResponse(BaseModel):
    conversation_id: uuid.UUID
    threat: ThreatRead
