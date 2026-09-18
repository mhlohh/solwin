"""Canonical, versioned API data contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BusinessCategory(StrEnum):
    PAYMENT_TRANSACTION_ISSUE = "PAYMENT_TRANSACTION_ISSUE"
    ACCOUNT_LOGIN_PROBLEM = "ACCOUNT_LOGIN_PROBLEM"
    PRODUCT_ISSUE = "PRODUCT_ISSUE"
    DELIVERY_SHIPPING_PROBLEM = "DELIVERY_SHIPPING_PROBLEM"
    REFUND_REQUEST = "REFUND_REQUEST"
    SUBSCRIPTION_ISSUE = "SUBSCRIPTION_ISSUE"
    TECHNICAL_PROBLEM = "TECHNICAL_PROBLEM"
    SERVICE_QUALITY = "SERVICE_QUALITY"
    BILLING_PROBLEM = "BILLING_PROBLEM"
    SECURITY_CONCERN = "SECURITY_CONCERN"
    OTHER = "OTHER"


class ComplaintInput(BaseModel):
    """Minimal complaint payload for future classification and unified analysis."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID | None = None
    customer_id: UUID | None = None
    conversation_id: UUID | None = None
    subject: str | None = Field(default=None, max_length=2_000)
    message: str | None = Field(default=None, max_length=10_000)
    language: str | None = Field(default=None, min_length=2, max_length=16)
    created_at: datetime | None = None
    source: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_text(self) -> "ComplaintInput":
        if not (self.subject or self.message):
            raise ValueError("at least one of subject or message must be supplied")
        return self


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    models_ready: bool
    detail: str | None = None


class ErrorResponse(BaseModel):
    status: str = "PARTIAL"
    errors: list[dict[str, str]]
