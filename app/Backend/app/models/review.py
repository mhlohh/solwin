import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.types import JSONType, UUIDType


class CustomerReview(Base):
    __tablename__ = "customer_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    review_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    # Source info
    source_type: Mapped[str] = mapped_column(String(64), default="KAGGLE")
    source_record_id: Mapped[str] = mapped_column(String(128), default="")
    domain: Mapped[str] = mapped_column(String(128), default="E-commerce/Retail")
    channel: Mapped[str] = mapped_column(String(64), default="Email")

    # Content
    subject: Mapped[str] = mapped_column(String(512), default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification & Sentiment
    category: Mapped[str] = mapped_column(String(128), index=True)
    fine_grained_intent: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    sentiment_label: Mapped[str] = mapped_column(String(32), default="NEUTRAL")
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.5)

    # Keywords & Summary
    keywords: Mapped[List[str]] = mapped_column(JSONType, default=list)
    summary_text: Mapped[str] = mapped_column(Text, default="")

    # Clustering
    cluster_id: Mapped[str] = mapped_column(String(64), default="cluster_00")
    cluster_name: Mapped[str] = mapped_column(String(255), default="")
    cluster_similarity_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Urgency & Resolution
    urgency_level: Mapped[str] = mapped_column(String(32), default="MEDIUM")
    urgency_score: Mapped[float] = mapped_column(Float, default=0.5)
    urgency_reasons: Mapped[List[str]] = mapped_column(JSONType, default=list)
    resolution_status: Mapped[str] = mapped_column(String(32), default="UNRESOLVED")
    resolution_confidence: Mapped[float] = mapped_column(Float, default=0.5)
    resolution_evidence: Mapped[List[str]] = mapped_column(JSONType, default=list)

    # Security
    security_risk_level: Mapped[str] = mapped_column(String(32), default="LOW")
    security_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    phishing: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    urls: Mapped[List[Dict[str, Any]]] = mapped_column(JSONType, default=list)
    email_addresses: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONType, default=list
    )
    social_engineering: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    security_reasons: Mapped[List[str]] = mapped_column(JSONType, default=list)

    # Overall Risk & Recommendation
    overall_risk_level: Mapped[str] = mapped_column(String(32), default="LOW")
    overall_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_risk_factors: Mapped[List[str]] = mapped_column(JSONType, default=list)
    primary_action: Mapped[str] = mapped_column(String(255), default="")
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL")
    secondary_actions: Mapped[List[str]] = mapped_column(JSONType, default=list)
    recommendation_rationale: Mapped[str] = mapped_column(Text, default="")

    # Provenance & Metadata
    model_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    warnings: Mapped[List[str]] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_customer_reviews_category_urgency", "category", "urgency_level"),
        Index("ix_customer_reviews_security_risk", "security_risk_level"),
    )
