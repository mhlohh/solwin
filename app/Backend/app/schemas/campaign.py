from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CampaignStatus, RiskLevel


class CampaignThreatRead(BaseModel):
    id: UUID
    conversation_id: Optional[UUID] = None
    threat_type: Optional[str] = None
    risk_level: Optional[str] = None
    suspicious_urls: List[str] = Field(default_factory=list)
    suspicious_emails: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SharedIndicators(BaseModel):
    domains: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    email_domains: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    threat_types: List[str] = Field(default_factory=list)


class CampaignSummary(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    risk_level: RiskLevel
    status: CampaignStatus
    correlation_score: int
    threat_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignRead(CampaignSummary):
    shared_indicators: SharedIndicators = Field(default_factory=SharedIndicators)


class CampaignDetailResponse(CampaignSummary):
    threats: List[CampaignThreatRead] = Field(default_factory=list)
    shared_indicators: SharedIndicators = Field(default_factory=SharedIndicators)


class CampaignStatusUpdate(BaseModel):
    status: CampaignStatus


class CampaignListResponse(BaseModel):
    items: List[CampaignSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class DomainMetric(BaseModel):
    domain: str
    count: int


class TechniqueMetric(BaseModel):
    technique: str
    count: int


class CampaignRadarResponse(BaseModel):
    total_campaigns: int
    active_campaigns: int
    critical_campaigns: int
    high_risk_campaigns: int
    top_shared_domains: List[DomainMetric] = Field(default_factory=list)
    top_shared_email_domains: List[DomainMetric] = Field(default_factory=list)
    most_common_techniques: List[TechniqueMetric] = Field(default_factory=list)
    recent_campaigns: List[CampaignSummary] = Field(default_factory=list)
