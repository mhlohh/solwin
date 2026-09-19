import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.enums import UserRole
from app.schemas.threat import (
    ConversationSecurityResponse,
    SecurityAnalysisRequest,
    ThreatBase,
    ThreatRead,
)
from app.services.conversation_service import ConversationService
from app.services.security.risk_engine import RiskEngine

router = APIRouter(
    prefix="/security",
    tags=["Security Intelligence"],
    dependencies=[
        Depends(
            require_role(
                UserRole.SECURITY_ANALYST,
                UserRole.SUPPORT_MANAGER,
                UserRole.ADMIN,
            )
        )
    ],
)


@router.post(
    "/analyze",
    response_model=ThreatBase,
    status_code=status.HTTP_200_OK,
    summary="Direct security analysis",
    description=(
        "Analyze a raw message or text snippet for suspicious URLs, lookalike "
        "domains, spoofed email addresses, social engineering lures, and risk level."
    ),
)
def analyze_direct_message(
    payload: SecurityAnalysisRequest,
):
    engine = RiskEngine()
    result = engine.evaluate(
        text=payload.message,
        expected_domain=payload.expected_domain,
        display_name=payload.display_name,
    )
    return ThreatBase(
        threat_detected=result.threat_detected,
        threat_type=result.threat_type,
        social_engineering_detected=result.social_engineering_detected,
        techniques=result.techniques,
        risk_level=result.risk_level,
        suspicious_urls=result.suspicious_urls,
        suspicious_emails=result.suspicious_emails,
        risk_reasons=result.risk_reasons,
        recommended_action=result.recommended_action,
    )


@router.post(
    "/conversation/{conversation_id}",
    response_model=ConversationSecurityResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze conversation security",
    description=(
        "Run the security intelligence engine across all messages in a conversation, "
        "persisting the resulting threat assessment in the threats table."
    ),
)
def analyze_conversation_security(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    # 1. Retrieve conversation detail
    conversation = ConversationService.get_conversation_detail(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )

    # 2. Verify messages
    messages = conversation.messages
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot analyze security on an empty conversation with no messages.",
        )

    # 3. Aggregate message content
    combined_texts = []
    if conversation.subject:
        combined_texts.append(f"Subject: {conversation.subject}")

    for msg in messages:
        sender = (
            msg.sender_type.value
            if hasattr(msg.sender_type, "value")
            else str(msg.sender_type)
        )
        sender_label = f"[{sender}]"
        if msg.sender_name:
            sender_label += f" {msg.sender_name}"
        combined_texts.append(f"{sender_label}: {msg.content}")

    aggregated_content = "\n".join(combined_texts)

    # 4. Evaluate through RiskEngine
    engine = RiskEngine()
    security_result = engine.evaluate(text=aggregated_content)

    # 5. Persist Threat record
    threat = ConversationService.save_or_update_threat(
        db=db,
        conversation_id=conversation_id,
        security_result=security_result,
    )

    return ConversationSecurityResponse(
        conversation_id=conversation_id,
        threat=ThreatRead.model_validate(threat),
    )


@router.get(
    "/conversation/{conversation_id}",
    response_model=ConversationSecurityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest security analysis",
    description="Retrieve the latest stored security threat record for a conversation.",
)
def get_conversation_security(
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

    threat = ConversationService.get_latest_threat(db, conversation_id)
    if not threat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security analysis found for conversation '{conversation_id}'.",
        )

    return ConversationSecurityResponse(
        conversation_id=conversation_id,
        threat=ThreatRead.model_validate(threat),
    )
