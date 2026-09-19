import json
from typing import List, Literal, Optional

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.message import Message
from app.schemas.analysis import CustomerIntelligenceOutput
from app.services.ai.preprocessing import clean_text
from app.services.ai.prompts import CUSTOMER_SUPPORT_SYSTEM_INSTRUCTION
from app.services.ml.adapter import (
    derive_sentiment_and_emotion,
    map_ml_category,
    map_ml_resolution,
    map_ml_urgency,
)
from app.services.ml.client import MLClient, MLServiceError

logger = get_logger("solwin.customer_intelligence")


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
        ml_client: Optional[MLClient] = None,
        provider: Optional[Literal["auto", "ml", "gemini"]] = None,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client = client
        self.provider = provider or settings.CUSTOMER_INTELLIGENCE_PROVIDER
        self.ml_client = ml_client or MLClient()

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

    def analyze_via_ml(
        self,
        messages: List[Message],
        subject: Optional[str] = None,
    ) -> CustomerIntelligenceOutput:
        """Analyze customer conversation using Solwin's local ML service models."""
        customer_texts = [
            clean_text(m.content)
            for m in messages
            if m.content and clean_text(m.content)
        ]
        combined_text = " ".join(customer_texts)
        if not combined_text.strip():
            raise CustomerIntelligenceError(
                "Conversation content is empty after preprocessing.",
                status_code=400,
            )

        # 1. Call ML classification
        try:
            clf_res = self.ml_client.classify_complaint(
                message=combined_text, subject=subject
            )
        except MLServiceError as exc:
            logger.error(f"ML service classification failed: {exc}")
            raise CustomerIntelligenceError(
                f"ML service classification failed: {exc.message}",
                status_code=exc.status_code,
            ) from exc

        # 2. Call ML urgency
        urg_res = self.ml_client.detect_urgency(message=combined_text, subject=subject)

        # 3. Call ML resolution
        res_res = self.ml_client.detect_resolution(
            message=combined_text, subject=subject
        )

        # 4. Map to domain enums deterministically
        mapped_category = map_ml_category(clf_res.category)
        mapped_priority = map_ml_urgency(urg_res.urgency)
        mapped_resolution = map_ml_resolution(res_res.status)

        is_resolved = mapped_resolution.value == "RESOLVED"
        sentiment, emotion = derive_sentiment_and_emotion(
            category=mapped_category,
            priority=mapped_priority,
            is_resolved=is_resolved,
        )

        intent_label = (
            clf_res.fine_grained_intent or clf_res.category.replace("_", " ").title()
        )
        issue_title = f"{intent_label} - {combined_text[:120].strip()}"
        if len(issue_title) > 255:
            issue_title = issue_title[:252] + "..."

        summary = (
            f"Customer complaint identified as {clf_res.category} "
            f"(intent: {intent_label}, confidence: {clf_res.confidence:.0%}). "
            f"Urgency assessed as {urg_res.urgency}. "
            f"Resolution state: {res_res.status}."
        )

        return CustomerIntelligenceOutput(
            category=mapped_category,
            issue=issue_title,
            sentiment=sentiment,
            emotion=emotion,
            priority=mapped_priority,
            resolution_status=mapped_resolution,
            summary=summary,
        )

    def analyze_via_gemini(
        self,
        messages: List[Message],
        subject: Optional[str] = None,
    ) -> CustomerIntelligenceOutput:
        """Send transcript to Gemini and return structured intelligence."""
        formatted_content = self.format_conversation(messages, subject=subject)
        if not formatted_content.strip():
            raise CustomerIntelligenceError(
                "Conversation content is empty after preprocessing.",
                status_code=400,
            )

        client = self.get_client()

        try:
            config = types.GenerateContentConfig(
                system_instruction=CUSTOMER_SUPPORT_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=CustomerIntelligenceOutput,
                temperature=0.1,
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=formatted_content,
                config=config,
            )
        except CustomerIntelligenceError:
            raise
        except Exception as exc:
            err_msg = str(exc)
            logger.error(f"Gemini call failed for model [{self.model_name}]: {err_msg}")
            if "not found" in err_msg.lower() or "unsupported" in err_msg.lower():
                raise CustomerIntelligenceError(
                    f"Configured Gemini model '{self.model_name}' is "
                    "unavailable or unsupported.",
                    status_code=502,
                ) from exc
            if "quota" in err_msg.lower() or "resource" in err_msg.lower():
                raise CustomerIntelligenceError(
                    "Gemini API quota or rate limit exceeded.",
                    status_code=503,
                ) from exc
            raise CustomerIntelligenceError(
                "Gemini AI service encountered an error while processing.",
                status_code=502,
            ) from exc

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

    def analyze_conversation(
        self,
        messages: List[Message],
        subject: Optional[str] = None,
    ) -> CustomerIntelligenceOutput:
        """
        Analyze customer conversation routing to ML service or Gemini
        based on provider configuration.
        """
        if not messages:
            raise CustomerIntelligenceError(
                "Cannot analyze an empty conversation with no messages.",
                status_code=400,
            )

        # Provider routing:
        # 1. 'ml': Use ML service explicitly
        if self.provider == "ml":
            return self.analyze_via_ml(messages, subject=subject)

        # 2. 'auto': Use ML service if Gemini API key is not configured, else Gemini
        if self.provider == "auto":
            if not self.api_key:
                logger.info("GEMINI_API_KEY not configured. Routing to ML service.")
                return self.analyze_via_ml(messages, subject=subject)
            return self.analyze_via_gemini(messages, subject=subject)

        # 3. 'gemini': Explicitly Gemini
        return self.analyze_via_gemini(messages, subject=subject)
