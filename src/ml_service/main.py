"""ASGI entry point for the Customer Complaint Intelligence service."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from ml_service.api.routes import router
from ml_service.core.config import get_settings
from ml_service.core.logging import configure_logging, safe_log
from ml_service.core.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create the application and initialize process-wide, non-secret dependencies."""

    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Customer Complaint Intelligence ML Service",
        version="0.1.0",
        description="Privacy-conscious, modular ML service foundation.",
    )
    app.state.model_registry = ModelRegistry(settings.model_registry_path)

    @app.middleware("http")
    async def request_observability(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        safe_log(
            logger,
            "request_completed",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return response

    app.include_router(router)
    return app


app = create_app()
