"""Unified analysis pipeline — tiered AI architecture.

Primary tier (always served, deterministic, zero-cost):
  * Classification:  local TF-IDF + LogReg (11 business categories)
  * Sentiment:       local NLP lexicon engine (negation/intensifier aware)
  * Social-eng:      local rule engine (urgency, credential harvesting, ...)

Secondary tier (one structured Gemini call, best-effort):
  * Summary:         Gemini is the PRIMARY summarizer; when unavailable the
                     extractive summarizer takes over.
  * Cross-check:     Gemini's classification/sentiment/SE outputs are computed
                     in the same call; agreement is recorded in warnings for
                     observability but local results are never overridden.

Fallback matrix
---------------
Classification:  local TF-IDF (primary) → OTHER + needs_review=True + warning
Sentiment:       local NLP lexicon (primary) — always available
Social-eng:      local rule engine (primary) — always available
Summary:         Gemini (primary) → ConversationSummarizer.summarize() (extractive)
"""

import logging
from dataclasses import dataclass, field

from ml_service.ai.exceptions import (
    ProviderConfigError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderValidationError,
)
from ml_service.ai.gemini_provider import GeminiProvider
from ml_service.api.schemas import (
    BusinessCategory,
    ClassificationResult,
    GeminiAnalysisOutput,
    SentimentResult,
    SocialEngineeringResult,
)
from ml_service.classification.classifier import ComplaintClassifier
from ml_service.core.config import Settings
from ml_service.security.social_engineering_detector import SocialEngineeringDetector
from ml_service.sentiment.local_nlp import LocalNLPSentimentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class GeminiPipelineResult:
    """Output of a single pipeline run.

    All fields are populated regardless of which tier produced them.
    Inspect ``provider``, the per-section ``provider`` fields on
    sentiment/social_engineering, and ``warnings`` for provenance.
    """

    # Classification (local ML — primary)
    classification: ClassificationResult

    # Sentiment (local NLP — primary)
    sentiment: SentimentResult

    # Social engineering (local rules — primary)
    social_engineering: SocialEngineeringResult

    # Summary text (Gemini primary; empty string means caller should use
    # the extractive summarizer)
    summary_text: str

    # Provenance: which tier produced the classification
    provider: str  # "local" | "gemini"
    model_name: str  # e.g. "tfidf-logistic-regression-mildly-balanced"

    warnings: list[str] = field(default_factory=list)


class GeminiPipeline:
    """Runs the tiered pipeline: local ML/NLP primary, Gemini secondary.

    One instance is created on startup and shared across requests.
    """

    def __init__(
        self,
        ai_provider: GeminiProvider | None,
        local_classifier: ComplaintClassifier,
        settings: Settings,
    ) -> None:
        self._provider = ai_provider
        self._local_classifier = local_classifier
        self._settings = settings
        self._nlp_sentiment = LocalNLPSentimentAnalyzer()
        self._se_detector = SocialEngineeringDetector()

    def run(
        self,
        subject: str | None,
        message: str | None,
    ) -> GeminiPipelineResult:
        """Execute the pipeline and return a fully populated result.

        Never raises — all exceptions are caught and converted to fallback
        results + warning messages.
        """
        warnings: list[str] = []

        # --- PRIMARY: local ML/NLP tier (classification + sentiment + SE) ---
        result = self._build_from_local(subject, message, warnings)

        # --- SECONDARY: one structured Gemini call ---
        gemini_out: GeminiAnalysisOutput | None = None
        if self._provider and self._provider.is_available and self._settings.gemini_enabled:
            try:
                gemini_out = self._provider.analyze(subject, message)
            except ProviderRateLimitError as exc:
                logger.warning("GeminiPipeline: rate limited: %s", exc)
                warnings.append("gemini_rate_limited")
            except ProviderTimeoutError as exc:
                logger.warning("GeminiPipeline: timeout: %s", exc)
                warnings.append("gemini_timeout")
            except ProviderValidationError as exc:
                logger.warning("GeminiPipeline: validation error: %s", exc)
                warnings.append("gemini_validation_error")
            except ProviderConfigError as exc:
                logger.warning("GeminiPipeline: config error: %s", exc)
                warnings.append("gemini_config_error")
            except ProviderError as exc:
                logger.warning("GeminiPipeline: provider error: %s", exc)
                warnings.append("gemini_provider_error")
            except Exception as exc:  # safety net
                logger.error("GeminiPipeline: unexpected error: %s", type(exc).__name__)
                warnings.append("gemini_unexpected_error")

        # Gemini unavailable → summary falls back to extractive (empty text
        # tells the caller to run the extractive summarizer).
        if gemini_out is None:
            if self._settings.gemini_enabled and "summary_fallback_extractive" not in warnings:
                warnings.append("summary_fallback_extractive")
            result.warnings = warnings
            return result

        # --- Gemini is the PRIMARY summarizer ---
        if gemini_out.summary_text and gemini_out.summary_text.strip():
            result.summary_text = gemini_out.summary_text.strip()
        else:
            warnings.append("summary_fallback_extractive")

        # --- Cross-check observability (local results are never overridden) ---
        try:
            if BusinessCategory(gemini_out.category) is result.classification.category:
                warnings.append("gemini_agrees_classification")
            if gemini_out.sentiment_label == result.sentiment.label.value:
                warnings.append("gemini_agrees_sentiment")
            if bool(gemini_out.social_engineering_detected) is result.social_engineering.detected:
                warnings.append("gemini_agrees_social_engineering")
        except ValueError:
            # Invalid Gemini category already handled inside provider validation.
            pass

        result.warnings = warnings
        return result

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------

    def _build_from_local(
        self,
        subject: str | None,
        message: str | None,
        warnings: list[str],
    ) -> GeminiPipelineResult:
        """Build the primary-tier result using local ML/NLP engines."""
        # Classification — local TF-IDF (primary)
        if self._local_classifier.is_loaded:
            try:
                classification = self._local_classifier.classify(message, subject)
                classification = ClassificationResult(
                    category=classification.category,
                    confidence=classification.confidence,
                    probabilities=classification.probabilities,
                    needs_review=classification.needs_review,
                    model_name=classification.model_name,
                    model_version=classification.model_version,
                    fine_grained_intent=classification.fine_grained_intent,
                )
            except Exception as exc:
                logger.error("GeminiPipeline: local classifier failed: %s", exc)
                classification = ClassificationResult(
                    category=BusinessCategory.OTHER,
                    confidence=0.0,
                    probabilities={c.value: 0.0 for c in BusinessCategory},
                    needs_review=True,
                    model_name="local-fallback",
                    model_version="0.0",
                )
                warnings.append("classifier_failure")
        else:
            classification = ClassificationResult(
                category=BusinessCategory.OTHER,
                confidence=0.0,
                probabilities={c.value: 0.0 for c in BusinessCategory},
                needs_review=True,
                model_name="local-fallback",
                model_version="0.0",
            )
            warnings.append("classifier_not_loaded")

        # Sentiment — local NLP lexicon engine (primary, always available)
        sentiment = self._nlp_sentiment.analyze(message, subject)

        # Social engineering — local rule engine (primary, always available)
        social_engineering = self._se_detector.detect(message, subject)

        return GeminiPipelineResult(
            classification=classification,
            sentiment=sentiment,
            social_engineering=social_engineering,
            summary_text="",  # caller uses extractive summarizer unless Gemini fills it
            provider="local",
            model_name=classification.model_name,
            warnings=warnings,
        )
