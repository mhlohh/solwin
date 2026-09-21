import pytest
from pydantic import ValidationError

from ml_service.api.schemas import ComplaintInput
from ml_service.core.config import Settings
from ml_service.core.logging import redact_email


def test_settings_reject_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        Settings(model_confidence_threshold=2.0)


def test_complaint_requires_text() -> None:
    with pytest.raises(ValidationError):
        ComplaintInput()


def test_email_redaction_masks_local_part() -> None:
    assert redact_email("Contact support@example.com") == "Contact s***@example.com"
