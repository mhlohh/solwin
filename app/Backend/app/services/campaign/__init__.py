from app.services.campaign.campaign_service import (
    CAMPAIGN_CORRELATION_THRESHOLD,
    CampaignService,
)
from app.services.campaign.correlation import (
    CorrelationMatch,
    ThreatIndicators,
    calculate_threat_correlation,
    derive_campaign_risk,
    extract_domain,
    extract_email_domain,
    generate_campaign_name,
    get_threat_indicators,
)

__all__ = [
    "CAMPAIGN_CORRELATION_THRESHOLD",
    "CampaignService",
    "CorrelationMatch",
    "ThreatIndicators",
    "calculate_threat_correlation",
    "derive_campaign_risk",
    "extract_domain",
    "extract_email_domain",
    "generate_campaign_name",
    "get_threat_indicators",
]
