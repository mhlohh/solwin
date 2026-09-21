from pathlib import Path

from ml_service.api.schemas import BusinessCategory
from ml_service.classification.classifier import ComplaintClassifier


def test_classifier_not_loaded_on_missing_file(tmp_path: Path) -> None:
    non_existent = tmp_path / "missing.joblib"
    clf = ComplaintClassifier(model_path=non_existent)
    assert clf.is_loaded is False


def test_classifier_predicts_and_calibrates() -> None:
    model_path = Path("models/complaint_classifier_v1.joblib")
    if not model_path.exists():
        return

    clf = ComplaintClassifier(model_path=model_path, confidence_threshold=0.60)
    assert clf.is_loaded is True

    # Test delivery query
    result = clf.classify(
        message="Where is my parcel? It has been delayed for 5 days.",
        subject="Delivery status",
    )
    assert isinstance(result.category, BusinessCategory)
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.probabilities) == 11
    assert isinstance(result.needs_review, bool)


def test_classifier_abstention_on_low_confidence() -> None:
    model_path = Path("models/complaint_classifier_v1.joblib")
    if not model_path.exists():
        return

    # Using high threshold 0.99 forces abstention
    clf = ComplaintClassifier(model_path=model_path, confidence_threshold=0.99)
    result = clf.classify(message="Some ambiguous random string qwertyuiop")
    assert result.needs_review is True


def test_classifier_handles_empty_text() -> None:
    model_path = Path("models/complaint_classifier_v1.joblib")
    if not model_path.exists():
        return

    clf = ComplaintClassifier(model_path=model_path)
    result = clf.classify(message="", subject="")
    assert result.category == BusinessCategory.OTHER
    assert result.needs_review is True
    assert result.confidence == 0.0
