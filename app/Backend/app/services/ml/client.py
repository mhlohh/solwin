"""
HTTP client for communicating with Solwin's Customer Complaint Intelligence ML service.
"""

from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("solwin.ml_client")


class MLServiceError(Exception):
    """Exception raised when ML service communication or response validation fails."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class MLClassificationResponse(BaseModel):
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: Dict[str, float] = Field(default_factory=dict)
    needs_review: bool = False
    model_name: str = ""
    model_version: str = ""
    fine_grained_intent: Optional[str] = None


class MLUrgencyResponse(BaseModel):
    urgency: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class MLResolutionResponse(BaseModel):
    status: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    pending_items: list[str] = Field(default_factory=list)


class MLClient:
    """
    Client for calling ML service endpoints with strict timeouts
    and error isolation.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.ML_SERVICE_URL).rstrip("/")
        self.timeout = timeout or settings.ML_SERVICE_TIMEOUT_SECONDS

    def check_health(self) -> Dict[str, Any]:
        """Check if ML service is healthy."""
        url = f"{self.base_url}/health"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url)
                res.raise_for_status()
                return res.json()
        except httpx.TimeoutException as exc:
            logger.warning(f"ML service health check timed out: {exc}")
            raise MLServiceError(
                "ML service health check timed out", status_code=504
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning(f"ML service health check failed: {exc}")
            raise MLServiceError(
                f"ML service health check failed: {exc}", status_code=502
            ) from exc

    def check_readiness(self) -> Dict[str, Any]:
        """Check if ML service models are loaded and ready."""
        url = f"{self.base_url}/ready"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url)
                res.raise_for_status()
                return res.json()
        except httpx.TimeoutException as exc:
            logger.warning(f"ML service readiness check timed out: {exc}")
            raise MLServiceError(
                "ML service readiness check timed out", status_code=504
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning(f"ML service readiness check failed: {exc}")
            raise MLServiceError(
                f"ML service readiness check failed: {exc}", status_code=502
            ) from exc

    def classify_complaint(
        self,
        message: str,
        subject: Optional[str] = None,
    ) -> MLClassificationResponse:
        """Call /api/v1/classify on the ML service."""
        url = f"{self.base_url}/api/v1/classify"
        payload = {"message": message, "subject": subject}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                return MLClassificationResponse.model_validate(res.json())
        except httpx.TimeoutException as exc:
            logger.error(f"ML service classification timed out: {exc}")
            raise MLServiceError(
                "ML service classification timed out", status_code=504
            ) from exc
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.error(f"ML service classification error {code}: {exc.response.text}")
            raise MLServiceError(
                f"ML service returned error {code}",
                status_code=502,
            ) from exc
        except httpx.RequestError as exc:
            logger.error(f"ML service connection failed: {exc}")
            raise MLServiceError(
                "Could not connect to ML service", status_code=503
            ) from exc
        except Exception as exc:
            logger.error(f"ML service response validation error: {exc}")
            raise MLServiceError(
                "Invalid response format from ML service", status_code=502
            ) from exc

    def detect_urgency(
        self,
        message: str,
        subject: Optional[str] = None,
    ) -> MLUrgencyResponse:
        """Call /api/v1/urgency on the ML service."""
        url = f"{self.base_url}/api/v1/urgency"
        payload = {"message": message, "subject": subject}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                return MLUrgencyResponse.model_validate(res.json())
        except Exception as exc:
            logger.warning(f"ML service urgency detection call failed: {exc}")
            # Non-fatal fallback with neutral defaults
            return MLUrgencyResponse(
                urgency="MEDIUM", confidence=0.5, signals=[], reasons=[]
            )

    def detect_resolution(
        self,
        message: str,
        subject: Optional[str] = None,
    ) -> MLResolutionResponse:
        """Call /api/v1/resolution on the ML service."""
        url = f"{self.base_url}/api/v1/resolution"
        payload = {"message": message, "subject": subject}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                return MLResolutionResponse.model_validate(res.json())
        except Exception as exc:
            logger.warning(f"ML service resolution detection call failed: {exc}")
            # Non-fatal fallback with unresolved default
            return MLResolutionResponse(
                status="UNRESOLVED", confidence=0.5, signals=[], pending_items=[]
            )
