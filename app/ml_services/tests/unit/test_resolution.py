from ml_service.api.schemas import ResolutionStatus
from ml_service.resolution.detector import ResolutionDetector


def test_resolved_explicit_confirmation() -> None:
    detector = ResolutionDetector()
    result = detector.detect(
        message="Thank you, I received my refund today and my issue is resolved.",
        subject="Ticket follow-up",
    )
    assert result.status == ResolutionStatus.RESOLVED
    assert result.confidence >= 0.85
    assert len(result.pending_items) == 0


def test_unresolved_pending_action() -> None:
    detector = ResolutionDetector()
    result = detector.detect(
        message="I still haven't received my order and no update has been provided.",
        subject="Where is my courier",
    )
    assert result.status == ResolutionStatus.UNRESOLVED
    assert "still_unresolved_complaint" in result.signals
    assert len(result.pending_items) > 0


def test_partially_resolved() -> None:
    detector = ResolutionDetector()
    result = detector.detect(
        message="I received a partial refund for the damaged item, replacement dispatched.",
        subject="Dispute update",
    )
    assert result.status == ResolutionStatus.PARTIALLY_RESOLVED


def test_unknown_resolution() -> None:
    detector = ResolutionDetector()
    result = detector.detect(
        message="Can you tell me about the specifications of this model?",
        subject="Product query",
    )
    assert result.status == ResolutionStatus.UNKNOWN
