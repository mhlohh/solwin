import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.enums import UserRole
from app.schemas.analysis import AnalysisRead, ConversationAnalysisResponse
from app.services.ai.customer_intelligence import (
    CustomerIntelligenceError,
    CustomerIntelligenceService,
)
from app.services.conversation_service import ConversationService

router = APIRouter(
    prefix="/analysis",
    tags=["Customer Intelligence"],
    dependencies=[
        Depends(
            require_role(
                UserRole.SUPPORT_AGENT,
                UserRole.SUPPORT_MANAGER,
                UserRole.ADMIN,
            )
        )
    ],
)


@router.post(
    "/conversation/{conversation_id}",
    response_model=ConversationAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze conversation",
    description=(
        "Analyze a conversation history using Gemini AI to extract structured "
        "customer support intelligence (issue, category, sentiment, emotion, "
        "priority, resolution status, summary) and persist the result."
    ),
)
def analyze_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    # 1. Retrieve conversation detail (including subject and messages)
    conversation = ConversationService.get_conversation_detail(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )

    # 2. Verify messages exist
    messages = conversation.messages
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot analyze an empty conversation with no messages.",
        )

    # 3. Call AI Service
    ai_service = CustomerIntelligenceService()
    try:
        intelligence = ai_service.analyze_conversation(
            messages=messages,
            subject=conversation.subject,
        )
    except CustomerIntelligenceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred during customer intelligence analysis.",
        ) from exc

    # 4. Save or update analysis record
    analysis = ConversationService.save_or_update_analysis(
        db=db,
        conversation_id=conversation_id,
        intelligence=intelligence,
    )

    return ConversationAnalysisResponse(
        conversation_id=conversation_id,
        analysis=AnalysisRead.model_validate(analysis),
    )


@router.get(
    "/conversation/{conversation_id}",
    response_model=ConversationAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest conversation analysis",
    description=(
        "Retrieve the latest available customer support analysis for a "
        "conversation without calling Gemini."
    ),
)
def get_conversation_analysis(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    # Verify conversation exists
    conversation = ConversationService.get_conversation_detail(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )

    analysis = ConversationService.get_latest_analysis(db, conversation_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found for conversation '{conversation_id}'.",
        )

    return ConversationAnalysisResponse(
        conversation_id=conversation_id,
        analysis=AnalysisRead.model_validate(analysis),
    )
