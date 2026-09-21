import ipaddress
import re
from datetime import UTC, datetime
from urllib.parse import urlparse

from ml_service.api.schemas import SecurityRiskLevel, URLAnalysis

URL_REGEX = re.compile(
    r"(?:(?:https?|ftp):\/\/|www\.)"
    r"(?:[a-zA-Z0-9\-\._~:/?#[\]@!$&\'()*+,;=]|%[0-9a-fA-F]{2})+",
    re.IGNORECASE,
)

KNOWN_SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "is.gd",
    "buff.ly",
    "ow.ly",
    "rb.gy",
    "cutt.ly",
}

SUSPICIOUS_TLDS = {
    "xyz",
    "top",
    "tk",
    "ml",
    "ga",
    "cf",
    "gq",
    "zip",
    "mov",
    "click",
    "fit",
    "country",
    "kim",
}

SUSPICIOUS_PATH_KEYWORDS = [
    r"login",
    r"signin",
    r"verify",
    r"account",
    r"update",
    r"security",
    r"banking",
    r"password",
    r"credential",
    r"invoice",
    r"\.exe$",
    r"\.scr$",
    r"\.zip$",
]


class URLAnalyzer:
    """Extracts and analyzes URLs with deterministic parsing and threat scoring."""

    def __init__(
        self,
        provider_name: str = "internal-heuristic-engine",
        shortener_score_penalty: float = 0.40,
        shortener_min_risk: SecurityRiskLevel = SecurityRiskLevel.MEDIUM,
    ) -> None:
        self.provider_name = provider_name
        self.shortener_score_penalty = shortener_score_penalty
        self.shortener_min_risk = shortener_min_risk
        self.suspicious_path_patterns = [
            re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATH_KEYWORDS
        ]


    def extract_urls(self, text: str | None) -> list[str]:
        if not text:
            return []
        found = URL_REGEX.findall(text)
        # Deduplicate while preserving order
        seen = set()
        clean = []
        for u in found:
            # Strip trailing punctuation often caught in sentences
            stripped = u.rstrip(".,;!?'\")>]} ")
            if stripped and stripped not in seen:
                seen.add(stripped)
                clean.append(stripped)
        return clean

    def analyze_url(self, raw_url: str) -> URLAnalysis:
        url = raw_url.strip()
        if not url.startswith(("http://", "https://", "ftp://")):
            url = "http://" + url

        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower()
        if ":" in domain:
            domain = domain.split(":")[0]

        normalized_url = f"{parsed.scheme.lower()}://{domain}{parsed.path}"
        if parsed.query:
            normalized_url += f"?{parsed.query}"

        signals: list[str] = []
        risk_score = 0.0

        # Check IP host
        try:
            ipaddress.ip_address(domain)
            signals.append("ip_address_host")
            risk_score += 0.40
        except ValueError:
            pass

        # Check punycode / homograph
        if "xn--" in domain:
            signals.append("punycode_homograph_domain")
            risk_score += 0.40

        # Check URL shortener
        is_shortener = domain in KNOWN_SHORTENERS
        if is_shortener:
            signals.append("url_shortener")
            risk_score += self.shortener_score_penalty

        # Check suspicious TLD
        tld = domain.split(".")[-1] if "." in domain else ""
        if tld in SUSPICIOUS_TLDS:
            signals.append(f"suspicious_tld_{tld}")
            risk_score += 0.30

        # Check excessive subdomains
        subdomain_count = len(domain.split(".")) - 2
        if subdomain_count >= 3:
            signals.append("excessive_subdomains")
            risk_score += 0.20

        # Check suspicious keywords in path or query
        full_path = f"{parsed.path}?{parsed.query}".lower()
        matched_keywords = []
        for pat in self.suspicious_path_patterns:
            if pat.search(full_path):
                matched_keywords.append(pat.pattern.replace(r"\b", "").replace("$", ""))
        if matched_keywords:
            signals.append(f"suspicious_path_keywords:{','.join(matched_keywords)}")
            risk_score += 0.30

        # Check unencrypted HTTP for credential or banking patterns
        if parsed.scheme == "http" and matched_keywords:
            signals.append("unencrypted_http_credential_target")
            risk_score += 0.20

        # Check excessive length
        if len(url) > 120:
            signals.append("excessive_url_length")
            risk_score += 0.10

        risk_score = min(round(risk_score, 4), 1.0)

        # Categorize risk level
        if risk_score >= 0.70:
            risk_level = SecurityRiskLevel.HIGH
        elif risk_score >= 0.40:
            risk_level = SecurityRiskLevel.MEDIUM
        elif risk_score >= 0.15:
            risk_level = SecurityRiskLevel.LOW
        else:
            risk_level = SecurityRiskLevel.SAFE

        # Enforce minimum risk level for concealed shorteners if applicable
        if is_shortener:
            order = [SecurityRiskLevel.SAFE, SecurityRiskLevel.LOW, SecurityRiskLevel.MEDIUM, SecurityRiskLevel.HIGH]
            if order.index(risk_level) < order.index(self.shortener_min_risk):
                risk_level = self.shortener_min_risk


        return URLAnalysis(
            url=raw_url,
            normalized_url=normalized_url,
            domain=domain,
            risk_level=risk_level,
            risk_score=risk_score,
            signals=signals,
            provider=self.provider_name,
            analyzed_at=datetime.now(UTC),
        )

    def analyze_text(self, text: str | None) -> list[URLAnalysis]:
        urls = self.extract_urls(text)
        return [self.analyze_url(u) for u in urls]
