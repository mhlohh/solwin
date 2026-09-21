import re

from ml_service.api.schemas import UrgencyLevel, UrgencyResult
from ml_service.preprocessing.cleaner import build_complaint_text

# High-risk objective risk indicators (do not confuse anger with operational urgency)
CRITICAL_INDICATORS = [
    (r"\bunauthorized\b", "unauthorized_transaction_indicator"),
    (r"\bstolen\b", "stolen_credential_or_item"),
    (r"\bhacked\b", "account_compromise_detected"),
    (r"\bphishing\b", "phishing_threat_detected"),
    (r"\bmalware\b", "malware_infection_detected"),
    (r"\bransomware\b", "ransomware_detected"),
    (r"\blawsuit\b|\blegal action\b", "legal_regulatory_deadline"),
    (r"\bfraud\b", "fraud_alert"),
    (r"\boutage\b|\bdown\b.*\bsystem\b", "system_outage"),
    (r"\bcredit card (stolen|compromised|charged illegally)\b", "card_theft"),
]

HIGH_INDICATORS = [
    (r"\bdeadline\b|\burgent(ly)?\b|\basap\b|\bimmediately\b|need.*resolved\s+urgently", "time_critical_deadline"),
    (r"\baccount locked\b|\bcannot login\b|\blockout\b|\bunable to login\b|\botp\b", "access_blockage"),
    (r"\boverdue\b|\bdelayed\s+(for\s+)?(\d+\s+)?days\b", "prolonged_service_delay"),
    (r"\bdid not receive.*refund\b|\bwhere is my refund\b|\bmissing refund\b", "pending_monetary_refund"),
    (r"\b(large\s+amount|money|amount|[₹$€£]\d+|funds).*(deducted|debited)\b", "monetary_deduction"),
    (r"\b(deducted|debited)\s+(incorrectly|without|from)\b", "monetary_deduction"),
    (r"\bdouble charg(ed|e)\b|\bovercharg(ed|e)\b|\bcharged twice\b", "disputed_monetary_charge"),
    (r"\bescalat(e|ed|ing)\b", "customer_escalation_request"),
]


MEDIUM_INDICATORS = [
    (r"\bdelayed\b|\blate\b", "service_delay"),
    (r"\bpending\b", "pending_transaction_delay"),
    (r"\btracking\b|\bwhere is my (order|package|parcel)\b", "order_status_query"),
    (r"\bwrong (item|product|order)\b", "incorrect_item_received"),
    (r"\bdamaged\b|\bbroken\b|\bdefective\b", "product_defect"),
    (
        r"\b(want to|need to|request to|please)\s+(return|exchange)\b|\breturn\s+my\b",
        "return_exchange_request",
    ),
]



class UrgencyDetector:
    """Detects operational urgency without confounding anger or profanity with operational risk."""

    def __init__(self) -> None:
        self.critical_patterns = [
            (re.compile(p, re.IGNORECASE), name) for p, name in CRITICAL_INDICATORS
        ]
        self.high_patterns = [
            (re.compile(p, re.IGNORECASE), name) for p, name in HIGH_INDICATORS
        ]
        self.medium_patterns = [
            (re.compile(p, re.IGNORECASE), name) for p, name in MEDIUM_INDICATORS
        ]

    def detect(
        self,
        message: str | None,
        subject: str | None = None,
    ) -> UrgencyResult:
        text = build_complaint_text(message, subject)
        if not text:
            return UrgencyResult(
                urgency=UrgencyLevel.LOW,
                confidence=1.0,
                signals=["empty_message"],
                reasons=["No actionable operational urgency signals detected."],
            )

        signals: list[str] = []
        reasons: list[str] = []

        # Check Critical
        for pattern, signal_name in self.critical_patterns:
            if pattern.search(text):
                signals.append(signal_name)
                reasons.append(f"Detected critical security or severe loss trigger: {signal_name}")

        if signals:
            return UrgencyResult(
                urgency=UrgencyLevel.CRITICAL,
                confidence=0.95,
                signals=signals,
                reasons=reasons,
            )

        # Check High
        for pattern, signal_name in self.high_patterns:
            if pattern.search(text):
                signals.append(signal_name)
                reasons.append(f"Detected time-sensitive or monetary trigger: {signal_name}")

        if signals:
            return UrgencyResult(
                urgency=UrgencyLevel.HIGH,
                confidence=0.85,
                signals=signals,
                reasons=reasons,
            )

        # Check Medium
        for pattern, signal_name in self.medium_patterns:
            if pattern.search(text):
                signals.append(signal_name)
                reasons.append(f"Detected standard operational inquiry: {signal_name}")

        if signals:
            return UrgencyResult(
                urgency=UrgencyLevel.MEDIUM,
                confidence=0.75,
                signals=signals,
                reasons=reasons,
            )

        # Fallback to Low
        return UrgencyResult(
            urgency=UrgencyLevel.LOW,
            confidence=0.70,
            signals=["routine_inquiry"],
            reasons=["Inquiry contains no urgent deadline, monetary loss, or security triggers."],
        )
