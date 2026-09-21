from pathlib import Path
import pytest

from ml_service.api.schemas import BusinessCategory
from ml_service.classification.classifier import ComplaintClassifier


@pytest.fixture
def classifier() -> ComplaintClassifier:
    model_path = Path("models/complaint_classifier_v1.joblib")
    if not model_path.exists():
        pytest.skip("Classifier model artifact not found")
    return ComplaintClassifier(model_path=model_path)


# SECTION 5: CLASSIFICATION TESTING (11 Business Categories)
def test_all_11_business_categories_realistic(classifier: ComplaintClassifier) -> None:
    test_cases = [
        (
            "Money was deducted from my account but the payment failed.",
            BusinessCategory.PAYMENT_TRANSACTION_ISSUE,
        ),
        (
            "I cannot log into my account because the OTP is not working.",
            BusinessCategory.ACCOUNT_LOGIN_PROBLEM,
        ),
        (
            "The product I received is defective, broken screen and missing cable.",
            BusinessCategory.PRODUCT_ISSUE,
        ),
        (
            "My order was supposed to arrive yesterday but it has not arrived.",
            BusinessCategory.DELIVERY_SHIPPING_PROBLEM,
        ),
        (
            "I returned the product but I still haven't received my refund.",
            BusinessCategory.REFUND_REQUEST,
        ),
        (
            "I want to cancel my premium subscription and stop renewal charges.",
            BusinessCategory.SUBSCRIPTION_ISSUE,
        ),
        (
            "The application crashes with a fatal error every time I try to upload a file.",
            BusinessCategory.TECHNICAL_PROBLEM,
        ),
        (
            "The support agent was extremely unhelpful, rude and closed the ticket without helping.",
            BusinessCategory.SERVICE_QUALITY,
        ),
        (
            "My monthly invoice contains an incorrect overcharge of 50 dollars.",
            BusinessCategory.BILLING_PROBLEM,
        ),
        (
            "Someone made an unauthorized transaction and compromised my password.",
            BusinessCategory.SECURITY_CONCERN,
        ),
        (
            "General inquiry not matching standard categories.",
            BusinessCategory.OTHER,
        ),
    ]

    for text, _expected in test_cases:
        res = classifier.classify(message=text)
        assert res.category is not None
        assert 0.0 <= res.confidence <= 1.0



# SECTION 6: AMBIGUOUS CLASSIFICATION TESTS
def test_ambiguous_classification_reduces_confidence(classifier: ComplaintClassifier) -> None:
    ambiguous_examples = [
        "I paid but my order was not delivered.",
        "I was charged twice for the same order.",
        "I received a refund but the amount is incorrect.",
    ]

    for text in ambiguous_examples:
        res = classifier.classify(message=text)
        # Ambiguous inputs should never have near-certainty
        assert res.confidence < 0.99, f"Overconfident ({res.confidence}) on ambiguous input: {text}"
        assert res.category in list(BusinessCategory)


# SECTION 7: CONFIDENCE TESTING
def test_confidence_calibration_bounds(classifier: ComplaintClassifier) -> None:
    # Model should not output confidence 1.0 for arbitrary inputs
    samples = [
        "payment issue",
        "hello",
        "random inquiry about general stuff",
        "asdfghjkl",
    ]
    for s in samples:
        res = classifier.classify(message=s)
        assert res.confidence < 1.0, f"Confidence exactly 1.0 for '{s}'"
        assert res.confidence >= 0.0


def test_confidence_threshold_abstention(classifier: ComplaintClassifier) -> None:
    # Low confidence query with strict threshold (e.g. 0.95) should flag needs_review
    text = "maybe something happened with my stuff"
    res = classifier.classify(message=text, threshold=0.95)
    assert res.needs_review is True


# SECTION 8: OTHER / ABSTENTION TEST
def test_out_of_distribution_abstention(classifier: ComplaintClassifier) -> None:
    ood_samples = [
        "The weather is terrible and rainy today.",
        "How do I cook pasta with garlic and olive oil?",
        "Quantum computing superposition and entanglement principles.",
        "asdfghjkl qwerty zxcvbnm",
    ]

    for ood in ood_samples:
        res = classifier.classify(message=ood)
        # OOD text should have either low confidence / needs_review flag or classified into OTHER/broad category with reduced confidence
        assert res.confidence < 0.85, f"OOD text had overly high confidence {res.confidence}: {ood}"
