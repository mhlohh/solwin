import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DashboardOverviewResponse(BaseModel):
    """Aggregated high-level overview metrics across support and security."""

    model_config = ConfigDict(from_attributes=True)

    total_conversations: int = Field(
        ..., description="Total count of customer conversations"
    )
    open_conversations: int = Field(
        ..., description="Conversations currently in OPEN state"
    )
    in_progress_conversations: int = Field(
        ..., description="Conversations currently IN_PROGRESS"
    )
    resolved_conversations: int = Field(
        ..., description="Conversations currently RESOLVED or CLOSED"
    )
    unresolved_conversations: int = Field(
        ..., description="Conversations that remain unresolved (OPEN or IN_PROGRESS)"
    )
    urgent_conversations: int = Field(
        ..., description="Conversations with HIGH or CRITICAL priority"
    )
    threats_detected: int = Field(
        ..., description="Total number of security threats detected"
    )
    critical_threats: int = Field(
        ..., description="Total threats with CRITICAL risk level"
    )
    sentiment_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of analyses grouped by sentiment (e.g. POSITIVE, NEUTRAL, NEGATIVE)"
        ),
    )
    category_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of analyses grouped by complaint category",
    )
    risk_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of threats grouped by risk level (LOW, MEDIUM, HIGH, CRITICAL)"
        ),
    )
    ingested_feedback: Optional[Dict] = Field(
        default=None,
        description=(
            "Statistics over the ingested raw feedback dataset (total_records, "
            "phishing_flagged, priority_counts, top_intents). Null when the "
            "data ingestion service is unavailable."
        ),
    )


class IssueFrequency(BaseModel):
    """Occurrence frequency for customer reported issues."""

    issue: str = Field(..., description="Reported customer issue description")
    count: int = Field(..., description="Number of times this issue was recorded")


class IngestedFeedbackStats(BaseModel):
    """Aggregated statistics over the ingested raw feedback dataset."""

    total_records: int = Field(0, description="Records in the ingested dataset")
    phishing_flagged: int = Field(
        0, description="Records flagged as phishing in the source dataset"
    )
    priority_counts: Dict[str, int] = Field(
        default_factory=dict, description="Record counts per priority tier"
    )
    top_intents: List[IssueFrequency] = Field(
        default_factory=list, description="Most frequent dataset intents"
    )


class CustomerAnalyticsResponse(BaseModel):
    """Detailed analytics metrics for customer support intelligence."""

    model_config = ConfigDict(from_attributes=True)

    total_conversations: int = Field(..., description="Total conversations")
    category_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of issues by category"
    )
    sentiment_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of customer sentiment"
    )
    priority_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of customer priority"
    )
    resolution_status_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of resolution statuses"
    )
    most_frequently_reported_issues: List[IssueFrequency] = Field(
        default_factory=list, description="Top reported customer issues by frequency"
    )
    unresolved_complaint_count: int = Field(
        ..., description="Total unresolved complaint count"
    )
    urgent_complaint_count: int = Field(
        ..., description="Total urgent complaint count (HIGH and CRITICAL priority)"
    )


class RecentThreat(BaseModel):
    """Summary of a recent security threat for security analyst view."""

    model_config = ConfigDict(from_attributes=True)

    threat_id: uuid.UUID = Field(..., description="Unique threat identifier")
    conversation_id: Optional[uuid.UUID] = Field(
        None, description="Associated conversation identifier if any"
    )
    threat_type: Optional[str] = Field(
        None, description="Classified threat type (e.g. PHISHING, SOCIAL_ENGINEERING)"
    )
    risk_level: Optional[str] = Field(
        None, description="Assessed risk level (e.g. CRITICAL, HIGH, MEDIUM, LOW)"
    )
    risk_reasons: List[str] = Field(
        default_factory=list, description="Specific risk indicators"
    )
    created_at: datetime = Field(..., description="Time of threat detection in UTC")


class SecurityAnalyticsResponse(BaseModel):
    """Detailed analytics metrics for security intelligence."""

    model_config = ConfigDict(from_attributes=True)

    total_threats: int = Field(..., description="Total threat evaluation records")
    threats_detected: int = Field(
        ..., description="Total confirmed threats detected (threat_detected=True)"
    )
    risk_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of evaluated risk levels"
    )
    threat_type_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of threat types"
    )
    technique_frequency: Dict[str, int] = Field(
        default_factory=dict,
        description="Frequency of identified social engineering techniques",
    )
    suspicious_url_count: int = Field(
        ..., description="Total count of suspicious URLs observed"
    )
    suspicious_email_count: int = Field(
        ..., description="Total count of suspicious emails observed"
    )
    recent_critical_threats: List[RecentThreat] = Field(
        default_factory=list,
        description="List of most recent CRITICAL severity threats",
    )


class TrendPoint(BaseModel):
    """Date-based aggregation point."""

    date: str = Field(..., description="Date formatted as YYYY-MM-DD")
    count: int = Field(..., description="Count of occurrences on this date")


class TrendResponse(BaseModel):
    """Time-series trend response."""

    days: int = Field(..., description="Query period in days")
    total_count: int = Field(
        ..., description="Total occurrences across the requested period"
    )
    trends: List[TrendPoint] = Field(
        default_factory=list, description="Chronological trend series"
    )
