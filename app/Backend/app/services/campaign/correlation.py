from typing import List, Set
from urllib.parse import urlparse

import tldextract
from pydantic import BaseModel, Field

from app.models.enums import RiskLevel
from app.models.threat import Threat


class ThreatIndicators(BaseModel):
    threat_id: str
    urls: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    email_domains: List[str] = Field(default_factory=list)
    threat_type: str = "NONE"
    techniques: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"


def extract_domain(url: str) -> str:
    """Extract registered domain or hostname from URL using tldextract."""
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    parsed = urlparse(url)
    host = parsed.netloc.split(":")[0].strip().lower()
    ext = tldextract.extract(host)
    # Check for top_domain_under_public_suffix, fallback to fqdn or domain+suffix
    try:
        domain = ext.top_domain_under_public_suffix
    except AttributeError:
        domain = (
            f"{ext.domain}.{ext.suffix}".strip(".")
            if ext.domain and ext.suffix
            else None
        )
    if domain:
        return domain.lower()
    return host


def extract_email_domain(email: str) -> str:
    """Extract domain portion from email address."""
    if not email or "@" not in email:
        return ""
    parts = email.split("@")
    return parts[-1].strip().lower()


def get_threat_indicators(threat: Threat) -> ThreatIndicators:
    """Extract structured indicators from a Threat model instance."""
    urls = [u.strip() for u in (threat.suspicious_urls or []) if u and u.strip()]
    emails = [e.strip() for e in (threat.suspicious_emails or []) if e and e.strip()]

    domains = sorted(list({extract_domain(u) for u in urls if extract_domain(u)}))
    email_domains = sorted(
        list({extract_email_domain(e) for e in emails if extract_email_domain(e)})
    )
    techniques = [t.strip() for t in (threat.techniques or []) if t and t.strip()]

    return ThreatIndicators(
        threat_id=str(threat.id),
        urls=urls,
        domains=domains,
        emails=emails,
        email_domains=email_domains,
        threat_type=threat.threat_type or "NONE",
        techniques=techniques,
        risk_level=threat.risk_level or "LOW",
    )


class CorrelationMatch(BaseModel):
    score: int
    shared_urls: List[str] = Field(default_factory=list)
    shared_domains: List[str] = Field(default_factory=list)
    shared_emails: List[str] = Field(default_factory=list)
    shared_email_domains: List[str] = Field(default_factory=list)
    shared_techniques: List[str] = Field(default_factory=list)
    shared_threat_type: bool = False
    reasons: List[str] = Field(default_factory=list)


def calculate_threat_correlation(
    t1: ThreatIndicators,
    t2: ThreatIndicators,
) -> CorrelationMatch:
    """Deterministically correlate two threats based on shared indicators.

    Scoring Heuristics:
    - EXACT SUSPICIOUS URL MATCH: +50
    - EXACT DOMAIN MATCH: +40
    - EXACT EMAIL DOMAIN MATCH: +30
    - SAME SOCIAL ENGINEERING TECHNIQUE: +10 per shared technique (max 20)
    - SAME THREAT TYPE: +10 (only if threat_type != "NONE")
    - MULTIPLE SHARED INDICATORS: +10 bounded bonus

    Strong indicators (exact URL, domain, email domain) dominate. Generic
    characteristics (urgency, same threat type) contribute weakly and
    CANNOT alone breach the threshold (>= 40) required for campaign grouping.
    Total score capped at 100.
    """
    score = 0
    reasons = []

    # 1. Exact Suspicious URLs
    shared_urls = sorted(list(set(t1.urls) & set(t2.urls)))
    if shared_urls:
        score += 50
        reasons.append(f"Exact suspicious URL match: {', '.join(shared_urls)}")

    # 2. Exact Domains
    shared_domains = sorted(list(set(t1.domains) & set(t2.domains)))
    if shared_domains:
        score += 40
        reasons.append(f"Exact suspicious domain match: {', '.join(shared_domains)}")

    # 3. Exact Email Domains
    shared_email_domains = sorted(list(set(t1.email_domains) & set(t2.email_domains)))
    # Exclude broad public webmail domains from strong correlation if present
    public_providers = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}
    meaningful_email_domains = [
        d for d in shared_email_domains if d not in public_providers
    ]
    if meaningful_email_domains:
        score += 30
        ed_list = ", ".join(meaningful_email_domains)
        reasons.append(f"Exact suspicious email domain match: {ed_list}")

    # 4. Exact Emails
    shared_emails = sorted(list(set(t1.emails) & set(t2.emails)))
    if shared_emails:
        score += 30
        reasons.append(f"Exact sender email match: {', '.join(shared_emails)}")

    # 5. Shared Social Engineering Techniques (weak, max +20)
    shared_techs = sorted(list(set(t1.techniques) & set(t2.techniques)))
    if shared_techs:
        tech_score = min(len(shared_techs) * 10, 20)
        score += tech_score
        tech_str = "+".join(shared_techs)
        reasons.append(
            f"Shared social engineering techniques ({tech_str}): +{tech_score}"
        )

    # 6. Same Threat Type (weak, +10)
    shared_type = False
    if (
        t1.threat_type
        and t2.threat_type
        and t1.threat_type != "NONE"
        and t1.threat_type == t2.threat_type
    ):
        shared_type = True
        score += 10
        reasons.append(f"Same threat type: {t1.threat_type}")

    # 7. Multiple shared indicators bonus (+10)
    strong_indicators_count = (
        bool(shared_urls)
        + bool(shared_domains)
        + bool(meaningful_email_domains)
        + bool(shared_emails)
    )
    if strong_indicators_count >= 2:
        score += 10
        reasons.append("Multi-indicator correlation bonus: +10")

    # Bounded between 0 and 100
    capped_score = min(max(score, 0), 100)

    return CorrelationMatch(
        score=capped_score,
        shared_urls=shared_urls,
        shared_domains=shared_domains,
        shared_emails=shared_emails,
        shared_email_domains=shared_email_domains,
        shared_techniques=shared_techs,
        shared_threat_type=shared_type,
        reasons=reasons,
    )


def generate_campaign_name(
    domains: Set[str],
    email_domains: Set[str],
    techniques: Set[str],
    threat_types: Set[str],
) -> str:
    """Generate a deterministic, human-readable name without false attribution."""
    # 1. Look for known brand or prominent domain
    if domains:
        primary_domain = sorted(list(domains))[0]
        # Clean up tld if desired, e.g. "paypa1-example.com" -> "Paypa1-Example"
        base_name = primary_domain.split(".")[0].replace("-", " ").title()
        return f"{base_name} Lookalike Activity Cluster"

    # 2. Prominent sender domain
    if email_domains:
        primary_email_domain = sorted(list(email_domains))[0]
        base_email = primary_email_domain.split(".")[0].replace("-", " ").title()
        return f"{base_email} Suspicious Sender Cluster"

    # 3. Phishing / Credential Harvesting technique
    if "CREDENTIAL_HARVESTING" in techniques or "OTP_REQUEST" in techniques:
        return "Targeted Credential Harvesting Cluster"

    if "URGENCY" in techniques and "IMPERSONATION" in techniques:
        return "Executive Impersonation Urgency Campaign"

    # 4. Threat Type
    if "PHISHING" in threat_types:
        return "Coordinated Phishing Incident Cluster"

    if "SUSPICIOUS_MESSAGE" in threat_types:
        return "Suspicious Messaging Security Cluster"

    return "Correlated Threat Activity Cluster"


def derive_campaign_risk(threats: List[Threat]) -> RiskLevel:
    """Derive campaign risk level from contained threats and correlation evidence.

    Deterministic Rules:
    - Any CRITICAL threat -> CRITICAL
    - Multiple (>=2) HIGH threats or 1 HIGH with >= 3 threats -> CRITICAL
    - At least one HIGH threat -> HIGH
    - Multiple (>=2) MEDIUM threats -> MEDIUM
    - Single MEDIUM threat -> MEDIUM
    - Otherwise -> LOW
    """
    if not threats:
        return RiskLevel.LOW

    levels = [t.risk_level.upper() if t.risk_level else "LOW" for t in threats]
    critical_count = levels.count("CRITICAL")
    high_count = levels.count("HIGH")
    medium_count = levels.count("MEDIUM")

    if critical_count >= 1:
        return RiskLevel.CRITICAL
    if high_count >= 2 or (high_count >= 1 and len(threats) >= 3):
        return RiskLevel.CRITICAL
    if high_count >= 1:
        return RiskLevel.HIGH
    if medium_count >= 1:
        return RiskLevel.MEDIUM

    return RiskLevel.LOW
