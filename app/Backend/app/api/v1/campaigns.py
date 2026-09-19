import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.enums import UserRole
from app.schemas.campaign import (
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignRadarResponse,
    CampaignStatusUpdate,
    CampaignSummary,
    CampaignThreatRead,
    SharedIndicators,
)
from app.services.campaign.campaign_service import CampaignService
from app.services.campaign.correlation import get_threat_indicators

router = APIRouter(
    prefix="/campaigns",
    tags=["Campaigns"],
)


def _build_shared_indicators(threats) -> SharedIndicators:
    """Helper to collect shared indicators across threats in a campaign."""
    domains = set()
    urls = set()
    email_domains = set()
    emails = set()
    techniques = set()
    threat_types = set()

    for threat in threats:
        ind = get_threat_indicators(threat)
        domains.update(ind.domains)
        urls.update(ind.urls)
        email_domains.update(ind.email_domains)
        emails.update(ind.emails)
        techniques.update(ind.techniques)
        if ind.threat_type and ind.threat_type != "NONE":
            threat_types.add(ind.threat_type)

    return SharedIndicators(
        domains=sorted(list(domains)),
        urls=sorted(list(urls)),
        email_domains=sorted(list(email_domains)),
        emails=sorted(list(emails)),
        techniques=sorted(list(techniques)),
        threat_types=sorted(list(threat_types)),
    )


@router.get(
    "/radar",
    response_model=CampaignRadarResponse,
    summary="Get Campaign Radar overview metrics",
    dependencies=[
        Depends(
            require_role(
                UserRole.SUPPORT_MANAGER,
                UserRole.SECURITY_ANALYST,
                UserRole.ADMIN,
            )
        )
    ],
)
def get_campaign_radar(
    db: Session = Depends(get_db),
) -> CampaignRadarResponse:
    data = CampaignService.get_radar_summary(db)
    recent_summaries = []
    for camp in data["recent_campaigns"]:
        recent_summaries.append(
            CampaignSummary(
                id=camp.id,
                name=camp.name,
                description=camp.description,
                risk_level=camp.risk_level,
                status=camp.status,
                correlation_score=camp.correlation_score,
                threat_count=len(camp.threats),
                first_seen_at=camp.first_seen_at,
                last_seen_at=camp.last_seen_at,
                created_at=camp.created_at,
                updated_at=camp.updated_at,
            )
        )

    return CampaignRadarResponse(
        total_campaigns=data["total_campaigns"],
        active_campaigns=data["active_campaigns"],
        critical_campaigns=data["critical_campaigns"],
        high_risk_campaigns=data["high_risk_campaigns"],
        top_shared_domains=data["top_shared_domains"],
        top_shared_email_domains=data["top_shared_email_domains"],
        most_common_techniques=data["most_common_techniques"],
        recent_campaigns=recent_summaries,
    )


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List correlated campaigns with filtering and pagination",
    dependencies=[
        Depends(
            require_role(
                UserRole.SUPPORT_MANAGER,
                UserRole.SECURITY_ANALYST,
                UserRole.ADMIN,
            )
        )
    ],
)
def list_campaigns(
    status: Optional[str] = Query(
        None, description="Filter by status (ACTIVE, MONITORED, RESOLVED)"
    ),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    search: Optional[str] = Query(
        None, description="Search campaign name or description"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> CampaignListResponse:
    items, total = CampaignService.list_campaigns(
        db=db,
        status=status,
        risk_level=risk_level,
        search=search,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, math.ceil(total / page_size))

    summaries = []
    for camp in items:
        summaries.append(
            CampaignSummary(
                id=camp.id,
                name=camp.name,
                description=camp.description,
                risk_level=camp.risk_level,
                status=camp.status,
                correlation_score=camp.correlation_score,
                threat_count=len(camp.threats),
                first_seen_at=camp.first_seen_at,
                last_seen_at=camp.last_seen_at,
                created_at=camp.created_at,
                updated_at=camp.updated_at,
            )
        )

    return CampaignListResponse(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignDetailResponse,
    summary="Get details for a specific campaign",
    dependencies=[
        Depends(
            require_role(
                UserRole.SUPPORT_MANAGER,
                UserRole.SECURITY_ANALYST,
                UserRole.ADMIN,
            )
        )
    ],
)
def get_campaign(
    campaign_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CampaignDetailResponse:
    campaign = CampaignService.get_campaign_detail(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found.",
        )

    threat_reads = [
        CampaignThreatRead(
            id=t.id,
            conversation_id=t.conversation_id,
            threat_type=t.threat_type,
            risk_level=t.risk_level,
            suspicious_urls=t.suspicious_urls or [],
            suspicious_emails=t.suspicious_emails or [],
            techniques=t.techniques or [],
            created_at=t.created_at,
        )
        for t in campaign.threats
    ]

    shared_indicators = _build_shared_indicators(campaign.threats)

    return CampaignDetailResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        risk_level=campaign.risk_level,
        status=campaign.status,
        correlation_score=campaign.correlation_score,
        threat_count=len(campaign.threats),
        first_seen_at=campaign.first_seen_at,
        last_seen_at=campaign.last_seen_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        threats=threat_reads,
        shared_indicators=shared_indicators,
    )


@router.patch(
    "/{campaign_id}/status",
    response_model=CampaignSummary,
    summary="Update status of a campaign",
    dependencies=[
        Depends(
            require_role(
                UserRole.SECURITY_ANALYST,
                UserRole.ADMIN,
            )
        )
    ],
)
def update_campaign_status(
    campaign_id: uuid.UUID,
    payload: CampaignStatusUpdate,
    db: Session = Depends(get_db),
) -> CampaignSummary:
    campaign = CampaignService.update_campaign_status(db, campaign_id, payload.status)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found.",
        )

    return CampaignSummary(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        risk_level=campaign.risk_level,
        status=campaign.status,
        correlation_score=campaign.correlation_score,
        threat_count=len(campaign.threats),
        first_seen_at=campaign.first_seen_at,
        last_seen_at=campaign.last_seen_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )
