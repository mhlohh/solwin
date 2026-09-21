from pathlib import Path

from ml_service.api.schemas import ActionType, BusinessCategory, UrgencyLevel
from ml_service.recommendation.engine import RecommendationEngine


def test_recommendation_security_escalation() -> None:
    engine = RecommendationEngine(Path("config/action_rules.yaml"))
    rec = engine.recommend(
        category=BusinessCategory.SECURITY_CONCERN,
        urgency=UrgencyLevel.CRITICAL,
        security_risk="CRITICAL",
    )
    assert rec.primary_action == ActionType.ESCALATE_TO_SECURITY_TEAM
    assert rec.matched_rule_id == "RULE_SECURITY_INCIDENT"


def test_recommendation_account_takeover() -> None:
    engine = RecommendationEngine(Path("config/action_rules.yaml"))
    rec = engine.recommend(
        category=BusinessCategory.ACCOUNT_LOGIN_PROBLEM,
        urgency=UrgencyLevel.CRITICAL,
    )
    assert rec.primary_action == ActionType.RESET_ACCOUNT_ACCESS


def test_recommendation_refund_request() -> None:
    engine = RecommendationEngine(Path("config/action_rules.yaml"))
    rec = engine.recommend(
        category=BusinessCategory.REFUND_REQUEST,
        urgency=UrgencyLevel.MEDIUM,
    )
    assert rec.primary_action == ActionType.INITIATE_REFUND_REVIEW


def test_recommendation_delivery_issue() -> None:
    engine = RecommendationEngine(Path("config/action_rules.yaml"))
    rec = engine.recommend(
        category=BusinessCategory.DELIVERY_SHIPPING_PROBLEM,
        urgency=UrgencyLevel.HIGH,
    )
    assert rec.primary_action == ActionType.ESCALATE_TO_DELIVERY_TEAM


def test_recommendation_fallback() -> None:
    engine = RecommendationEngine(Path("config/action_rules.yaml"))
    rec = engine.recommend(
        category=BusinessCategory.OTHER,
        urgency=UrgencyLevel.LOW,
    )
    assert rec.primary_action == ActionType.STANDARD_SUPPORT_RESPONSE
