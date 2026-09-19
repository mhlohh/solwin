import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.campaign import Campaign
from app.models.enums import CampaignStatus
from app.models.threat import Threat
from app.services.campaign.correlation import (
    calculate_threat_correlation,
    derive_campaign_risk,
    generate_campaign_name,
    get_threat_indicators,
)

logger = get_logger("solwin.campaign_service")

# Minimum correlation score required to attach to or start a campaign
CAMPAIGN_CORRELATION_THRESHOLD = 40


class CampaignService:
    """Service managing threat correlation, campaign creation, and campaign radar."""

    @staticmethod
    def correlate_threat(db: Session, new_threat: Threat) -> Optional[Campaign]:
        """Correlate a newly persisted threat with existing threats and campaigns.

        Rules:
        - If new_threat is already attached to a campaign, do nothing.
        - Query existing threats that share at least one candidate indicator.
        - Calculate deterministic pairwise correlation.
        - If matching an existing campaign: attach threat, update timestamps & risk.
        - If matching another unattached threat with score >= threshold:
          create new Campaign, attach both threats.
        - Isolated threats (no matches >= threshold) do not create a campaign.
        """
        if new_threat.campaign_id is not None:
            return db.scalar(
                select(Campaign).where(Campaign.id == new_threat.campaign_id)
            )

        new_indicators = get_threat_indicators(new_threat)
        if (
            not new_indicators.urls
            and not new_indicators.domains
            and not new_indicators.emails
            and not new_indicators.email_domains
            and not new_indicators.techniques
        ):
            # No correlation signals available
            return None

        # 1. Candidate query: look for other threats with threat_detected=True
        # excluding new_threat itself
        stmt = (
            select(Threat)
            .where(
                Threat.id != new_threat.id,
                Threat.threat_detected == True,  # noqa: E712
            )
            .order_by(Threat.created_at.desc())
            .limit(100)
        )
        candidates = list(db.scalars(stmt).all())

        best_score = 0
        best_candidate: Optional[Threat] = None
        best_match = None

        for candidate in candidates:
            cand_indicators = get_threat_indicators(candidate)
            match = calculate_threat_correlation(new_indicators, cand_indicators)
            if match.score > best_score:
                best_score = match.score
                best_candidate = candidate
                best_match = match

        if best_score < CAMPAIGN_CORRELATION_THRESHOLD or best_candidate is None:
            logger.info(
                "Threat %s has no strong correlations (best: %s).",
                new_threat.id,
                best_score,
            )
            return None

        # 2. Case A: Candidate already belongs to a campaign -> attach new threat
        if best_candidate.campaign_id is not None:
            campaign = db.scalar(
                select(Campaign).where(Campaign.id == best_candidate.campaign_id)
            )
            if campaign:
                new_threat.campaign_id = campaign.id
                campaign.last_seen_at = max(
                    campaign.last_seen_at,
                    new_threat.created_at or datetime.now(timezone.utc),
                )
                campaign.correlation_score = max(campaign.correlation_score, best_score)
                # Re-evaluate campaign risk with new threat
                all_threats = list(campaign.threats)
                if new_threat not in all_threats:
                    all_threats.append(new_threat)
                campaign.risk_level = derive_campaign_risk(all_threats)
                db.commit()
                db.refresh(campaign)
                logger.info(
                    "Threat %s attached to existing campaign %s (score: %s).",
                    new_threat.id,
                    campaign.name,
                    best_score,
                )
                return campaign

        # 3. Case B: Neither has a campaign, but strongly correlate -> Create
        now = datetime.now(timezone.utc)
        first_seen = min(
            candidate.created_at or now,
            new_threat.created_at or now,
        )
        last_seen = max(
            candidate.created_at or now,
            new_threat.created_at or now,
        )

        # Collect shared indicators for naming & description
        shared_domains = set(new_indicators.domains) | set(
            get_threat_indicators(best_candidate).domains
        )
        shared_email_domains = set(new_indicators.email_domains) | set(
            get_threat_indicators(best_candidate).email_domains
        )
        shared_techs = set(new_indicators.techniques) | set(
            get_threat_indicators(best_candidate).techniques
        )
        shared_types = {
            new_indicators.threat_type,
            best_candidate.threat_type or "NONE",
        }

        campaign_name = generate_campaign_name(
            domains=shared_domains,
            email_domains=shared_email_domains,
            techniques=shared_techs,
            threat_types=shared_types,
        )

        initial_threats = [new_threat, best_candidate]
        campaign_risk = derive_campaign_risk(initial_threats)

        reasons_text = "; ".join(best_match.reasons) if best_match else ""
        description = (
            f"Correlated threat activity cluster (score: {best_score}/100). "
            f"Signals: {reasons_text}"
        )

        campaign = Campaign(
            id=uuid.uuid4(),
            name=campaign_name,
            description=description,
            risk_level=campaign_risk,
            status=CampaignStatus.ACTIVE,
            correlation_score=best_score,
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            created_at=now,
            updated_at=now,
        )
        db.add(campaign)
        db.flush()

        new_threat.campaign_id = campaign.id
        best_candidate.campaign_id = campaign.id
        db.commit()
        db.refresh(campaign)

        logger.info(
            f"Created new campaign '{campaign.name}' ({campaign.id}) linking threats "
            f"{new_threat.id} and {best_candidate.id}."
        )
        return campaign

    @staticmethod
    def list_campaigns(
        db: Session,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Campaign], int]:
        """List campaigns with filtering and pagination."""
        query = select(Campaign)

        if status:
            query = query.where(Campaign.status == status.upper())
        if risk_level:
            query = query.where(Campaign.risk_level == risk_level.upper())
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Campaign.name.ilike(term),
                    Campaign.description.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_stmt) or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = (
            query.order_by(Campaign.last_seen_at.desc()).offset(offset).limit(page_size)
        )
        items = list(db.scalars(stmt).all())
        return items, total

    @staticmethod
    def get_campaign_detail(db: Session, campaign_id: uuid.UUID) -> Optional[Campaign]:
        """Retrieve a campaign and its associated threats."""
        return db.scalar(select(Campaign).where(Campaign.id == campaign_id))

    @staticmethod
    def update_campaign_status(
        db: Session, campaign_id: uuid.UUID, new_status: CampaignStatus
    ) -> Optional[Campaign]:
        """Update campaign status."""
        campaign = db.scalar(select(Campaign).where(Campaign.id == campaign_id))
        if not campaign:
            return None
        campaign.status = new_status
        campaign.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def get_radar_summary(db: Session) -> dict:
        """Get dashboard-ready Campaign Radar summary using aggregation."""
        total_campaigns = db.scalar(select(func.count(Campaign.id))) or 0
        active_campaigns = (
            db.scalar(
                select(func.count(Campaign.id)).where(
                    Campaign.status == CampaignStatus.ACTIVE
                )
            )
            or 0
        )
        critical_campaigns = (
            db.scalar(
                select(func.count(Campaign.id)).where(Campaign.risk_level == "CRITICAL")
            )
            or 0
        )
        high_risk_campaigns = (
            db.scalar(
                select(func.count(Campaign.id)).where(Campaign.risk_level == "HIGH")
            )
            or 0
        )

        # Recent campaigns
        recent_stmt = select(Campaign).order_by(Campaign.last_seen_at.desc()).limit(5)
        recent_campaigns = list(db.scalars(recent_stmt).all())

        # Extract top shared domains & email domains from active campaigns
        active_stmt = select(Campaign).where(Campaign.status == CampaignStatus.ACTIVE)
        active_list = list(db.scalars(active_stmt).all())

        domain_counts: dict[str, int] = {}
        email_domain_counts: dict[str, int] = {}
        technique_counts: dict[str, int] = {}

        for camp in active_list:
            for threat in camp.threats:
                ind = get_threat_indicators(threat)
                for d in ind.domains:
                    domain_counts[d] = domain_counts.get(d, 0) + 1
                for ed in ind.email_domains:
                    email_domain_counts[ed] = email_domain_counts.get(ed, 0) + 1
                for t in ind.techniques:
                    technique_counts[t] = technique_counts.get(t, 0) + 1

        top_domains = sorted(
            [{"domain": k, "count": v} for k, v in domain_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        top_email_domains = sorted(
            [{"domain": k, "count": v} for k, v in email_domain_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        top_techniques = sorted(
            [{"technique": k, "count": v} for k, v in technique_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        return {
            "total_campaigns": total_campaigns,
            "active_campaigns": active_campaigns,
            "critical_campaigns": critical_campaigns,
            "high_risk_campaigns": high_risk_campaigns,
            "top_shared_domains": top_domains,
            "top_shared_email_domains": top_email_domains,
            "most_common_techniques": top_techniques,
            "recent_campaigns": recent_campaigns,
        }
