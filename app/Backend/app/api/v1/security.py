import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.threat import Threat
from app.schemas.pagination import PaginatedResponse
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
)


@router.get(
    "/threats",
    response_model=PaginatedResponse[ThreatRead],
    status_code=status.HTTP_200_OK,
    summary="List persisted threat records",
    description=(
        "Retrieve a paginated list of persisted threat records with optional "
        "filtering by risk level and threat detection flag, plus text search "
        "across threat type and risk reasons."
    ),
)
def list_threats(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    threat_detected: Optional[bool] = Query(
        None, description="Filter by confirmed threat flag"
    ),
    search: Optional[str] = Query(
        None, description="Search across threat type and risk reasons"
    ),
    db: Session = Depends(get_db),
):
    query = select(Threat)

    if risk_level:
        query = query.where(Threat.risk_level == risk_level)
    if threat_detected is not None:
        query = query.where(Threat.threat_detected == threat_detected)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Threat.threat_type.ilike(term),
                Threat.risk_reasons.cast(String).ilike(term),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            query.order_by(Threat.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()
    )

    return PaginatedResponse[ThreatRead](
        items=[ThreatRead.model_validate(t) for t in items],
        page=page,
        page_size=page_size,
        total=int(total),
        total_pages=total_pages,
    )


@router.get(
    "/threats/{threat_id}",
    response_model=ThreatRead,
    status_code=status.HTTP_200_OK,
    summary="Get threat record by id",
    description="Retrieve a single persisted threat record by its identifier.",
)
def get_threat(
    threat_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    threat = db.scalar(select(Threat).where(Threat.id == threat_id))
    if not threat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat '{threat_id}' not found.",
        )
    return ThreatRead.model_validate(threat)


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
