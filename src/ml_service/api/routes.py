"""Phase-one HTTP routes with explicit unavailable-model behavior."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from ml_service.api.schemas import ErrorResponse, HealthResponse, ReadinessResponse
from ml_service.core.model_registry import ModelRegistry

router = APIRouter()


def get_registry(request: Request) -> ModelRegistry:
    return request.app.state.model_registry  # type: ignore[no-any-return]


@router.get("/health", response_model=HealthResponse, tags=["operations"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="customer-complaint-intelligence", version="0.1.0")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
    tags=["operations"],
)
def ready(request: Request) -> ReadinessResponse | JSONResponse:
    registry = get_registry(request)
    if registry.is_ready():
        return ReadinessResponse(status="ready", models_ready=True)
    response = ReadinessResponse(
        status="not_ready",
        models_ready=False,
        detail="No production model is registered. Train and register a model before serving inference.",
    )
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response.model_dump())


@router.get("/api/v1/models", tags=["models"])
def list_models(request: Request) -> dict[str, object]:
    return {"models": get_registry(request).list()}


@router.get("/api/v1/capabilities", tags=["operations"])
def capabilities() -> dict[str, object]:
    return {
        "status": "foundation_only",
        "available": ["health", "readiness", "model_registry"],
        "planned": ["classification", "clustering", "urgency", "resolution", "url", "email", "summary"],
    }


@router.get("/api/v1/unavailable", response_model=ErrorResponse, tags=["operations"])
def unavailable() -> JSONResponse:
    error = ErrorResponse(
        errors=[
            {
                "component": "ml_pipeline",
                "code": "MODEL_NOT_READY",
                "message": "Inference endpoints are added after a trained model is registered.",
            }
        ]
    )
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=error.model_dump())
