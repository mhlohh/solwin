import logging
import re
from typing import Any

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
# Credit / debit card pattern (13-19 digits with optional hyphens/spaces, matching standard PAN ranges)
_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
# Bearer tokens and general JWT patterns (header.payload.signature)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.=]+", re.IGNORECASE)
_JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")
# API keys, passwords, private keys
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|password|passwd|auth[_-]?token)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)

BLOCKED_KEY_NAMES = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "access_token",
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
}


def redact_string(val: str) -> str:
    """Scrub PII, payment card numbers, JWTs, bearer tokens, and secrets from strings."""
    if not val:
        return val
    s = _BEARER_PATTERN.sub("Bearer [REDACTED]", val)
    s = _JWT_PATTERN.sub("[REDACTED_JWT]", s)
    s = _SECRET_KEY_PATTERN.sub(lambda m: f"{m.group(0).split(':')[0]}: [REDACTED]", s)
    s = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", s)
    # Check card pattern on cleaned digits to avoid masking short numbers
    def _mask_card(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19:
            return "[REDACTED_CARD]"
        return match.group(0)

    s = _CARD_PATTERN.sub(_mask_card, s)
    return s


def sanitize_data(obj: Any) -> Any:
    """Recursively sanitize dicts, lists, tuples, and strings."""
    if isinstance(obj, dict):
        sanitized_dict = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(b in k_lower for b in BLOCKED_KEY_NAMES):
                sanitized_dict[k] = "[REDACTED]"
            else:
                sanitized_dict[k] = sanitize_data(v)
        return sanitized_dict
    if isinstance(obj, list):
        return [sanitize_data(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(sanitize_data(item) for item in obj)
    if isinstance(obj, set):
        return {sanitize_data(item) for item in obj}
    if isinstance(obj, str):
        return redact_string(obj)
    return obj


def redact_email(value: str) -> str:
    return _EMAIL_PATTERN.sub(lambda m: f"{m.group(0)[0]}***@{m.group(0).split('@')[1]}", value)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def safe_log(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Log structured event with comprehensive recursive value scrubbing."""
    sanitized = sanitize_data(fields)
    logger.info("%s %s", event, sanitized)

