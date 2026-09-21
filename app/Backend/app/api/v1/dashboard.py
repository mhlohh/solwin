from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import (
    CustomerAnalyticsResponse,
    DashboardOverviewResponse,
    IssueFrequency,
    RecentThreat,
    SecurityAnalyticsResponse,
    TrendResponse,
)
from app.services.analytics_service import AnalyticsService

# Router for dashboard overview
dashboard_router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

# Router for deep customer and security analytics
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ============================================================================
# Dashboard Overview
# ============================================================================


@dashboard_router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated dashboard overview metrics",
    description=(
        "Retrieve pre-aggregated overview metrics covering conversation statuses, "
        "sentiment distribution, category distribution, threat counts, "
        "and risk distribution."
    ),
)
def get_dashboard_overview(db: Session = Depends(get_db)):
    return AnalyticsService.get_dashboard_overview(db=db)


# ============================================================================
# Customer Support Analytics
# ============================================================================


@analytics_router.get(
    "/customer",
    response_model=CustomerAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer support intelligence analytics",
    description=(
        "Retrieve detailed customer support metrics including sentiment, category, "
        "priority, and resolution distributions, along with top reported issues."
    ),
)
def get_customer_analytics(db: Session = Depends(get_db)):
    return AnalyticsService.get_customer_analytics(db=db)


@analytics_router.get(
    "/customer/top-issues",
    response_model=List[IssueFrequency],
    status_code=status.HTTP_200_OK,
    summary="Get most frequently reported customer issues",
    description=(
        "Retrieve the most frequently occurring customer issues "
        "from analysis records."
    ),
)
def get_top_issues(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of issue frequencies to return",
    ),
    db: Session = Depends(get_db),
):
    return AnalyticsService.get_top_issues(db=db, limit=limit)


@analytics_router.get(
    "/customer/trends",
    response_model=TrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer conversation trends over time",
    description=(
        "Retrieve conversation counts grouped by UTC date for "
        "the specified number of days."
    ),
)
def get_customer_trends(
    days: int = Query(
        default=30,
        ge=1,
        le=90,
        description="Number of past days for trend evaluation (max 90)",
    ),
    db: Session = Depends(get_db),
):
    return AnalyticsService.get_customer_trends(db=db, days=days)


# ============================================================================
# Security Intelligence Analytics
# ============================================================================


@analytics_router.get(
    "/security",
    response_model=SecurityAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get security intelligence analytics",
    description=(
        "Retrieve security metrics including threat detection counts, risk levels, "
        "technique frequency, suspicious link counts, and recent critical threats."
    ),
)
def get_security_analytics(db: Session = Depends(get_db)):
    return AnalyticsService.get_security_analytics(db=db)


@analytics_router.get(
    "/security/recent-threats",
    response_model=List[RecentThreat],
    status_code=status.HTTP_200_OK,
    summary="Get recent security threats",
    description="Retrieve the most recent confirmed threats for security team review.",
)
def get_recent_threats(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of recent threats to return",
    ),
    db: Session = Depends(get_db),
):
    return AnalyticsService.get_recent_threats(db=db, limit=limit)


@analytics_router.get(
    "/security/trends",
    response_model=TrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get security threat trends over time",
    description=(
        "Retrieve confirmed threat counts grouped by UTC date for "
        "the specified number of days."
    ),
)
def get_security_trends(
    days: int = Query(
        default=30,
        ge=1,
        le=90,
        description="Number of past days for trend evaluation (max 90)",
    ),
    db: Session = Depends(get_db),
):
    return AnalyticsService.get_security_trends(db=db, days=days)
