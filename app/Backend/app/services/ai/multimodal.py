import json
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.attachment import MultimodalAnalysisOutput
from app.services.ai.prompts import MULTIMODAL_SYSTEM_INSTRUCTION

logger = get_logger("solwin.multimodal")


class MultimodalServiceError(Exception):
    """Base exception for multimodal service failures."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class MultimodalService:
    """Service for analyzing attachments using Gemini Multimodal capabilities."""

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
            raise MultimodalServiceError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY.",
                status_code=503,
            )

        try:
            self._client = genai.Client(api_key=self.api_key)
            return self._client
        except Exception as exc:
            logger.error(f"Failed to initialize Google GenAI Client: {exc}")
            raise MultimodalServiceError(
                "Failed to initialize Gemini AI client.",
                status_code=500,
            ) from exc

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        filename: Optional[str] = None,
    ) -> MultimodalAnalysisOutput:
        """Analyze image or supported document bytes using Gemini multimodal model."""
        if not image_bytes:
            raise MultimodalServiceError(
                "Cannot analyze empty attachment bytes.",
                status_code=400,
            )

        client = self.get_client()

        # Build part from bytes
        part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type,
        )

        user_prompt = (
            f"Analyze this attached file ({filename or 'attachment'}). "
            "Extract any visible text, customer context, failure indicators, "
            "security indicators, visible URLs, and visible email addresses."
        )

        try:
            config = types.GenerateContentConfig(
                system_instruction=MULTIMODAL_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=MultimodalAnalysisOutput,
                temperature=0.1,
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=[part, user_prompt],
                config=config,
            )
        except MultimodalServiceError:
            raise
        except Exception as exc:
            err_msg = str(exc)
            logger.error(f"Gemini multimodal call failed: {err_msg}")
            if "not found" in err_msg.lower() or "unsupported" in err_msg.lower():
                raise MultimodalServiceError(
                    f"Configured Gemini model '{self.model_name}' is "
                    "unavailable or unsupported.",
                    status_code=502,
                ) from exc
            if "quota" in err_msg.lower() or "resource" in err_msg.lower():
                raise MultimodalServiceError(
                    "Gemini API quota or rate limit exceeded.",
                    status_code=503,
                ) from exc
            raise MultimodalServiceError(
                "Gemini AI service encountered an error while processing attachment.",
                status_code=502,
            ) from exc

        # Parse structured response
        raw_text = response.text
        if not raw_text or not raw_text.strip():
            logger.warning("Empty response received from Gemini multimodal model.")
            return MultimodalAnalysisOutput()

        try:
            data = json.loads(raw_text)
            return MultimodalAnalysisOutput.model_validate(data)
        except Exception as exc:
            logger.warning(
                f"Failed to parse multimodal JSON response: {exc}. "
                f"Raw: {raw_text[:200]}"
            )

            return MultimodalAnalysisOutput(
                visible_text=raw_text[:500],
                attachment_summary="Visual attachment analyzed",
            )
