"""Unit tests for the local rule-based social-engineering detector (primary SE tier)."""

import pytest

from ml_service.security.social_engineering_detector import SocialEngineeringDetector


@pytest.fixture()
def detector() -> SocialEngineeringDetector:
    return SocialEngineeringDetector()


@pytest.mark.parametrize(
    "text,expected_technique",
    [
        ("Your account will be permanently closed unless you verify now", "THREAT_COERCION"),
        ("Last warning: confirm your identity immediately", "THREAT_COERCION"),
        ("Please share the OTP you just received to confirm", "OTP_REQUEST"),
        ("Enter your password here so we can unlock the account", "CREDENTIAL_HARVESTING"),
        ("I am calling from the security department of your bank", "IMPERSONATION"),
        ("Pay the processing fee to release your refund via gift cards", "PAYMENT_MANIPULATION"),
        ("Verify your account now within 24 hours or it expires today", "URGENCY"),
    ],
)
def test_detects_expected_technique(
    detector: SocialEngineeringDetector, text: str, expected_technique: str
) -> None:
    result = detector.detect(text)
    assert result.detected is True
    assert expected_technique in [t.value for t in result.techniques]
    assert result.provider == "local"


@pytest.mark.parametrize(
    "text",
    [
        "My order has not arrived yet, where is it?",
        "I want a refund for the broken coffee maker",
        "The app crashes when I upload a file",
        "Thank you for the quick resolution",
        "",
    ],
)
def test_clean_text_not_flagged(detector: SocialEngineeringDetector, text: str) -> None:
    result = detector.detect(text)
    assert result.detected is False
    assert result.techniques == []


def test_subject_line_is_scanned(detector: SocialEngineeringDetector) -> None:
    result = detector.detect(message="see below", subject="URGENT: verify your account now")
    assert result.detected is True


def test_reason_contains_rule_evidence(detector: SocialEngineeringDetector) -> None:
    result = detector.detect("Please share the OTP to proceed")
    assert "SE-" in result.reason
