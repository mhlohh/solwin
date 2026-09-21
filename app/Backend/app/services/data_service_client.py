"""HTTP client for the Data API's raw feedback dataset (app/data backend).

Fetches pre-aggregated statistics over the ingested customer-feedback dataset
so the dashboard reflects the full ingestion volume (tens of thousands of
records) alongside the live support-queue metrics. Every failure degrades to
``None`` so the dashboard stays fully functional without the Data API.
"""

from typing import Optional

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.analytics import IngestedFeedbackStats

logger = get_logger("solwin.data_service_client")

DEFAULT_TIMEOUT_SECONDS = 5.0


def get_ingested_feedback_stats(
    base_url: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Optional[IngestedFeedbackStats]:
    """Fetch ``GET /tickets/stats`` from the Data API, or ``None`` if unavailable.

    Args:
        base_url: Override the Data API base URL (defaults to DATA_SERVICE_URL).
        timeout: Request timeout in seconds; kept short because this powers a
            dashboard widget and must never stall the overview endpoint.

    Returns:
        Validated IngestedFeedbackStats, or None on any failure.
    """
    url = (
        (base_url or get_settings().DATA_SERVICE_URL).rstrip("/") + "/tickets/stats"
    )
    try:
        response = httpx.get(url, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.warning(f"Data API unreachable at {url}: {exc}")
        return None

    if response.status_code != 200:
        logger.warning(
            f"Data API returned {response.status_code} for /tickets/stats"
        )
        return None

    try:
        body = response.json()
    except ValueError:
        logger.warning("Data API returned malformed JSON for /tickets/stats.")
        return None

    try:
        return IngestedFeedbackStats.model_validate(body)
    except ValidationError as exc:
        logger.warning(f"Data API stats payload failed validation: {exc}")
        return None
