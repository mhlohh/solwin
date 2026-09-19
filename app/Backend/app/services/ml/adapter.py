"""
Adapter for deterministically mapping ML service categories and urgency
to Solwin's domain enums.
"""

from typing import Dict, Tuple

from app.models.enums import ComplaintCategory, Priority, ResolutionStatus, Sentiment

# Deterministic mapping from the 11 ML BusinessCategory strings
# to Solwin's 5 ComplaintCategory enums
ML_CATEGORY_MAP: Dict[str, ComplaintCategory] = {
    "PAYMENT_TRANSACTION_ISSUE": ComplaintCategory.PAYMENT_BILLING,
    "REFUND_REQUEST": ComplaintCategory.PAYMENT_BILLING,
    "BILLING_PROBLEM": ComplaintCategory.PAYMENT_BILLING,
    "ACCOUNT_LOGIN_PROBLEM": ComplaintCategory.ACCOUNT_ACCESS,
    "SUBSCRIPTION_ISSUE": ComplaintCategory.ACCOUNT_ACCESS,
    "TECHNICAL_PROBLEM": ComplaintCategory.TECHNICAL_ISSUE,
    "PRODUCT_ISSUE": ComplaintCategory.TECHNICAL_ISSUE,
    "DELIVERY_SHIPPING_PROBLEM": ComplaintCategory.SERVICE_REQUEST,
    "SERVICE_QUALITY": ComplaintCategory.SERVICE_REQUEST,
    "SECURITY_CONCERN": ComplaintCategory.OTHER,
    "OTHER": ComplaintCategory.OTHER,
}

# Deterministic mapping from ML UrgencyLevel to Solwin's Priority
ML_URGENCY_TO_PRIORITY: Dict[str, Priority] = {
    "CRITICAL": Priority.CRITICAL,
    "HIGH": Priority.HIGH,
    "MEDIUM": Priority.MEDIUM,
    "LOW": Priority.LOW,
}

# Deterministic mapping from ML ResolutionStatus to Solwin's ResolutionStatus
ML_RESOLUTION_MAP: Dict[str, ResolutionStatus] = {
    "RESOLVED": ResolutionStatus.RESOLVED,
    "PARTIALLY_RESOLVED": ResolutionStatus.IN_PROGRESS,
    "UNRESOLVED": ResolutionStatus.UNRESOLVED,
    "UNKNOWN": ResolutionStatus.UNRESOLVED,
}


def map_ml_category(ml_category_str: str) -> ComplaintCategory:
    """Map ML service category string to Solwin ComplaintCategory deterministically."""
    if not ml_category_str:
        return ComplaintCategory.OTHER
    return ML_CATEGORY_MAP.get(ml_category_str.upper().strip(), ComplaintCategory.OTHER)


def map_ml_urgency(ml_urgency_str: str) -> Priority:
    """Map ML service urgency string to Solwin Priority deterministically."""
    if not ml_urgency_str:
        return Priority.MEDIUM
    return ML_URGENCY_TO_PRIORITY.get(ml_urgency_str.upper().strip(), Priority.MEDIUM)


def map_ml_resolution(ml_resolution_str: str) -> ResolutionStatus:
    """Map ML service resolution string to Solwin ResolutionStatus deterministically."""
    if not ml_resolution_str:
        return ResolutionStatus.UNRESOLVED
    return ML_RESOLUTION_MAP.get(
        ml_resolution_str.upper().strip(), ResolutionStatus.UNRESOLVED
    )


def derive_sentiment_and_emotion(
    category: ComplaintCategory, priority: Priority, is_resolved: bool
) -> Tuple[Sentiment, str]:
    """
    Derive deterministic baseline sentiment and emotion from validated signals
    without fabricating random claims.
    """
    if is_resolved:
        return Sentiment.POSITIVE, "Satisfaction"

    if priority == Priority.CRITICAL:
        return Sentiment.NEGATIVE, "Urgency"
    if priority == Priority.HIGH:
        return Sentiment.NEGATIVE, "Frustration"
    if priority == Priority.LOW:
        return Sentiment.NEUTRAL, "Calm"

    return Sentiment.NEUTRAL, "Concern"
