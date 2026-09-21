"""Customer Review Intelligence service.

Connects the Backend unified pipeline to the ML service, receives the
canonical CustomerReviewOutput, persists it to PostgreSQL via the
CustomerReview ORM model, and serves stored records back through the API.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.review import CustomerReview
from app.schemas.review import CustomerReviewOutput
from app.services.ml_service_client import MLServiceError, analyze_review_via_ml

logger = get_logger("solwin.customer_review_service")


class CustomerReviewError(Exception):
    """Domain error for customer review operations."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CustomerReviewService:
    @staticmethod
    def analyze_and_persist(
        db: Session,
        message: str,
        subject: Optional[str] = None,
        review_id: Optional[str] = None,
        source_type: str = "KAGGLE",
        source_record_id: str = "",
        domain: str = "E-commerce/Retail",
        channel: str = "Email",
        prefer_llm: bool = True,
    ) -> CustomerReviewOutput:
        """Run ML analysis and persist the resulting canonical record.

        Calls the ML service /analyze/review endpoint, stores the full
        intelligence payload in the customer_reviews table and returns the
        validated canonical output.

        Raises:
            CustomerReviewError: When the message is empty or the ML service
                cannot produce a valid result.
        """
        if not message or not message.strip():
            raise CustomerReviewError(
                "Cannot analyze an empty message.", status_code=400
            )

        try:
            review: CustomerReviewOutput = analyze_review_via_ml(
                {
                    "message": message,
                    "subject": subject or "",
                    "review_id": review_id,
                    "source_type": source_type,
                    "source_record_id": source_record_id,
                    "domain": domain,
                    "channel": channel,
                    "prefer_llm": prefer_llm,
                }
            )
        except MLServiceError as exc:
            raise CustomerReviewError(exc.message, status_code=exc.status_code) from exc

        CustomerReviewService.persist(db, review)
        return review

    @staticmethod
    def persist(db: Session, review: CustomerReviewOutput) -> CustomerReviewOutput:
        """Persist a canonical CustomerReviewOutput. Updates the record in
        place when review_id already exists (idempotent ingestion)."""
        now = datetime.now(timezone.utc)
        existing = db.scalar(
            select(CustomerReview).where(CustomerReview.review_id == review.review_id)
        )

        record = existing or CustomerReview(id=uuid.uuid4(), review_id=review.review_id)
        is_new = existing is None

        record.source_type = review.source.source_type
        record.source_record_id = review.source.source_record_id
        record.domain = review.source.domain
        record.channel = review.source.channel
        record.subject = review.content.subject
        record.message = review.content.message
        record.category = review.classification.category
        record.fine_grained_intent = review.classification.fine_grained_intent
        record.classification_confidence = review.classification.confidence
        record.needs_review = review.classification.needs_review
        record.sentiment_label = review.sentiment.label
        record.sentiment_score = review.sentiment.score
        record.keywords = list(review.keywords)
        record.summary_text = review.summary.text
        record.cluster_id = review.clustering.cluster_id
        record.cluster_name = review.clustering.cluster_name
        record.cluster_similarity_score = review.clustering.similarity_score
        record.urgency_level = review.urgency.level
        record.urgency_score = review.urgency.score
        record.urgency_reasons = list(review.urgency.reasons)
        record.resolution_status = review.resolution.status
        record.resolution_confidence = review.resolution.confidence
        record.resolution_evidence = list(review.resolution.evidence)
        record.security_risk_level = review.security.risk_level
        record.security_risk_score = review.security.risk_score
        record.phishing = review.security.phishing.model_dump()
        record.urls = review.security.urls
        record.email_addresses = review.security.email_addresses
        record.social_engineering = review.security.social_engineering.model_dump()
        record.security_reasons = list(review.security.reasons)
        record.overall_risk_level = review.overall_risk.level
        record.overall_risk_score = review.overall_risk.score
        record.overall_risk_factors = list(review.overall_risk.factors)
        record.primary_action = review.recommendation.primary_action
        record.priority = review.recommendation.priority
        record.secondary_actions = list(review.recommendation.secondary_actions)
        record.recommendation_rationale = review.recommendation.rationale
        record.model_metadata = review.model_metadata.model_dump()
        record.processing_time_ms = review.processing.processing_time_ms
        record.warnings = list(review.processing.warnings)
        record.created_at = now

        if is_new:
            db.add(record)
        db.commit()
        db.refresh(record)
        return CustomerReviewService.to_schema(record)

    @staticmethod
    def get_by_review_id(
        db: Session, review_id: str
    ) -> Optional[CustomerReviewOutput]:
        """Fetch a stored review by its canonical review_id."""
        record = db.scalar(
            select(CustomerReview).where(CustomerReview.review_id == review_id)
        )
        if not record:
            return None
        return CustomerReviewService.to_schema(record)

    @staticmethod
    def list_reviews(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        urgency_level: Optional[str] = None,
        security_risk_level: Optional[str] = None,
        sentiment_label: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[CustomerReviewOutput], int, int]:
        """Paginated, filterable listing of stored review intelligence."""
        query = select(CustomerReview)

        if category:
            query = query.where(CustomerReview.category == category)
        if urgency_level:
            query = query.where(CustomerReview.urgency_level == urgency_level)
        if security_risk_level:
            query = query.where(
                CustomerReview.security_risk_level == security_risk_level
            )
        if sentiment_label:
            query = query.where(CustomerReview.sentiment_label == sentiment_label)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    CustomerReview.review_id.ilike(term),
                    CustomerReview.subject.ilike(term),
                    CustomerReview.message.ilike(term),
                    CustomerReview.summary_text.ilike(term),
                )
            )

        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        offset = (page - 1) * page_size
        records = list(
            db.scalars(
                query.order_by(CustomerReview.created_at.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
        )

        return (
            [CustomerReviewService.to_schema(r) for r in records],
            int(total),
            total_pages,
        )

    @staticmethod
    def to_schema(record: CustomerReview) -> CustomerReviewOutput:
        """Map a CustomerReview ORM record back to the canonical schema."""
        return CustomerReviewOutput.model_validate(
            {
                "review_id": record.review_id,
                "source": {
                    "source_type": record.source_type,
                    "source_record_id": record.source_record_id,
                    "domain": record.domain,
                    "channel": record.channel,
                },
                "content": {
                    "subject": record.subject,
                    "message": record.message,
                },
                "classification": {
                    "category": record.category,
                    "fine_grained_intent": record.fine_grained_intent,
                    "confidence": record.classification_confidence,
                    "needs_review": record.needs_review,
                },
                "sentiment": {
                    "label": record.sentiment_label,
                    "score": record.sentiment_score,
                },
                "keywords": record.keywords or [],
                "summary": {"text": record.summary_text},
                "clustering": {
                    "cluster_id": record.cluster_id,
                    "cluster_name": record.cluster_name,
                    "similarity_score": record.cluster_similarity_score,
                },
                "urgency": {
                    "level": record.urgency_level,
                    "score": record.urgency_score,
                    "reasons": record.urgency_reasons or [],
                },
                "resolution": {
                    "status": record.resolution_status,
                    "confidence": record.resolution_confidence,
                    "evidence": record.resolution_evidence or [],
                },
                "security": {
                    "risk_level": record.security_risk_level,
                    "risk_score": record.security_risk_score,
                    "phishing": record.phishing
                    or {"detected": False, "confidence": 0.0},
                    "urls": record.urls or [],
                    "email_addresses": record.email_addresses or [],
                    "social_engineering": record.social_engineering
                    or {"detected": False, "techniques": []},
                    "reasons": record.security_reasons or [],
                },
                "overall_risk": {
                    "level": record.overall_risk_level,
                    "score": record.overall_risk_score,
                    "factors": record.overall_risk_factors or [],
                },
                "recommendation": {
                    "primary_action": record.primary_action,
                    "priority": record.priority,
                    "secondary_actions": record.secondary_actions or [],
                    "rationale": record.recommendation_rationale,
                },
                "model_metadata": record.model_metadata or {},
                "processing": {
                    "processed_at": record.created_at.isoformat()
                    if record.created_at
                    else datetime.now(timezone.utc).isoformat(),
                    "processing_time_ms": record.processing_time_ms,
                    "warnings": record.warnings or [],
                },
            }
        )

    # Re-exported so the API layer can translate client errors without
    # importing the ML client directly.
    MLServiceError = MLServiceError
