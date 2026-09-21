import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response

from ml_service.ai.exceptions import ProviderConfigError, ProviderError
from ml_service.ai.gemini_provider import GeminiProvider
from ml_service.analytics.frequency import FrequencyTracker
from ml_service.api.routes import router
from ml_service.classification.classifier import ComplaintClassifier
from ml_service.clustering.clusterer import ComplaintClusterer
from ml_service.core.config import get_settings
from ml_service.core.logging import configure_logging, safe_log
from ml_service.core.model_registry import ModelRegistry
from ml_service.orchestration.pipeline import GeminiPipeline
from ml_service.recommendation.engine import RecommendationEngine
from ml_service.resolution.detector import ResolutionDetector
from ml_service.security.email_analyzer import EmailAnalyzer
from ml_service.security.url_analyzer import URLAnalyzer
from ml_service.summarization.summarizer import ConversationSummarizer
from ml_service.urgency.detector import UrgencyDetector

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="Customer Complaint Intelligence ML Service", version="0.1.0")
    app.state.model_registry = ModelRegistry(settings.model_registry_path)

    # Initialize models once on startup
    primary_model_path = settings.model_dir / "complaint_classifier_v1.joblib"
    fg_model_path = settings.model_dir / "intent_classifier_v1.joblib"
    app.state.classifier = ComplaintClassifier(
        model_path=primary_model_path,
        confidence_threshold=settings.model_confidence_threshold,
        fine_grained_model_path=fg_model_path,
    )

    cluster_model_path = settings.model_dir / "clusterer_v1.joblib"
    cluster_meta_path = settings.model_dir / "clusters_metadata.json"
    app.state.clusterer = ComplaintClusterer(
        model_path=cluster_model_path,
        metadata_path=cluster_meta_path,
    )

    app.state.frequency_tracker = FrequencyTracker()
    app.state.urgency_detector = UrgencyDetector()
    app.state.resolution_detector = ResolutionDetector()
    app.state.recommendation_engine = RecommendationEngine(Path("config/action_rules.yaml"))
    app.state.url_analyzer = URLAnalyzer()
    app.state.email_analyzer = EmailAnalyzer()
    app.state.summarizer = ConversationSummarizer(
        resolution_detector=app.state.resolution_detector
    )

    # --- Gemini AI provider (optional — app starts even if unavailable) ---
    ai_provider: GeminiProvider | None = None
    if settings.gemini_enabled:
        try:
            ai_provider = GeminiProvider(settings)
            logger.info("Gemini AI provider initialized: model=%s", settings.gemini_model)
        except (ProviderConfigError, ProviderError) as exc:
            logger.warning(
                "Gemini AI provider could not be initialized (%s). "
                "Local fallbacks will be used.",
                exc,
            )
        except Exception as exc:
            logger.error(
                "Unexpected error initializing Gemini provider (%s). "
                "Local fallbacks will be used.",
                type(exc).__name__,
            )
    else:
        logger.info("Gemini AI provider disabled (GEMINI_ENABLED=false). Using local models.")

    app.state.ai_provider = ai_provider
    app.state.gemini_pipeline = GeminiPipeline(
        ai_provider=ai_provider,
        local_classifier=app.state.classifier,
        settings=settings,
    )

    @app.middleware("http")
    async def observability(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        safe_log(logger, "request_completed", request_id=request_id, path=request.url.path,
                 method=request.method, status_code=response.status_code,
                 latency_ms=round((time.perf_counter() - started) * 1000, 2))
        return response

    app.include_router(router)
    return app


app = create_app()

