import re
from datetime import UTC, datetime

from ml_service.api.schemas import EmailAnalysis, SecurityRiskLevel

EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

FREE_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "protonmail.com",
    "mail.com",
    "zoho.com",
}

DISPOSABLE_DOMAINS = {
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com",
    "throwawaymail.com",
    "yopmail.com",
    "sharklasers.com",
    "mailinator.com",
}

# Major brands commonly targeted by lookalike typosquatting
TARGET_BRANDS = [
    ("amazon", ["amaz0n", "arnazon", "amzon", "amazone", "amazn"]),
    ("google", ["g00gle", "goog1e", "googel", "g0ogle", "g0og1e", "g00gl"]),
    ("paypal", ["paypa1", "paypai", "pay-pal", "paypall", "paypa-l"]),
    ("microsoft", ["micros0ft", "m1crosoft", "micro-soft", "m1cr0soft"]),
    ("shopzilla", ["shopzi11a", "shopzila", "shop-zilla", "sh0pzilla"]),
    ("apple", ["app1e", "app-le", "appl-e"]),
    ("netflix", ["netf1ix", "net-flix", "netfllx", "netflx"]),
]



class EmailAnalyzer:
    """Extracts and analyzes email addresses for typosquatting, spoofing, and domain risk."""

    def __init__(self) -> None:
        pass

    def extract_emails(self, text: str | None) -> list[str]:
        if not text:
            return []
        found = EMAIL_REGEX.findall(text)
        seen = set()
        clean = []
        for e in found:
            norm = e.lower().strip()
            if norm not in seen:
                seen.add(norm)
                clean.append(norm)
        return clean

    def analyze_email(self, raw_email: str) -> EmailAnalysis:
        email = raw_email.lower().strip()
        parts = email.split("@")
        domain = parts[1] if len(parts) == 2 else ""

        reasons: list[str] = []
        risk_score = 0.0

        is_free = domain in FREE_PROVIDERS
        is_disposable = domain in DISPOSABLE_DOMAINS

        if is_disposable:
            reasons.append("disposable_temporary_email_domain")
            risk_score += 0.60

        if "xn--" in domain:
            reasons.append("punycode_homograph_domain")
            risk_score += 0.50

        # Extract registrable domain and label
        domain_parts = domain.split(".")
        domain_label = domain_parts[0] if domain_parts else domain

        # Check lookalike typosquatting against major brands
        for brand, lookalikes in TARGET_BRANDS:
            # 1. Authentic brand domain check: If exact domain label is the authentic brand, do not flag as typosquat
            if domain_label == brand:
                continue

            # 2. Check known lookalike variants matching domain label or containing specific typosquat tokens
            for la in lookalikes:
                if la == domain_label or (len(la) >= 5 and la in domain_label):
                    reasons.append(f"typosquatting_lookalike_of_{brand}")
                    risk_score += 0.70
                    break

            # 3. Check brand followed by suspicious suffix like amazon-security, paypal-support
            if (f"{brand}-" in domain or f"{brand}support" in domain or f"{brand}security" in domain) and domain not in {
                f"{brand}.com",
                f"{brand}.org",
                f"{brand}.net",
            }:
                reasons.append(f"unauthorized_brand_impersonation_{brand}")
                risk_score += 0.65

        # Check numeric character substitution in domain (e.g., paypa1, amaz0n)
        if re.search(r"[0-9]", domain_label) and not is_free and not is_disposable:
            reasons.append("numeric_character_in_domain_name")
            risk_score += 0.15


        # Check multiple hyphenation
        if domain.count("-") >= 2:
            reasons.append("excessive_hyphenation_in_domain")
            risk_score += 0.20

        risk_score = min(round(risk_score, 4), 1.0)

        # Categorize risk level
        if risk_score >= 0.60:
            risk_level = SecurityRiskLevel.HIGH
        elif risk_score >= 0.35:
            risk_level = SecurityRiskLevel.MEDIUM
        elif risk_score >= 0.10:
            risk_level = SecurityRiskLevel.LOW
        else:
            risk_level = SecurityRiskLevel.SAFE

        if not reasons:
            reasons.append("valid_syntax_no_anomalies_detected")

        return EmailAnalysis(
            email=email,
            domain=domain,
            risk_level=risk_level,
            risk_score=risk_score,
            reasons=reasons,
            is_free_provider=is_free,
            is_disposable=is_disposable,
            analyzed_at=datetime.now(UTC),
        )

    def analyze_text(self, text: str | None) -> list[EmailAnalysis]:
        emails = self.extract_emails(text)
        return [self.analyze_email(e) for e in emails]
