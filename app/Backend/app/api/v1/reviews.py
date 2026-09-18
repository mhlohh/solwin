from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.review import (
    CustomerReviewCreateRequest,
    CustomerReviewOutput,
)
from app.services.customer_review_service import (
    CustomerReviewError,
    CustomerReviewService,
)
from app.services.ml_service_client import MLServiceError

router = APIRouter(
    prefix="/reviews",
    tags=["Customer Review Intelligence"],
)


def _translate_error(exc: Exception) -> HTTPException:
    """Map service-layer errors to HTTP errors."""
    if isinstance(exc, CustomerReviewError):
        return HTTPException(status_code=exc.status_code, detail=exc.message)
    if isinstance(exc, MLServiceError):
        return HTTPException(status_code=exc.status_code, detail=exc.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred during customer review processing.",
    )


@router.post(
    "",
    response_model=CustomerReviewOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze and persist a customer review",
    description=(
        "Runs the canonical Customer Review Intelligence pipeline: forwards "
        "the review to the ML service /analyze/review endpoint, validates the "
        "returned canonical CustomerReviewOutput, persists it to PostgreSQL "
        "and returns the full intelligence record."
    ),
)
def analyze_review(
    payload: CustomerReviewCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        return CustomerReviewService.analyze_and_persist(
            db=db,
            message=payload.message,
            subject=payload.subject,
            review_id=payload.review_id,
            source_type=payload.source_type,
            source_record_id=payload.source_record_id,
            domain=payload.domain,
            channel=payload.channel,
        )
    except (CustomerReviewError, MLServiceError) as exc:
        raise _translate_error(exc) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise _translate_error(exc) from exc


@router.get(
    "",
    response_model=PaginatedResponse[CustomerReviewOutput],
    status_code=status.HTTP_200_OK,
    summary="List customer review intelligence records",
    description=(
        "Retrieve a paginated list of persisted customer review intelligence "
        "records with optional filtering by category, urgency, security risk "
        "and sentiment, plus text search across review id, subject, message "
        "and summary."
    ),
)
def list_reviews(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    category: Optional[str] = Query(None, description="Filter by canonical category"),
    urgency_level: Optional[str] = Query(None, description="Filter by urgency level"),
    security_risk_level: Optional[str] = Query(
        None, description="Filter by security risk level"
    ),
    sentiment_label: Optional[str] = Query(
        None, description="Filter by sentiment label"
    ),
    search: Optional[str] = Query(
        None,
        description="Search across review id, subject, message and summary",
    ),
    db: Session = Depends(get_db),
):
    try:
        items, total, total_pages = CustomerReviewService.list_reviews(
            db=db,
            page=page,
            page_size=page_size,
            category=category,
            urgency_level=urgency_level,
            security_risk_level=security_risk_level,
            sentiment_label=sentiment_label,
            search=search,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise _translate_error(exc) from exc

    return PaginatedResponse[CustomerReviewOutput](
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/{review_id}",
    response_model=CustomerReviewOutput,
    status_code=status.HTTP_200_OK,
    summary="Get a stored customer review by id",
    description=(
        "Retrieve a previously persisted canonical customer review "
        "intelligence record without re-invoking the ML service."
    ),
)
def get_review(
    review_id: str,
    db: Session = Depends(get_db),
):
    review = CustomerReviewService.get_by_review_id(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer review '{review_id}' not found.",
        )
    return review
