import re
from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.security.url_analyzer import URLAnalyzer

# Common public free-mail providers
FREE_MAIL_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
    "zoho.com",
    "mail.com",
    "gmx.com",
    "yandex.com",
}

# Regex to safely find email addresses
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


class EmailAnalysisResult(BaseModel):
    email: str
    local_part: str
    domain: str
    is_free_mail: bool
    lookalike_detected: bool
    signals: List[str] = Field(default_factory=list)
    suspicious: bool = False


class EmailAnalyzer:
    def __init__(self):
        self._url_analyzer = URLAnalyzer()

    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text while avoiding trailing punctuation."""
        if not text:
            return []

        raw_matches = EMAIL_REGEX.findall(text)
        cleaned = []
        seen = set()

        for email in raw_matches:
            c = email.strip().rstrip(".,;!?:)'\">")
            if c and c.lower() not in seen:
                seen.add(c.lower())
                cleaned.append(c)

        return cleaned

    def analyze_email(
        self,
        email: str,
        expected_domain: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> EmailAnalysisResult:
        """Analyze email security signals deterministically."""
        signals = []
        parts = email.split("@", 1)
        local_part = parts[0]
        domain = parts[1].lower() if len(parts) > 1 else ""

        # 1. Free-mail contextual check
        is_free_mail = domain in FREE_MAIL_PROVIDERS
        if is_free_mail:
            signals.append(f"Free-mail service provider domain ({domain})")

        # 2. Lookalike domain check
        lookalike_reason = self._url_analyzer.check_lookalike(domain)
        lookalike_detected = bool(lookalike_reason)
        if lookalike_reason:
            signals.append(lookalike_reason)

        # 3. Expected domain mismatch check
        if expected_domain and expected_domain.strip():
            exp = expected_domain.lower().strip()
            if domain != exp and not domain.endswith("." + exp):
                signals.append(
                    f"Email domain '{domain}' does not match expected '{exp}'"
                )

        # 4. Display-name brand spoofing
        if display_name:
            disp_lower = display_name.lower()
            brands = [
                "microsoft",
                "paypal",
                "google",
                "apple",
                "bank",
                "support",
                "security",
            ]
            for brand in brands:
                if brand in disp_lower and brand not in domain:
                    signals.append(
                        f"Display name claims '{display_name}' but domain is '{domain}'"
                    )

        # 5. Suspicious characters in local part
        if len(local_part) > 30:
            signals.append("Unusually long email local part")
        role_keywords = ["admin", "root", "security", "support", "verify"]
        if any(c in local_part for c in role_keywords) and is_free_mail:
            signals.append(
                f"Official role name '{local_part}' used on free-mail domain"
            )

        # Suspicious if lookalike detected or spoofed display or role on free-mail
        suspicious = (
            lookalike_detected
            or any("display name claims" in s.lower() for s in signals)
            or any("role name" in s.lower() for s in signals)
        )

        return EmailAnalysisResult(
            email=email,
            local_part=local_part,
            domain=domain,
            is_free_mail=is_free_mail,
            lookalike_detected=lookalike_detected,
            signals=signals,
            suspicious=suspicious,
        )

    def analyze_text(
        self,
        text: str,
        expected_domain: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> List[EmailAnalysisResult]:
        """Extract and analyze all emails in text."""
        emails = self.extract_emails(text)
        return [
            self.analyze_email(
                e,
                expected_domain=expected_domain,
                display_name=display_name,
            )
            for e in emails
        ]
