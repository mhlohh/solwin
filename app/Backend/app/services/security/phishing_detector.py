import re
from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.security.email_analyzer import EmailAnalysisResult, EmailAnalyzer
from app.services.security.social_engineering import (
    SocialEngineeringDetector,
    SocialEngineeringResult,
)
from app.services.security.url_analyzer import URLAnalysisResult, URLAnalyzer


# Executable / script file extensions dangerous as email attachments.
# NOTE: no ".com" — it collides with domain names (www.amazon.com);
# the legacy DOS executable meaning is dead in practice.
DANGEROUS_ATTACHMENT_EXTENSIONS = {
    ".exe", ".scr", ".bat", ".cmd", ".pif", ".msi",
    ".vbs", ".vbe", ".js", ".jse", ".wsf", ".ps1",
    ".jar", ".hta", ".lnk", ".iso", ".img",
}

# Double-extension trap: document.jpg.exe, invoice.pdf.scr, etc.
_DOUBLE_EXT_REGEX = re.compile(
    r"\b[\w.\-]+\.(?:(?:pdf|docx?|xlsx?|jpe?g|png|txt|html?)\.)"
    r"(?:exe|scr|bat|cmd|pif|msi|vbs|js|jar|hta|lnk)\b",
    re.IGNORECASE,
)

# Dataset convention: "[attachment: invoice.exe]" plus bare filenames
_ATTACHMENT_TAG_REGEX = re.compile(r"\[attachment:\s*([^\]]+)\]", re.IGNORECASE)
_DANGEROUS_FILE_REGEX = re.compile(
    r"\b[\w.\-]+(?:"
    + "|".join(ext.lstrip(".") for ext in DANGEROUS_ATTACHMENT_EXTENSIONS)
    + r")\b",
    re.IGNORECASE,
)


def detect_dangerous_attachments(text: str) -> List[str]:
    """Find dangerous executable attachments mentioned in a message.

    Catches both the dataset convention "[attachment: invoice.exe]" and
    bare executable filenames, including double-extension traps like
    "invoice.pdf.exe". Deterministic, no ML.
    """
    if not text:
        return []
    found = []
    for match in _ATTACHMENT_TAG_REGEX.findall(text):
        name = match.strip().strip("'\"")
        if name.lower().endswith(tuple(DANGEROUS_ATTACHMENT_EXTENSIONS)):
            found.append(name)
    found.extend(m.group(0).strip() for m in _DOUBLE_EXT_REGEX.finditer(text))
    for match in _DANGEROUS_FILE_REGEX.finditer(text):
        name = match.group(0).strip()
        if name.lower() not in [f.lower() for f in found]:
            found.append(name)
    return found


class PhishingDetectionResult(BaseModel):
    threat_detected: bool = False
    threat_type: str = "NONE"  # PHISHING, SUSPICIOUS_MESSAGE, NONE
    suspicious_urls: List[str] = Field(default_factory=list)
    suspicious_emails: List[str] = Field(default_factory=list)
    suspicious_attachments: List[str] = Field(default_factory=list)
    social_engineering: SocialEngineeringResult
    indicators: List[str] = Field(default_factory=list)


class PhishingDetector:
    def __init__(self):
        self.url_analyzer = URLAnalyzer()
        self.email_analyzer = EmailAnalyzer()
        self.social_engineering_detector = SocialEngineeringDetector()

    def analyze(
        self,
        text: str,
        expected_domain: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> PhishingDetectionResult:
        """Combine deterministic signals to detect phishing or suspicious content."""
        # 1. Analyze URLs
        url_results: List[URLAnalysisResult] = self.url_analyzer.analyze_text(
            text, expected_domain=expected_domain
        )
        suspicious_urls = [u.url for u in url_results if u.suspicious]

        # 2. Analyze Emails
        email_results: List[EmailAnalysisResult] = self.email_analyzer.analyze_text(
            text, expected_domain=expected_domain, display_name=display_name
        )
        suspicious_emails = [e.email for e in email_results if e.suspicious]

        # 3. Analyze Social Engineering
        se_result: SocialEngineeringResult = self.social_engineering_detector.detect(
            text
        )

        # 3b. Dangerous executable attachments (e.g. "[attachment: invoice.exe]")
        suspicious_attachments = detect_dangerous_attachments(text)

        # 4. Synthesize Indicators
        indicators = []

        for u in url_results:
            if u.suspicious:
                indicators.append(f"Suspicious URL [{u.url}]: {', '.join(u.signals)}")

        for e in email_results:
            if e.suspicious:
                indicators.append(
                    f"Suspicious Email [{e.email}]: {', '.join(e.signals)}"
                )

        for att in suspicious_attachments:
            indicators.append(
                f"Dangerous executable attachment: {att}"
            )

        for sig in se_result.signals:
            indicators.append(f"Social Engineering: {sig}")

        # 5. Phishing Determination
        # High confidence phishing requires:
        # (a) Suspicious URL or email + credential/OTP/urgency request OR
        # (b) Lookalike domain + credential harvesting OR
        # (c) Credential harvesting + OTP request + Urgency
        has_suspicious_link = len(suspicious_urls) > 0
        has_suspicious_email = len(suspicious_emails) > 0
        has_credentials = "CREDENTIAL_HARVESTING" in se_result.techniques
        has_otp = "OTP_REQUEST" in se_result.techniques
        has_urgency = "URGENCY" in se_result.techniques
        has_impersonation = "IMPERSONATION" in se_result.techniques
        has_dangerous_attachment = len(suspicious_attachments) > 0

        is_phishing = False
        is_suspicious = False

        if has_suspicious_link and (
            has_credentials or has_otp or has_urgency or has_impersonation
        ):
            is_phishing = True
        elif has_suspicious_email and (has_credentials or has_otp):
            is_phishing = True
        elif has_credentials and has_otp:
            is_phishing = True
        elif has_credentials and has_urgency and has_impersonation:
            is_phishing = True
        elif (
            has_suspicious_link
            or has_suspicious_email
            or has_credentials
            or has_dangerous_attachment
            or (has_urgency and has_impersonation)
        ):
            is_suspicious = True

        if is_phishing:
            threat_detected = True
            threat_type = "PHISHING"
        elif is_suspicious:
            threat_detected = True
            threat_type = "SUSPICIOUS_MESSAGE"
        else:
            threat_detected = False
            threat_type = "NONE"

        return PhishingDetectionResult(
            threat_detected=threat_detected,
            threat_type=threat_type,
            suspicious_urls=suspicious_urls,
            suspicious_emails=suspicious_emails,
            suspicious_attachments=suspicious_attachments,
            social_engineering=se_result,
            indicators=indicators,
        )
