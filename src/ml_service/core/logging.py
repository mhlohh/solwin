"""Privacy-preserving structured logging helpers."""

import logging
import re
from typing import Any

EMAIL_PATTERN = re.compile(r"(?P<local>[^@\s]{1,64})@(?P<domain>[^@\s]{1,255})")


def redact_email(value: str) -> str:
    """Mask local parts of emails before any diagnostic use."""

    return EMAIL_PATTERN.sub(
        lambda match: f"{match.group('local')[0]}***@{match.group('domain')}", value
    )


def configure_logging(level: str) -> None:
    """Configure a concise logger that callers use only with safe fields."""

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def safe_log(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Log metadata only; raw customer text and credentials are never accepted."""

    forbidden = {"message", "subject", "text", "email", "token", "api_key", "password"}
    safe_fields = {key: value for key, value in fields.items() if key not in forbidden}
    logger.info("%s %s", event, safe_fields)
