from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, Priority, RiskLevel
from app.models.threat import Threat
from app.schemas.analytics import (
    CustomerAnalyticsResponse,
    DashboardOverviewResponse,
    IngestedFeedbackStats,
    IssueFrequency,
    RecentThreat,
    SecurityAnalyticsResponse,
    TrendPoint,
    TrendResponse,
)
from app.services.data_service_client import get_ingested_feedback_stats


class AnalyticsService:
    """Service layer for computing pre-aggregated dashboard and intelligence metrics."""

    @staticmethod
    def get_dashboard_overview(db: Session) -> DashboardOverviewResponse:
        """Compute overview metrics across conversations, analyses, and threats."""
        # 1. Aggregate conversation counts by status
        conv_stats = db.execute(
            select(
                func.count(Conversation.id).label("total"),
                func.count(
                    case(
                        (
                            Conversation.status == ConversationStatus.OPEN,
                            Conversation.id,
                        )
                    )
                ).label("open_count"),
                func.count(
                    case(
                        (
                            Conversation.status == ConversationStatus.IN_PROGRESS,
                            Conversation.id,
                        )
                    )
                ).label("in_progress_count"),
                func.count(
                    case(
                        (
                            Conversation.status.in_(
                                [
                                    ConversationStatus.RESOLVED,
                                    ConversationStatus.CLOSED,
                                ]
                            ),
                            Conversation.id,
                        )
                    )
                ).label("resolved_count"),
            )
        ).one()

        total_conv = conv_stats.total or 0
        open_conv = conv_stats.open_count or 0
        in_progress_conv = conv_stats.in_progress_count or 0
        resolved_conv = conv_stats.resolved_count or 0
        unresolved_conv = open_conv + in_progress_conv

        # 2. Urgent conversations count from Analysis priority (HIGH or CRITICAL)
        # Using DISTINCT conversation_id so multiple runs don't inflate urgent count
        urgent_count = (
            db.scalar(
                select(func.count(func.distinct(Analysis.conversation_id))).where(
                    Analysis.priority.in_(
                        [Priority.HIGH.value, Priority.CRITICAL.value]
                    )
                )
            )
            or 0
        )

        # 3. Threat detection metrics
        threat_stats = db.execute(
            select(
                func.count(case((Threat.threat_detected.is_(True), Threat.id))).label(
                    "detected_count"
                ),
                func.count(
                    case(
                        (
                            Threat.threat_detected.is_(True)
                            & (Threat.risk_level == RiskLevel.CRITICAL.value),
                            Threat.id,
                        )
                    )
                ).label("critical_count"),
            )
        ).one()

        threats_detected = threat_stats.detected_count or 0
        critical_threats = threat_stats.critical_count or 0

        # 4. Sentiment distribution
        sentiment_rows = db.execute(
            select(Analysis.sentiment, func.count(Analysis.id))
            .where(Analysis.sentiment.isnot(None))
            .group_by(Analysis.sentiment)
        ).all()
        sentiment_distribution: Dict[str, int] = {
            row[0]: row[1] for row in sentiment_rows if row[0]
        }

        # 5. Category distribution
        category_rows = db.execute(
            select(Analysis.category, func.count(Analysis.id))
            .where(Analysis.category.isnot(None))
            .group_by(Analysis.category)
        ).all()
        category_distribution: Dict[str, int] = {
            row[0]: row[1] for row in category_rows if row[0]
        }

        # 6. Risk distribution
        risk_rows = db.execute(
            select(Threat.risk_level, func.count(Threat.id))
            .where(Threat.risk_level.isnot(None))
            .group_by(Threat.risk_level)
        ).all()
        risk_distribution: Dict[str, int] = {
            row[0]: row[1] for row in risk_rows if row[0]
        }

        # 7. Ingested raw feedback dataset stats (external Data API; degrades to
        # None when unreachable so the dashboard never depends on it).
        ingested = get_ingested_feedback_stats()
        ingested_payload = (
            ingested.model_dump()
            if isinstance(ingested, IngestedFeedbackStats)
            else ingested
        )

        return DashboardOverviewResponse(
            total_conversations=total_conv,
            open_conversations=open_conv,
            in_progress_conversations=in_progress_conv,
            resolved_conversations=resolved_conv,
            unresolved_conversations=unresolved_conv,
            urgent_conversations=urgent_count,
            threats_detected=threats_detected,
            critical_threats=critical_threats,
            sentiment_distribution=sentiment_distribution,
            category_distribution=category_distribution,
            risk_distribution=risk_distribution,
            ingested_feedback=ingested_payload,
        )

    @staticmethod
    def get_customer_analytics(db: Session) -> CustomerAnalyticsResponse:
        """Compute dedicated customer support metrics and issue trends."""
        total_conv = db.scalar(select(func.count(Conversation.id))) or 0

        category_rows = db.execute(
            select(Analysis.category, func.count(Analysis.id))
            .where(Analysis.category.isnot(None))
            .group_by(Analysis.category)
        ).all()
        category_distribution = {row[0]: row[1] for row in category_rows if row[0]}

        sentiment_rows = db.execute(
            select(Analysis.sentiment, func.count(Analysis.id))
            .where(Analysis.sentiment.isnot(None))
            .group_by(Analysis.sentiment)
        ).all()
        sentiment_distribution = {row[0]: row[1] for row in sentiment_rows if row[0]}

        priority_rows = db.execute(
            select(Analysis.priority, func.count(Analysis.id))
            .where(Analysis.priority.isnot(None))
            .group_by(Analysis.priority)
        ).all()
        priority_distribution = {row[0]: row[1] for row in priority_rows if row[0]}

        status_rows = db.execute(
            select(Analysis.resolution_status, func.count(Analysis.id))
            .where(Analysis.resolution_status.isnot(None))
            .group_by(Analysis.resolution_status)
        ).all()
        resolution_status_distribution = {
            row[0]: row[1] for row in status_rows if row[0]
        }

        # Most frequently reported issues (top 10)
        issue_rows = db.execute(
            select(Analysis.issue, func.count(Analysis.id).label("issue_count"))
            .where(Analysis.issue.isnot(None), Analysis.issue != "")
            .group_by(Analysis.issue)
            .order_by(desc("issue_count"))
            .limit(10)
        ).all()
        most_frequently_reported_issues = [
            IssueFrequency(issue=row[0], count=row[1]) for row in issue_rows
        ]

        # Unresolved count from conversation or analysis status
        unresolved_complaint_count = (
            db.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.status.in_(
                        [ConversationStatus.OPEN, ConversationStatus.IN_PROGRESS]
                    )
                )
            )
            or 0
        )

        urgent_complaint_count = (
            db.scalar(
                select(func.count(func.distinct(Analysis.conversation_id))).where(
                    Analysis.priority.in_(
                        [Priority.HIGH.value, Priority.CRITICAL.value]
                    )
                )
            )
            or 0
        )

        return CustomerAnalyticsResponse(
            total_conversations=total_conv,
            category_distribution=category_distribution,
            sentiment_distribution=sentiment_distribution,
            priority_distribution=priority_distribution,
            resolution_status_distribution=resolution_status_distribution,
            most_frequently_reported_issues=most_frequently_reported_issues,
            unresolved_complaint_count=unresolved_complaint_count,
            urgent_complaint_count=urgent_complaint_count,
        )

    @staticmethod
    def get_security_analytics(db: Session) -> SecurityAnalyticsResponse:
        """Compute dedicated security intelligence metrics and technique frequencies."""
        total_threats = db.scalar(select(func.count(Threat.id))) or 0
        threats_detected = (
            db.scalar(
                select(func.count(Threat.id)).where(Threat.threat_detected.is_(True))
            )
            or 0
        )

        risk_rows = db.execute(
            select(Threat.risk_level, func.count(Threat.id))
            .where(Threat.risk_level.isnot(None))
            .group_by(Threat.risk_level)
        ).all()
        risk_distribution = {row[0]: row[1] for row in risk_rows if row[0]}

        threat_type_rows = db.execute(
            select(Threat.threat_type, func.count(Threat.id))
            .where(Threat.threat_type.isnot(None))
            .group_by(Threat.threat_type)
        ).all()
        threat_type_distribution = {
            row[0]: row[1] for row in threat_type_rows if row[0]
        }

        # Query array/JSON fields: techniques, suspicious_urls, suspicious_emails
        # Load JSON columns for threats to aggregate in-memory (cross-DB clean)
        threat_details = db.execute(
            select(
                Threat.techniques,
                Threat.suspicious_urls,
                Threat.suspicious_emails,
            )
        ).all()

        technique_counter: Counter[str] = Counter()
        url_count = 0
        email_count = 0

        for row in threat_details:
            techniques = row[0]
            if techniques and isinstance(techniques, list):
                for tech in techniques:
                    technique_counter[str(tech)] += 1

            urls = row[1]
            if urls and isinstance(urls, list):
                url_count += len(urls)

            emails = row[2]
            if emails and isinstance(emails, list):
                email_count += len(emails)

        # Recent critical threats (limit 10)
        recent_crit_rows = db.execute(
            select(
                Threat.id,
                Threat.conversation_id,
                Threat.threat_type,
                Threat.risk_level,
                Threat.risk_reasons,
                Threat.created_at,
            )
            .where(
                Threat.threat_detected.is_(True),
                Threat.risk_level == RiskLevel.CRITICAL.value,
            )
            .order_by(desc(Threat.created_at))
            .limit(10)
        ).all()

        recent_critical_threats = [
            RecentThreat(
                threat_id=row[0],
                conversation_id=row[1],
                threat_type=row[2],
                risk_level=row[3],
                risk_reasons=row[4] if isinstance(row[4], list) else [],
                created_at=row[5],
            )
            for row in recent_crit_rows
        ]

        return SecurityAnalyticsResponse(
            total_threats=total_threats,
            threats_detected=threats_detected,
            risk_distribution=risk_distribution,
            threat_type_distribution=threat_type_distribution,
            technique_frequency=dict(technique_counter),
            suspicious_url_count=url_count,
            suspicious_email_count=email_count,
            recent_critical_threats=recent_critical_threats,
        )

    @staticmethod
    def get_recent_threats(db: Session, limit: int = 10) -> List[RecentThreat]:
        """Fetch list of most recent detected threats for security team dashboard."""
        capped_limit = max(1, min(limit, 50))
        rows = db.execute(
            select(
                Threat.id,
                Threat.conversation_id,
                Threat.threat_type,
                Threat.risk_level,
                Threat.risk_reasons,
                Threat.created_at,
            )
            .where(Threat.threat_detected.is_(True))
            .order_by(desc(Threat.created_at))
            .limit(capped_limit)
        ).all()

        return [
            RecentThreat(
                threat_id=row[0],
                conversation_id=row[1],
                threat_type=row[2],
                risk_level=row[3],
                risk_reasons=row[4] if isinstance(row[4], list) else [],
                created_at=row[5],
            )
            for row in rows
        ]

    @staticmethod
    def get_top_issues(db: Session, limit: int = 10) -> List[IssueFrequency]:
        """Fetch top reported customer issue descriptions."""
        capped_limit = max(1, min(limit, 50))
        issue_rows = db.execute(
            select(Analysis.issue, func.count(Analysis.id).label("issue_count"))
            .where(Analysis.issue.isnot(None), Analysis.issue != "")
            .group_by(Analysis.issue)
            .order_by(desc("issue_count"))
            .limit(capped_limit)
        ).all()

        return [IssueFrequency(issue=row[0], count=row[1]) for row in issue_rows]

    @staticmethod
    def get_customer_trends(db: Session, days: int = 30) -> TrendResponse:
        """Aggregate customer conversation volume by calendar date (UTC)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        date_expr = func.date(Conversation.created_at)
        rows = db.execute(
            select(
                date_expr.label("c_date"), func.count(Conversation.id).label("c_count")
            )
            .where(Conversation.created_at >= cutoff)
            .group_by(date_expr)
            .order_by(date_expr.asc())
        ).all()

        trend_points = [
            TrendPoint(date=str(row[0]), count=row[1]) for row in rows if row[0]
        ]
        total = sum(pt.count for pt in trend_points)

        return TrendResponse(
            days=days,
            total_count=total,
            trends=trend_points,
        )

    @staticmethod
    def get_security_trends(db: Session, days: int = 30) -> TrendResponse:
        """Aggregate security threat occurrences by calendar date (UTC)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        date_expr = func.date(Threat.created_at)
        rows = db.execute(
            select(date_expr.label("t_date"), func.count(Threat.id).label("t_count"))
            .where(
                Threat.threat_detected.is_(True),
                Threat.created_at >= cutoff,
            )
            .group_by(date_expr)
            .order_by(date_expr.asc())
        ).all()

        trend_points = [
            TrendPoint(date=str(row[0]), count=row[1]) for row in rows if row[0]
        ]
        total = sum(pt.count for pt in trend_points)

        return TrendResponse(
            days=days,
            total_count=total,
            trends=trend_points,
        )
