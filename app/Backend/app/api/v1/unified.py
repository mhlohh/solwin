import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.enums import UserRole
from app.schemas.unified import (
    DirectMessageAnalysisRequest,
    UnifiedAnalysisRequest,
    UnifiedAnalysisResponse,
)
from app.services.unified_intelligence import (
    UnifiedIntelligenceError,
    UnifiedIntelligenceService,
)

router = APIRouter(
    prefix="/analyze",
    tags=["Unified Intelligence Pipeline"],
    dependencies=[
        Depends(
            require_role(
                UserRole.SUPPORT_AGENT,
                UserRole.SUPPORT_MANAGER,
                UserRole.SECURITY_ANALYST,
                UserRole.ADMIN,
            )
        )
    ],
)


@router.post(
    "",
    response_model=UnifiedAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run unified conversation analysis",
    description=(
        "Primary Solwin analysis endpoint: orchestrates Customer Support "
        "Intelligence and Security Intelligence across a conversation's "
        "message history, determines calibrated recommended action, "
        "persists Analysis and Threat records, and returns a unified result."
    ),
)
def analyze_conversation(
    payload: UnifiedAnalysisRequest,
    db: Session = Depends(get_db),
):
    try:
        result = UnifiedIntelligenceService.analyze_conversation(
            db=db,
            conversation_id=payload.conversation_id,
        )
        return result
    except UnifiedIntelligenceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during unified intelligence analysis.",
        ) from exc


@router.post(
    "/message",
    response_model=UnifiedAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct message unified analysis",
    description=(
        "Direct real-time analysis for security team investigation: runs both customer "
        "and security intelligence on a raw message without requiring or persisting "
        "a conversation record."
    ),
)
def analyze_direct_message(
    payload: DirectMessageAnalysisRequest,
):
    try:
        result = UnifiedIntelligenceService.analyze_direct_message(
            message_text=payload.message,
            expected_domain=payload.expected_domain,
        )
        return result
    except UnifiedIntelligenceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during direct message analysis.",
        ) from exc


@router.get(
    "/conversation/{conversation_id}",
    response_model=UnifiedAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest unified analysis",
    description=(
        "Retrieve the latest persisted unified customer and security analysis "
        "for a conversation without re-invoking AI or security engines."
    ),
)
def get_unified_analysis(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    try:
        result = UnifiedIntelligenceService.get_latest_unified_analysis(
            db=db,
            conversation_id=conversation_id,
        )
        return result
    except UnifiedIntelligenceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve unified analysis.",
        ) from exc
