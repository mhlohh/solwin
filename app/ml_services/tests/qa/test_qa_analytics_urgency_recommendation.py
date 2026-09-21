from pathlib import Path
import pytest

from ml_service.analytics.frequency import FrequencyTracker
from ml_service.api.schemas import ActionType, BusinessCategory, ResolutionStatus, UrgencyLevel
from ml_service.recommendation.engine import RecommendationEngine
from ml_service.resolution.detector import ResolutionDetector
from ml_service.urgency.detector import UrgencyDetector


# SECTION 13: FREQUENCY ANALYTICS TEST
def test_frequency_synthetic_counts() -> None:
    tracker = FrequencyTracker()

    # Ingest synthetic complaints
    for _ in range(100):
        tracker.record_event("PAYMENT_ISSUE", cluster_id=1)
    for _ in range(50):
        tracker.record_event("DELIVERY_PROBLEM", cluster_id=2)
    for _ in range(10):
        tracker.record_event("REFUND_REQUEST", cluster_id=3)

    report = tracker.get_report()
    assert report.total_live_reports == 160
    assert report.by_category["PAYMENT_ISSUE"] == 100
    assert report.by_category["DELIVERY_PROBLEM"] == 50
    assert report.by_category["REFUND_REQUEST"] == 10
    assert report.by_cluster["1"] == 100


def test_frequency_zero_division_guard() -> None:
    tracker = FrequencyTracker()
    report = tracker.get_report()
    assert report.total_live_reports == 0
    # Safe percentage change math
    prev = 0
    curr = report.total_live_reports
    pct_change = ((curr - prev) / prev * 100.0) if prev > 0 else 0.0
    assert pct_change == 0.0


# SECTION 14: URGENCY TEST
def test_urgency_risk_based_levels() -> None:
    detector = UrgencyDetector()

    # Critical: Active theft/fraud
    res_crit = detector.detect(
        message="Someone has stolen money from my account and is making transactions right now!"
    )
    assert res_crit.urgency == UrgencyLevel.CRITICAL

    # High: Large monetary deduction error
    res_high = detector.detect(
        message="₹20,000 was deducted incorrectly and I need this resolved urgently."
    )
    assert res_high.urgency in (UrgencyLevel.HIGH, UrgencyLevel.CRITICAL)

    # Medium: Pending payment delay
    res_med = detector.detect(
        message="My payment has been pending since yesterday."
    )
    assert res_med.urgency in (UrgencyLevel.MEDIUM, UrgencyLevel.HIGH)

    # Low: General inquiry
    res_low = detector.detect(
        message="Can you tell me how the payment process works?"
    )
    assert res_low.urgency == UrgencyLevel.LOW

    # Angry sentiment with low business impact should NOT be CRITICAL
    res_angry = detector.detect(
        message="Your service is absolutely terrible, worst app ever!!!"
    )
    assert res_angry.urgency != UrgencyLevel.CRITICAL


# SECTION 15: RECOMMENDED ACTION TEST
def test_action_recommendations_rules() -> None:
    rules_path = Path("config/action_rules.yaml")
    if not rules_path.exists():
        pytest.skip("action_rules.yaml not found")

    engine = RecommendationEngine(rules_path)

    # Security Critical
    rec_sec = engine.recommend(
        category=BusinessCategory.SECURITY_CONCERN,
        urgency=UrgencyLevel.CRITICAL,
        security_risk="HIGH",
    )
    assert rec_sec.primary_action == ActionType.ESCALATE_TO_SECURITY_TEAM

    # Payment issue with high urgency
    rec_pay = engine.recommend(
        category=BusinessCategory.PAYMENT_TRANSACTION_ISSUE,
        urgency=UrgencyLevel.HIGH,
    )
    assert rec_pay.primary_action in (
        ActionType.ESCALATE_TO_PAYMENT_TEAM,
        ActionType.INITIATE_REFUND_REVIEW,
    )

    # Fallback when no rule matches
    rec_fallback = engine.recommend(
        category="NON_EXISTENT_CATEGORY",
        urgency="NON_EXISTENT_URGENCY",
    )
    assert rec_fallback.primary_action in (
        ActionType.HUMAN_REVIEW,
        ActionType.STANDARD_SUPPORT_RESPONSE,
    )



# SECTION 16: UNRESOLVED COMPLAINT TEST
def test_resolution_status_detection() -> None:
    detector = ResolutionDetector()

    # Resolved
    res_done = detector.detect(
        message="We have refunded the amount. Customer: I received the refund. Thank you, issue resolved."
    )
    assert res_done.status == ResolutionStatus.RESOLVED

    # Unresolved
    res_pending = detector.detect(
        message="Any update? I still haven't received my money and am waiting for response."
    )
    assert res_pending.status == ResolutionStatus.UNRESOLVED

    # Partially resolved
    res_partial = detector.detect(
        message="One item arrived, but the other is missing and replacement dispatched."
    )
    assert res_partial.status == ResolutionStatus.PARTIALLY_RESOLVED

    # Unknown
    res_unknown = detector.detect(
        message="Just asking about store opening hours."
    )
    assert res_unknown.status == ResolutionStatus.UNKNOWN
