"""Sentiment analysis via the AI provider layer.

Wraps ``GeminiProvider`` and provides an explicit fallback state when
the provider is unavailable.  Callers receive a ``SentimentResult`` in all
cases — never an exception propagated to the request handler.
"""

import logging

from ml_service.ai.exceptions import ProviderError
from ml_service.ai.gemini_provider import GeminiProvider
from ml_service.api.schemas import GeminiAnalysisOutput, SentimentLabel, SentimentResult

logger = logging.getLogger(__name__)

# Sentinel used when the provider is unavailable — clearly marked.
_UNAVAILABLE = SentimentResult(
    label=SentimentLabel.NEUTRAL,
    score=0.0,
    reason="Sentiment analysis unavailable: AI provider not configured or failed.",
    provider="fallback",
    available=False,
)


class SentimentAnalyzer:
    """Extracts sentiment from a pre-computed ``GeminiAnalysisOutput``.

    The analyzer does not make its own API call; it reads fields already
    present in the unified Gemini response, keeping the "one call per
    complaint" design intact.
    """

    @staticmethod
    def from_gemini_output(output: GeminiAnalysisOutput) -> SentimentResult:
        """Build a ``SentimentResult`` from a validated ``GeminiAnalysisOutput``."""
        try:
            label = SentimentLabel(output.sentiment_label)
        except ValueError:
            logger.warning("SentimentAnalyzer: unexpected label %r, defaulting to NEUTRAL",
                           output.sentiment_label)
            label = SentimentLabel.NEUTRAL

        score = max(0.0, min(1.0, float(output.sentiment_score)))
        return SentimentResult(
            label=label,
            score=score,
            reason=output.sentiment_reason,
            provider="gemini",
            available=True,
        )

    @staticmethod
    def unavailable(reason: str = "") -> SentimentResult:
        """Return an explicit unavailable sentinel with an optional reason."""
        return SentimentResult(
            label=SentimentLabel.NEUTRAL,
            score=0.0,
            reason=reason or _UNAVAILABLE.reason,
            provider="fallback",
            available=False,
        )
