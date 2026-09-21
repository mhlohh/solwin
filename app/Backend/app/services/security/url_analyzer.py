import ipaddress
import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

import tldextract
from pydantic import BaseModel, Field

# Common URL Shortener domains
SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "adf.ly",
    "cutt.ly",
    "rb.gy",
    "shorturl.at",
}

# Common targeted brands for lookalike detection
TARGETED_BRANDS = {
    "paypal",
    "microsoft",
    "google",
    "apple",
    "amazon",
    "netflix",
    "facebook",
    "instagram",
    "chase",
    "wellsfargo",
    "bankofamerica",
    "citi",
    "support",
    "security",
}

# Credential / Authentication sensitive keywords in path/query
SENSITIVE_KEYWORDS = {
    "login",
    "signin",
    "verify",
    "verification",
    "authenticate",
    "auth",
    "password",
    "passcode",
    "credential",
    "wallet",
    "banking",
    "secure",
    "update-account",
    "reset",
}

# Leetspeak / digit substitution mapping
LEET_MAP = {
    "0": "o",
    "1": "l",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s",
}

# Regex to safely find URLs in text while preserving boundaries and punctuation
URL_REGEX = re.compile(
    r"(?i)\b((?:https?://|www\d{0,3}\.|[a-z0-9.\-]+[.][a-z]{2,4}/)"
    r"(?:[^\s()<>]|\((?:[^\s()<>]|(?:\([^\s()<>]+\)))*\))+"
    r"(?:\((?:[^\s()<>]|(?:\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
)


class URLExtractionResult(BaseModel):
    url: str
    scheme: str
    hostname: str
    registered_domain: str
    subdomain: str
    path: str
    query_params: dict = Field(default_factory=dict)


class URLAnalysisResult(BaseModel):
    url: str
    domain: str
    is_https: bool
    is_ip_address: bool
    is_shortener: bool
    lookalike_detected: bool
    signals: List[str] = Field(default_factory=list)
    suspicious: bool = False


class URLAnalyzer:
    def __init__(self):
        # Configure tldextract without live HTTP fetch
        self._extractor = tldextract.TLDExtract(suffix_list_urls=None)

    def extract_urls(self, text: str) -> List[URLExtractionResult]:
        """Extract URLs robustly from text without destroying original strings."""
        if not text:
            return []

        matches = URL_REGEX.findall(text)
        results = []
        seen = set()

        for match in matches:
            clean_match = match.rstrip(".,;!?)\"'>")
            if clean_match in seen:
                continue
            seen.add(clean_match)

            # Ensure scheme for urllib.parse
            parse_target = clean_match
            if not (
                parse_target.startswith("http://")
                or parse_target.startswith("https://")
            ):
                parse_target = "http://" + parse_target

            parsed = urlparse(parse_target)
            hostname = (parsed.hostname or "").lower()
            if not hostname:
                continue

            extracted = self._extractor(hostname)
            registered_domain = (
                f"{extracted.domain}.{extracted.suffix}"
                if extracted.domain and extracted.suffix
                else hostname
            )

            results.append(
                URLExtractionResult(
                    url=clean_match,
                    scheme=parsed.scheme or "http",
                    hostname=hostname,
                    registered_domain=registered_domain,
                    subdomain=extracted.subdomain,
                    path=parsed.path,
                    query_params=parse_qs(parsed.query),
                )
            )

        return results

    def check_lookalike(self, domain: str) -> Optional[str]:
        """Detect obvious lookalike substitutions and deceptive brand combos."""
        normalized = domain.lower()
        for char, sub in LEET_MAP.items():
            normalized = normalized.replace(char, sub)

        for brand in TARGETED_BRANDS:
            # Check if domain has leetspeak substitution of brand
            if (
                brand in normalized
                and brand not in domain.lower()
                and any(c in domain.lower() for c in LEET_MAP.keys())
            ):
                return f"Lookalike brand substitution detected for '{brand}'"

            # Check deceptive brand combinations
            if brand in domain.lower():
                parts = domain.lower().split(".")
                for part in parts:
                    if brand in part and part != brand:
                        lures = [
                            "login",
                            "verify",
                            "security",
                            "support",
                            "update",
                        ]
                        if any(kw in part for kw in lures):
                            return (
                                "Deceptive brand and security keyword "
                                f"combination: '{part}'"
                            )

        return None

    def analyze_url(
        self,
        extracted: URLExtractionResult,
        expected_domain: Optional[str] = None,
    ) -> URLAnalysisResult:
        """Perform deterministic static security signal analysis on URL."""
        signals = []
        is_https = extracted.scheme.lower() == "https"
        is_ip = False

        # 1. IP address hostname check
        try:
            ipaddress.ip_address(extracted.hostname)
            is_ip = True
            signals.append("IP address used as hostname instead of domain")
        except ValueError:
            pass

        # 2. Scheme check
        if not is_https:
            signals.append("Insecure HTTP scheme used")

        # 3. Shortener check
        is_shortener = (
            extracted.registered_domain.lower() in SHORTENER_DOMAINS
            or extracted.hostname.lower() in SHORTENER_DOMAINS
        )
        if is_shortener:
            signals.append("URL shortening service hides true destination")

        # 4. Excessive length or subdomains
        if len(extracted.url) > 150:
            signals.append(f"Unusually long URL length ({len(extracted.url)} chars)")

        subdomain_parts = [p for p in extracted.subdomain.split(".") if p]
        if len(subdomain_parts) >= 3:
            signals.append(f"Excessive subdomains count ({len(subdomain_parts)})")

        # 5. Lookalike domain check
        lookalike_reason = self.check_lookalike(extracted.hostname)
        lookalike_detected = bool(lookalike_reason)
        if lookalike_reason:
            signals.append(lookalike_reason)

        # 6. Sensitive credential path check
        path_lower = extracted.path.lower()
        matched_kws = [kw for kw in SENSITIVE_KEYWORDS if kw in path_lower]
        if matched_kws:
            signals.append(f"Credential/security lure path ({', '.join(matched_kws)})")

        # 7. Expected organization domain mismatch
        if expected_domain and expected_domain.strip():
            exp = expected_domain.lower().strip()
            if (
                extracted.registered_domain.lower() != exp
                and not extracted.hostname.lower().endswith("." + exp)
            ):
                signals.append(
                    f"Domain mismatch: host '{extracted.registered_domain}' "
                    f"differs from expected '{exp}'"
                )

        # 8. Obfuscation check (e.g. '@' in url userinfo)
        if "@" in extracted.url.split("?")[0]:
            signals.append("URL contains '@' userinfo credentials/redirection trick")

        # Determination: suspicious if lookalike, ip, shortener, or 2+ signals
        suspicious = lookalike_detected or is_ip or is_shortener or len(signals) >= 2

        return URLAnalysisResult(
            url=extracted.url,
            domain=extracted.registered_domain,
            is_https=is_https,
            is_ip_address=is_ip,
            is_shortener=is_shortener,
            lookalike_detected=lookalike_detected,
            signals=signals,
            suspicious=suspicious,
        )

    def analyze_text(
        self,
        text: str,
        expected_domain: Optional[str] = None,
    ) -> List[URLAnalysisResult]:
        """Extract and analyze all URLs found in text."""
        extracted_list = self.extract_urls(text)
        return [
            self.analyze_url(item, expected_domain=expected_domain)
            for item in extracted_list
        ]
