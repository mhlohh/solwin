import json
import time
from typing import List, Optional

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.message import Message
from app.schemas.analysis import CustomerIntelligenceOutput
from app.services.ai.preprocessing import clean_text
from app.services.ai.prompts import CUSTOMER_SUPPORT_SYSTEM_INSTRUCTION

logger = get_logger("solwin.customer_intelligence")

# Transient upstream errors (rate limits, capacity spikes) worth retrying.
_TRANSIENT_MARKERS = (
    "unavailable",
    "high demand",
    "503",
    "internal error",
    "500",
    "deadline exceeded",
    "504",
    "timeout",
    "connection reset",
    "temporarily over",
)
_MAX_ATTEMPTS = 4


def _is_transient_error(err_msg: str) -> bool:
    lowered = err_msg.lower()
    return any(marker in lowered for marker in _TRANSIENT_MARKERS)


class CustomerIntelligenceError(Exception):
    """Base exception for customer intelligence service failures."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CustomerIntelligenceService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        client: Optional[genai.Client] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client = client

    def get_client(self) -> genai.Client:
        """Lazily initialize and return the official Google GenAI Client."""
        if self._client is not None:
            return self._client

        if not self.api_key:
            logger.error("GEMINI_API_KEY is not configured in settings.")
            raise CustomerIntelligenceError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY.",
                status_code=503,
            )

        try:
            self._client = genai.Client(api_key=self.api_key)
            return self._client
        except Exception as exc:
            logger.error(f"Failed to initialize Google GenAI Client: {exc}")
            raise CustomerIntelligenceError(
                "Failed to initialize Gemini AI client.",
                status_code=500,
            ) from exc

    def format_conversation(
        self,
        messages: List[Message],
        subject: Optional[str] = None,
    ) -> str:
        """Format and preprocess conversation messages into a transcript."""
        if not messages:
            return ""

        parts = []
        if subject and subject.strip():
            clean_sub = clean_text(subject)
            parts.append(f"Conversation Subject: {clean_sub}\n")

        parts.append("Conversation Transcript:")
        for idx, msg in enumerate(messages, 1):
            sender = (
                msg.sender_type.value
                if hasattr(msg.sender_type, "value")
                else str(msg.sender_type)
            )
            name = f" ({clean_text(msg.sender_name)})" if msg.sender_name else ""
            content = clean_text(msg.content)
            parts.append(f"[{idx}] {sender}{name}: {content}")

        return "\n".join(parts)

    def analyze_conversation(
        self,
        messages: List[Message],
        subject: Optional[str] = None,
    ) -> CustomerIntelligenceOutput:
        """Send transcript to Gemini and return structured intelligence."""
        if not messages:
            raise CustomerIntelligenceError(
                "Cannot analyze an empty conversation with no messages.",
                status_code=400,
            )

        formatted_content = self.format_conversation(messages, subject=subject)
        if not formatted_content.strip():
            raise CustomerIntelligenceError(
                "Conversation content is empty after preprocessing.",
                status_code=400,
            )

        client = self.get_client()

        config = types.GenerateContentConfig(
            system_instruction=CUSTOMER_SUPPORT_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=CustomerIntelligenceOutput,
            temperature=0.1,
        )

        # Retry transient upstream failures (capacity spikes, resets) with
        # exponential backoff; fail fast on permanent errors.
        response = None
        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=formatted_content,
                    config=config,
                )
                break
            except CustomerIntelligenceError:
                raise
            except Exception as exc:
                last_exc = exc
                err_msg = str(exc)
                if not _is_transient_error(err_msg):
                    break
                delay = min(2 ** (attempt - 1), 8)
                logger.warning(
                    f"Transient Gemini error (attempt {attempt}/{_MAX_ATTEMPTS}), "
                    f"retrying in {delay}s: {err_msg[:200]}"
                )
                time.sleep(delay)

        if response is None:
            err_msg = str(last_exc) if last_exc else "unknown error"
            logger.error(f"Gemini call failed for model [{self.model_name}]: {err_msg}")
            if "not found" in err_msg.lower() or "unsupported" in err_msg.lower():
                raise CustomerIntelligenceError(
                    f"Configured Gemini model '{self.model_name}' is "
                    "unavailable or unsupported.",
                    status_code=502,
                ) from last_exc
            if "quota" in err_msg.lower() or "resource" in err_msg.lower():
                raise CustomerIntelligenceError(
                    "Gemini API quota or rate limit exceeded.",
                    status_code=503,
                ) from last_exc
            raise CustomerIntelligenceError(
                "Gemini AI service encountered an error while processing.",
                status_code=502,
            ) from last_exc

        raw_text = response.text
        if not raw_text:
            logger.error("Gemini returned empty response text.")
            raise CustomerIntelligenceError(
                "Gemini returned an empty response.",
                status_code=502,
            )

        try:
            parsed = json.loads(raw_text)
            return CustomerIntelligenceOutput.model_validate(parsed)
        except Exception as exc:
            logger.error(f"Failed to parse or validate Gemini structured output: {exc}")
            raise CustomerIntelligenceError(
                "Failed to validate structured AI intelligence output.",
                status_code=502,
            ) from exc
