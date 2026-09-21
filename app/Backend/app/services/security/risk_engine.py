from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel
from app.services.security.phishing_detector import (
    PhishingDetectionResult,
    PhishingDetector,
)

# Deterministic Risk Scoring Weights
# Signals:
# - Credential Harvesting: 30
# - OTP Request: 30
# - Suspicious Lookalike/IP/Shortener URL: 25 each (max 50)
# - Suspicious Email: 20
# - Impersonation: 15
# - Urgency: 10
#
# Score Ranges:
# 0 - 15: LOW
# 16 - 39: MEDIUM
# 40 - 69: HIGH
# >= 70: CRITICAL


class SecurityAnalysisResult(BaseModel):
    threat_detected: bool = False
    threat_type: str = "NONE"
    social_engineering_detected: bool = False
    techniques: List[str] = Field(default_factory=list)
    risk_level: str = RiskLevel.LOW.value
    suspicious_urls: List[str] = Field(default_factory=list)
    suspicious_emails: List[str] = Field(default_factory=list)
    risk_reasons: List[str] = Field(default_factory=list)
    recommended_action: str = "Continue normal support handling."


class RiskEngine:
    def __init__(self):
        self.phishing_detector = PhishingDetector()

    def evaluate(
        self,
        text: str,
        expected_domain: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> SecurityAnalysisResult:
        """Calculate risk score, level, explainable reasons and actions."""
        phishing_res: PhishingDetectionResult = self.phishing_detector.analyze(
            text, expected_domain=expected_domain, display_name=display_name
        )

        score = 0
        reasons = []

        # 1. Social Engineering Signals
        techniques = phishing_res.social_engineering.techniques
        if "CREDENTIAL_HARVESTING" in techniques:
            score += 30
            reasons.append("Credential harvesting request detected")
        if "OTP_REQUEST" in techniques:
            score += 30
            reasons.append("One-Time Password (OTP) request detected")
        if "IMPERSONATION" in techniques:
            score += 15
            reasons.append("Brand or organizational impersonation detected")
        if "URGENCY" in techniques:
            score += 10
            reasons.append("Urgency or account suspension pressure language detected")

        # 2. Suspicious URLs
        num_susp_urls = len(phishing_res.suspicious_urls)
        if num_susp_urls > 0:
            url_points = min(50, num_susp_urls * 25)
            score += url_points
            reasons.append(f"{num_susp_urls} suspicious or deceptive URL(s) detected")

        # 3. Suspicious Emails
        num_susp_emails = len(phishing_res.suspicious_emails)
        if num_susp_emails > 0:
            score += 20
            reasons.append(
                f"{num_susp_emails} suspicious email sender address(es) detected"
            )

        # 4. Determine Risk Level
        if score >= 70 or (phishing_res.threat_type == "PHISHING" and score >= 50):
            risk_level = RiskLevel.CRITICAL.value
            recommended_action = (
                "Escalate to the security team and avoid interacting with "
                "suspicious links or credentials."
            )
        elif score >= 40:
            risk_level = RiskLevel.HIGH.value
            recommended_action = (
                "Escalate for security review and do not execute customer instructions."
            )
        elif score >= 16:
            risk_level = RiskLevel.MEDIUM.value
            recommended_action = (
                "Review the message and verify sender identity before taking action."
            )
        else:
            risk_level = RiskLevel.LOW.value
            recommended_action = "Continue normal support handling."

        # If clean
        if not reasons:
            reasons.append(
                "No significant security threats or deceptive signals detected"
            )

        threat_detected = phishing_res.threat_detected or risk_level in [
            RiskLevel.HIGH.value,
            RiskLevel.CRITICAL.value,
        ]

        return SecurityAnalysisResult(
            threat_detected=threat_detected,
            threat_type=phishing_res.threat_type,
            social_engineering_detected=phishing_res.social_engineering.detected,
            techniques=techniques,
            risk_level=risk_level,
            suspicious_urls=phishing_res.suspicious_urls,
            suspicious_emails=phishing_res.suspicious_emails,
            risk_reasons=reasons,
            recommended_action=recommended_action,
        )
