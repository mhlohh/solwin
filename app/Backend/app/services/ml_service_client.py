"""HTTP client for the ML service's canonical Customer Review intelligence API.

Bridges app/Backend to app/ml_services via the ML service's
``POST /api/v1/analyze/review`` endpoint, which returns the canonical
CustomerReviewOutput schema. The raw JSON is re-validated locally against
app.schemas.review.CustomerReviewOutput so the Backend never persists a
payload that does not match the canonical contract.
"""

from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.review import CustomerReviewOutput

logger = get_logger("solwin.ml_service_client")

DEFAULT_TIMEOUT_SECONDS = 60.0


class MLServiceError(Exception):
    """Raised when the ML service cannot produce a valid CustomerReviewOutput."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def analyze_review_via_ml(
    payload: dict[str, Any],
    base_url: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> CustomerReviewOutput:
    """Call the ML service /api/v1/analyze/review and validate the response.

    Args:
        payload: Request body matching the ML service CustomerReviewRequest
            schema (message required; subject, source_type, source_record_id,
            domain, channel, include_* and prefer_llm optional).
        base_url: Override the ML service base URL (defaults to the
            ML_SERVICE_URL setting).
        timeout: Request timeout in seconds; ML inference can be slow on
            cold start.

    Returns:
        A validated CustomerReviewOutput instance.

    Raises:
        MLServiceError: On connectivity failure, non-200 response, malformed
            JSON, or schema validation failure.
    """
    url = (
        (base_url or get_settings().ML_SERVICE_URL).rstrip("/")
        + "/api/v1/analyze/review"
    )
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.error(f"ML service unreachable at {url}: {exc}")
        raise MLServiceError(
            "ML intelligence service is unreachable. "
            "Please verify the ML service is running.",
            status_code=503,
        ) from exc

    if response.status_code != 200:
        logger.error(
            f"ML service returned {response.status_code} for analyze/review: "
            f"{response.text[:500]}"
        )
        raise MLServiceError(
            f"ML intelligence service failed with status {response.status_code}.",
            status_code=502,
        )

    try:
        body = response.json()
    except ValueError as exc:
        logger.error("ML service returned malformed JSON.")
        raise MLServiceError(
            "ML intelligence service returned a malformed response.",
            status_code=502,
        ) from exc

    try:
        return CustomerReviewOutput.model_validate(body)
    except Exception as exc:
        logger.error(f"ML response failed canonical schema validation: {exc}")
        raise MLServiceError(
            "ML intelligence service response does not match the canonical "
            "Customer Review schema.",
            status_code=502,
        ) from exc
