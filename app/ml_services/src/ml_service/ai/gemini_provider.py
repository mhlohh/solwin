"""Concrete Google Gemini implementation of :class:`AIProvider`.

Single responsibility: own the Gemini client, retries, timeouts, structured
output, error translation, and logging.  Callers receive either a validated
``GeminiAnalysisOutput`` or a typed ``ProviderError`` subclass — never raw
exception leakage from the SDK.

Security notes
--------------
* The API key is read once from settings and passed to ``genai.Client``.
  It is never logged, printed, or stored on instance attributes accessible
  from outside this module.
* User-supplied text is isolated behind the ``[CUSTOMER CONTENT]`` delimiter
  in the prompt to mitigate prompt injection.
* Raw Gemini API responses are never logged in full (only token counts and
  status codes are safe to emit).
"""

import json
import logging
import signal
import threading
import time
from contextlib import contextmanager
from typing import Generator

import httpx
from google import genai
from google.genai import types

from ml_service.ai.exceptions import (
    ProviderConfigError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderValidationError,
)
from ml_service.ai.prompts import SYSTEM_INSTRUCTION, build_user_content
from ml_service.ai.provider import AIProvider
from ml_service.api.schemas import (
    BusinessCategory,
    GeminiAnalysisOutput,
    SentimentLabel,
    SocialEngineeringTechnique,
)
from ml_service.core.config import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Timeout strategy
# ---------------------------------------------------------------------------
# SIGALRM only works in the main thread of the main interpreter — uvicorn runs
# sync endpoints in worker threads, so signal-based timeouts would raise
# "signal only works in main thread" on every request. The real enforcement is
# an HTTP-level timeout on the underlying client; the context manager below
# keeps SIGALRM for main-thread callers (tests, scripts) and degrades to a no-op
# elsewhere.

class _TimeoutError(Exception):
    pass


