"""Unit tests for the local NLP sentiment analyzer (primary sentiment tier)."""

import pytest

from ml_service.sentiment.local_nlp import LocalNLPSentimentAnalyzer, analyze_sentiment


@pytest.mark.parametrize(
    "text,expected_label",
    [
        ("This app is fantastic, super fast and I love it", "POSITIVE"),
        ("Excellent service, very helpful team, thank you!", "POSITIVE"),
        ("Very bad service, I am extremely disappointed", "NEGATIVE"),
        ("Worst experience ever, complete waste of money", "NEGATIVE"),
        ("I did not receive my refund and nobody replies", "NEGATIVE"),
        ("The package arrived on time, thank you!", "POSITIVE"),
        ("Please review the attached invoice for order 12345", "NEUTRAL"),
        ("ok", "NEUTRAL"),
        ("", "NEUTRAL"),
    ],
)
def test_sentiment_labels(text: str, expected_label: str) -> None:
    result = analyze_sentiment(text)
    assert result.label.value == expected_label
    assert result.provider == "local"
    assert result.available is True


def test_negation_flips_polarity() -> None:
    positive = analyze_sentiment("The service is good")
    negated = analyze_sentiment("The service is not good")
    assert positive.label.value == "POSITIVE"
    assert negated.label.value == "NEGATIVE"


def test_intensifier_raises_confidence() -> None:
    plain = analyze_sentiment("This is bad")
    intensified = analyze_sentiment("This is extremely bad")
    assert intensified.score > plain.score


def test_neutral_score_is_half() -> None:
    result = analyze_sentiment("Meeting scheduled for tomorrow")
    assert result.score == 0.5


def test_score_band_matches_gemini_shape() -> None:
    for text in ("fantastic amazing excellent love it", "terrible horrible awful hate it"):
        result = analyze_sentiment(text)
        assert 0.55 <= result.score <= 0.95


def test_reason_mentions_signals() -> None:
    result = analyze_sentiment("very bad and rude support")
    assert "bad" in result.reason or "rude" in result.reason


def test_wrapper_class_matches_function() -> None:
    fn = analyze_sentiment("great product, works perfectly")
    wrapper = LocalNLPSentimentAnalyzer().analyze("great product, works perfectly")
    assert fn.label == wrapper.label
    assert fn.score == wrapper.score
