"""Tests for the Customer Review Intelligence pipeline:

Backend schema validation, persistence service, API endpoints, and the
ML service client contract (mocked HTTP).
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Setup sys.path for Backend before local imports (mirrors other test modules)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.models.review import CustomerReview
from app.schemas.review import CustomerReviewOutput
from app.services.ml_service_client import MLServiceError, analyze_review_via_ml
from app.services.customer_review_service import (
    CustomerReviewError,
    CustomerReviewService,
)


def make_review_payload(review_id: str = "REV-TEST-001") -> dict:
    """A canonical CustomerReviewOutput payload matching the ML contract."""
    return {
        "review_id": review_id,
        "source": {
            "source_type": "KAGGLE",
            "source_record_id": "12345",
            "domain": "E-commerce/Retail",
            "channel": "Email",
        },
        "content": {
            "subject": "Unauthorized charge on my card",
            "message": "I noticed an unauthorized charge of $350. Please reverse it.",
        },
        "classification": {
            "category": "PAYMENT_TRANSACTION_ISSUE",
            "fine_grained_intent": "unauthorized_charge",
            "confidence": 0.92,
            "needs_review": False,
        },
        "sentiment": {"label": "NEGATIVE", "score": 0.85},
        "keywords": ["unauthorized charge", "refund"],
        "summary": {"text": "Customer reports an unauthorized card charge."},
        "clustering": {
            "cluster_id": "cluster_03",
            "cluster_name": "Payment Issues",
            "similarity_score": 0.81,
        },
        "urgency": {
            "level": "HIGH",
            "score": 0.78,
            "reasons": ["Immediate refund demanded"],
        },
        "resolution": {
            "status": "UNRESOLVED",
            "confidence": 0.7,
            "evidence": ["refund requested"],
        },
        "security": {
            "risk_level": "MEDIUM",
            "risk_score": 0.65,
            "phishing": {"detected": False, "confidence": 0.0},
            "urls": [],
            "email_addresses": [],
            "social_engineering": {"detected": False, "techniques": []},
            "reasons": [],
        },
        "overall_risk": {
            "level": "HIGH",
            "score": 0.72,
            "factors": ["Urgency: Immediate refund demanded"],
        },
        "recommendation": {
            "primary_action": "ESCALATE_TO_PAYMENT_TEAM",
            "priority": "HIGH",
            "secondary_actions": ["MONITOR"],
            "rationale": "Unauthorized charge with high urgency.",
        },
        "model_metadata": {
            "classifier": "complaint_classifier_v1",
            "intent_classifier": "intent_classifier_v1",
            "clusterer": "clusterer_v1",
            "sentiment_model": "gemini",
            "summarizer": "extractive_v1",
        },
        "processing": {
            "processed_at": "2026-09-19T00:00:00+00:00",
            "processing_time_ms": 42.5,
            "warnings": [],
        },
    }


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestReviewSchema:
    def test_canonical_payload_validates(self):
        review = CustomerReviewOutput.model_validate(make_review_payload())
        assert review.review_id == "REV-TEST-001"
        assert review.classification.category == "PAYMENT_TRANSACTION_ISSUE"
        assert review.security.risk_level == "MEDIUM"

    def test_confidence_bounds_enforced(self):
        bad = make_review_payload()
        bad["classification"]["confidence"] = 1.5
        with pytest.raises(Exception):
            CustomerReviewOutput.model_validate(bad)

    def test_missing_required_section_rejected(self):
        bad = make_review_payload()
        del bad["urgency"]
        with pytest.raises(Exception):
            CustomerReviewOutput.model_validate(bad)


# ---------------------------------------------------------------------------
# ML service client (mocked HTTP)
# ---------------------------------------------------------------------------


class TestMLServiceClient:
    def test_successful_call_returns_validated_review(self):
        with patch("app.services.ml_service_client.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200, json=lambda: make_review_payload()
            )
            review = analyze_review_via_ml({"message": "hello"})
        assert review.review_id == "REV-TEST-001"

    def test_connection_error_raises_503(self):
        import httpx

        with patch(
            "app.services.ml_service_client.httpx.post",
            side_effect=httpx.ConnectError("boom"),
        ):
            with pytest.raises(MLServiceError) as exc_info:
                analyze_review_via_ml({"message": "hello"})
        assert exc_info.value.status_code == 503

    def test_non_200_raises_502(self):
        with patch("app.services.ml_service_client.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=500, text="oops")
            with pytest.raises(MLServiceError) as exc_info:
                analyze_review_via_ml({"message": "hello"})
        assert exc_info.value.status_code == 502

    def test_schema_mismatch_raises_502(self):
        with patch("app.services.ml_service_client.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200, json=lambda: {"unexpected": "shape"}
            )
            with pytest.raises(MLServiceError) as exc_info:
                analyze_review_via_ml({"message": "hello"})
        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Persistence service (mocked DB session)
# ---------------------------------------------------------------------------


class TestCustomerReviewService:
    def test_persist_maps_all_fields(self):
        db = MagicMock()
        db.scalar.return_value = None  # no existing record
        review = CustomerReviewOutput.model_validate(make_review_payload())

        CustomerReviewService.persist(db, review)

        added = db.add.call_args[0][0]
        assert isinstance(added, CustomerReview)
        assert added.review_id == "REV-TEST-001"
        assert added.category == "PAYMENT_TRANSACTION_ISSUE"
        assert added.urgency_level == "HIGH"
        assert added.security_risk_level == "MEDIUM"
        assert added.primary_action == "ESCALATE_TO_PAYMENT_TEAM"
        db.commit.assert_called_once()

    def test_persist_updates_existing_record(self):
        db = MagicMock()
        existing = CustomerReview(
            id=uuid.uuid4(), review_id="REV-TEST-001", message="old"
        )
        db.scalar.return_value = existing
        review = CustomerReviewOutput.model_validate(make_review_payload())

        CustomerReviewService.persist(db, review)

        assert existing.category == "PAYMENT_TRANSACTION_ISSUE"
        db.add.assert_not_called()
        db.commit.assert_called_once()

    def test_analyze_and_persist_rejects_empty_message(self):
        db = MagicMock()
        with pytest.raises(CustomerReviewError) as exc_info:
            CustomerReviewService.analyze_and_persist(db, message="   ")
        assert exc_info.value.status_code == 400

    def test_analyze_and_persist_translates_ml_error(self):
        db = MagicMock()
        with patch(
            "app.services.customer_review_service.analyze_review_via_ml",
            side_effect=MLServiceError("unreachable", status_code=503),
        ):
            with pytest.raises(CustomerReviewError) as exc_info:
                CustomerReviewService.analyze_and_persist(db, message="hello")
        assert exc_info.value.status_code == 503

    def test_roundtrip_via_to_schema(self):
        record = CustomerReview(
            id=uuid.uuid4(),
            review_id="REV-RT-1",
            source_type="KAGGLE",
            source_record_id="7",
            domain="E-commerce/Retail",
            channel="Email",
            subject="Sub",
            message="Msg",
            category="OTHER",
            fine_grained_intent=None,
            classification_confidence=0.5,
            needs_review=False,
            sentiment_label="NEUTRAL",
            sentiment_score=0.5,
            keywords=[],
            summary_text="s",
            cluster_id="cluster_00",
            cluster_name="General",
            cluster_similarity_score=0.5,
            urgency_level="LOW",
            urgency_score=0.2,
            urgency_reasons=[],
            resolution_status="UNKNOWN",
            resolution_confidence=0.5,
            resolution_evidence=[],
            security_risk_level="SAFE",
            security_risk_score=0.0,
            phishing={"detected": False, "confidence": 0.0},
            urls=[],
            email_addresses=[],
            social_engineering={"detected": False, "techniques": []},
            security_reasons=[],
            overall_risk_level="SAFE",
            overall_risk_score=0.0,
            overall_risk_factors=[],
            primary_action="STANDARD_SUPPORT_RESPONSE",
            priority="NORMAL",
            secondary_actions=[],
            recommendation_rationale="r",
            model_metadata={},
            processing_time_ms=1.0,
            warnings=[],
        )
        review = CustomerReviewService.to_schema(record)
        assert review.review_id == "REV-RT-1"
        assert review.source.source_record_id == "7"
        assert review.security.phishing.detected is False


# ---------------------------------------------------------------------------
# API endpoints (mocked DB)
# ---------------------------------------------------------------------------


class TestReviewAPI:
    @pytest.mark.asyncio
    async def test_post_reviews_persists_and_returns_201(self, override_db):
        override_db.scalar.return_value = None
        with patch(
            "app.services.customer_review_service.analyze_review_via_ml",
            return_value=CustomerReviewOutput.model_validate(make_review_payload()),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/reviews",
                    json={
                        "message": "I noticed an unauthorized charge of $350.",
                        "subject": "Unauthorized charge on my card",
                        "source_record_id": "12345",
                    },
                )
        assert response.status_code == 201
        data = response.json()
        assert data["review_id"] == "REV-TEST-001"
        assert data["classification"]["category"] == "PAYMENT_TRANSACTION_ISSUE"
        assert "clustering" in data
        assert "overall_risk" in data

    @pytest.mark.asyncio
    async def test_post_reviews_empty_message_400(self, override_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/reviews", json={"message": "  "})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_reviews_ml_unreachable_503(self, override_db):
        override_db.scalar.return_value = None
        with patch(
            "app.services.customer_review_service.analyze_review_via_ml",
            side_effect=MLServiceError("unreachable", status_code=503),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/reviews", json={"message": "hello"}
                )
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_get_review_returns_stored_record(self, override_db):
        stored = CustomerReviewOutput.model_validate(make_review_payload("REV-GET-1"))
        with patch(
            "app.services.customer_review_service.CustomerReviewService.get_by_review_id",
            return_value=stored,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/reviews/REV-GET-1")
        assert response.status_code == 200
        assert response.json()["review_id"] == "REV-GET-1"

    @pytest.mark.asyncio
    async def test_get_review_404_when_missing(self, override_db):
        with patch(
            "app.services.customer_review_service.CustomerReviewService.get_by_review_id",
            return_value=None,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/reviews/REV-MISSING")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_reviews_paginated(self, override_db):
        stored = CustomerReviewOutput.model_validate(make_review_payload("REV-L-1"))
        with patch(
            "app.services.customer_review_service.CustomerReviewService.list_reviews",
            return_value=([stored], 1, 1),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/reviews",
                    params={"page": 1, "page_size": 10, "category": "OTHER"},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["review_id"] == "REV-L-1"
