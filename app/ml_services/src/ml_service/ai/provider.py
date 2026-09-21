"""Abstract provider interface for hosted AI services."""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Abstract base for all hosted AI providers.

    Concrete implementations must be safe to use from multiple threads
    (the FastAPI app state is shared across requests).
    """

    @abstractmethod
    def analyze(self, subject: str | None, message: str | None) -> object:
        """Run combined classification + sentiment + social engineering + summarization.

        Returns a validated ``GeminiAnalysisOutput`` (or provider-equivalent).
        Raises :class:`~ml_service.ai.exceptions.ProviderError` subclasses on
        unrecoverable failure.
        """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return dense embedding vectors for the given texts.

        Raises :class:`~ml_service.ai.exceptions.ProviderError` on failure.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the generation model identifier in use."""

    @property
    @abstractmethod
    def embedding_model_name(self) -> str:
        """Return the embedding model identifier in use."""
