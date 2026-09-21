"""Exceptions for the AI provider layer."""


class ProviderError(Exception):
    """Base exception for AI provider failures."""


class ProviderConfigError(ProviderError):
    """Raised when the provider is misconfigured (e.g., missing API key)."""


class ProviderRateLimitError(ProviderError):
    """Raised when the provider returns HTTP 429 after all retries exhausted."""


class ProviderTimeoutError(ProviderError):
    """Raised when the provider request exceeds the configured timeout."""


class ProviderValidationError(ProviderError):
    """Raised when the provider response fails Pydantic schema validation."""