@contextmanager
def _timeout(seconds: float) -> Generator[None, None, None]:
    """Raise ``_TimeoutError`` if the block exceeds *seconds* (main thread only).

    In worker threads this is a no-op; the client's HTTP timeout enforces the
    deadline instead.
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    int_secs = max(1, int(seconds))

    def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
        raise _TimeoutError("Gemini request timed out")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(int_secs)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider(AIProvider):
    """Google Gemini implementation of the ``AIProvider`` interface.

    One instance is created on application startup and shared across requests
    via ``app.state.ai_provider``.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = settings.gemini_model
        self._embedding_model = settings.gemini_embedding_model
        self._client: genai.Client | None = None
        self._available: bool = False

        if not settings.gemini_enabled:
            logger.info("GeminiProvider: disabled via GEMINI_ENABLED=false")
            return

        if not settings.gemini_api_key:
            raise ProviderConfigError(
                "GEMINI_API_KEY is not set. Set it in .env or the environment."
            )

        try:
            # Key is never stored on a public attribute.
            # The HTTP client timeout is the authoritative deadline for requests
            # made from worker threads (see _timeout notes above).
            http = httpx.Client(
                timeout=httpx.Timeout(
                    settings.gemini_timeout_seconds,
                    connect=min(5.0, settings.gemini_timeout_seconds),
                )
            )
            self._client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options={"client_args": {"http": http}},
            )
            self._available = True
            logger.info(
                "GeminiProvider: initialized with model=%s (http timeout=%ss)",
                self._model, settings.gemini_timeout_seconds,
            )
        except Exception as exc:
            logger.error("GeminiProvider: failed to initialize client: %s", type(exc).__name__)
            raise ProviderConfigError(
                "Failed to initialize Google GenAI client."
            ) from exc

    # ------------------------------------------------------------------
    # AIProvider interface
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def embedding_model_name(self) -> str:
        return self._embedding_model

    def analyze(self, subject: str | None, message: str | None) -> GeminiAnalysisOutput:
        """Single structured Gemini call: classification + sentiment + SE + summary.

        Raises
        ------
        ProviderConfigError
            Provider not configured or disabled.
        ProviderRateLimitError
            HTTP 429 after all retries exhausted.
        ProviderTimeoutError
            Request exceeded ``gemini_timeout_seconds``.
        ProviderValidationError
            Gemini response failed Pydantic validation.
        ProviderError
            All other unrecoverable failures.
        """
        if not self._available or self._client is None:
            raise ProviderConfigError("GeminiProvider is not available.")

        user_content = build_user_content(subject, message)
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=GeminiAnalysisOutput,
            temperature=0.1,
        )

        return self._call_with_retry(user_content, config)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return dense embeddings for a list of texts.

        Raises
        ------
        ProviderConfigError
            Provider not configured or embeddings not enabled.
        ProviderError
            Any embedding API failure.
        """
        if not self._available or self._client is None:
            raise ProviderConfigError("GeminiProvider is not available.")
        if not self._settings.gemini_use_for_embeddings:
            raise ProviderConfigError("Gemini embeddings are disabled (GEMINI_USE_FOR_EMBEDDINGS=false).")

        try:
            with _timeout(self._settings.gemini_timeout_seconds):
                response = self._client.models.embed_content(
                    model=self._embedding_model,
                    contents=texts,
                    config=types.EmbedContentConfig(task_type="CLUSTERING"),
                )
            embeddings = [list(e.values) for e in response.embeddings]  # type: ignore[attr-defined]
            logger.debug("GeminiProvider: embedded %d texts", len(texts))
            return embeddings
        except _TimeoutError as exc:
            raise ProviderTimeoutError("Embedding request timed out.") from exc
        except Exception as exc:
            raise ProviderError(f"Embedding request failed: {type(exc).__name__}") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(
        self,
        content: str,
        config: types.GenerateContentConfig,
    ) -> GeminiAnalysisOutput:
        """Call Gemini with bounded exponential-backoff retry.

        On HTTP 429 after all retries: raises ``ProviderRateLimitError``.
        On timeout: raises ``ProviderTimeoutError``.
        On other errors: raises ``ProviderError``.
        """
        max_retries = self._settings.gemini_max_retries
        last_exc: Exception = RuntimeError("Unknown error")

        for attempt in range(max_retries + 1):
            try:
                with _timeout(self._settings.gemini_timeout_seconds):
                    response = self._client.models.generate_content(  # type: ignore[union-attr]
                        model=self._model,
                        contents=content,
                        config=config,
                    )

                # Log token usage safely (no PII)
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    um = response.usage_metadata
                    logger.debug(
                        "GeminiProvider: tokens in=%s out=%s",
                        getattr(um, "prompt_token_count", "?"),
                        getattr(um, "candidates_token_count", "?"),
                    )

                return self._parse_response(response)

            except _TimeoutError as exc:
                logger.warning("GeminiProvider: timeout on attempt %d", attempt + 1)
                last_exc = exc
                # No retry on timeout — fail fast
                raise ProviderTimeoutError("Gemini request timed out.") from exc

            except ProviderValidationError:
                raise

            except Exception as exc:
                err_str = str(exc).lower()
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str

                if is_rate_limit:
                    if attempt < max_retries:
                        wait = 2 ** attempt  # 1 s, 2 s, 4 s ...
                        logger.warning(
                            "GeminiProvider: rate limited (attempt %d/%d), retrying in %ds",
                            attempt + 1, max_retries + 1, wait,
                        )
                        time.sleep(wait)
                        last_exc = exc
                        continue
                    raise ProviderRateLimitError(
                        "Gemini API rate limit exceeded after all retries."
                    ) from exc

                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "GeminiProvider: transient error on attempt %d/%d (%s: %s), retrying in %ds",
                        attempt + 1, max_retries + 1, type(exc).__name__, str(exc)[:200], wait,
                    )
                    time.sleep(wait)
                    last_exc = exc
                    continue

                logger.error(
                    "GeminiProvider: unrecoverable error after %d attempts: %s: %s",
                    max_retries + 1, type(exc).__name__, str(exc)[:300],
                )
                raise ProviderError(f"Gemini call failed: {type(exc).__name__}") from exc

        raise ProviderError("Gemini call failed after all retries.") from last_exc

    def _parse_response(self, response: object) -> GeminiAnalysisOutput:
        """Validate and parse the raw Gemini response into a typed model."""
        raw_text: str = getattr(response, "text", None) or ""

        if not raw_text.strip():
            raise ProviderValidationError("Gemini returned an empty response.")

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ProviderValidationError(
                f"Gemini response is not valid JSON: {exc}"
            ) from exc

        try:
            result = GeminiAnalysisOutput.model_validate(parsed)
        except Exception as exc:
            raise ProviderValidationError(
                f"Gemini response failed schema validation: {exc}"
            ) from exc

        # Extra semantic guard: reject invented categories / labels
        try:
            BusinessCategory(result.category)
        except ValueError as exc:
            raise ProviderValidationError(
                f"Gemini returned an invalid category: {result.category!r}"
            ) from exc

        try:
            SentimentLabel(result.sentiment_label)
        except ValueError as exc:
            raise ProviderValidationError(
                f"Gemini returned an invalid sentiment label: {result.sentiment_label!r}"
            ) from exc

        for tech in result.social_engineering_techniques:
            try:
                SocialEngineeringTechnique(tech)
            except ValueError as exc:
                raise ProviderValidationError(
                    f"Gemini returned an invalid social engineering technique: {tech!r}"
                ) from exc

        return result
