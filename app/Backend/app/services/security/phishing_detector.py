from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.security.email_analyzer import EmailAnalysisResult, EmailAnalyzer
from app.services.security.social_engineering import (
    SocialEngineeringDetector,
    SocialEngineeringResult,
)
from app.services.security.url_analyzer import URLAnalysisResult, URLAnalyzer


class PhishingDetectionResult(BaseModel):
    threat_detected: bool = False
    threat_type: str = "NONE"  # PHISHING, SUSPICIOUS_MESSAGE, NONE
    suspicious_urls: List[str] = Field(default_factory=list)
    suspicious_emails: List[str] = Field(default_factory=list)
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
            social_engineering=se_result,
            indicators=indicators,
        )
