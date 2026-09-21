import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.database import get_db
from app.models.enums import ConversationChannel, ConversationStatus
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailRead,
    ConversationRead,
    ConversationUpdate,
)
from app.schemas.message import (
    MessageCreate,
    MessageRead,
)
from app.schemas.pagination import PaginatedResponse
from app.services.conversation_service import ConversationService

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.post(
    "",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
    description=(
        "Create a conversation with an auto-generated reference (e.g. CONV-000001) "
        "and an optional initial message in a single transaction."
    ),
)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
):
    try:
        conversation = ConversationService.create_conversation(db, payload)
        return conversation
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation.",
        ) from exc


@router.get(
    "",
    response_model=PaginatedResponse[ConversationRead],
    status_code=status.HTTP_200_OK,
    summary="List conversations",
    description=(
        "Retrieve a paginated list of conversations with optional "
        "filtering and search."
    ),
)
def list_conversations(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status_filter: Optional[ConversationStatus] = Query(
        None, alias="status", description="Filter by conversation status"
    ),
    channel: Optional[ConversationChannel] = Query(
        None, description="Filter by communication channel"
    ),
    assigned_agent_id: Optional[uuid.UUID] = Query(
        None, description="Filter by assigned user UUID"
    ),
    search: Optional[str] = Query(
        None,
        description="Search across reference, customer name, email, or subject",
    ),
    db: Session = Depends(get_db),
):
    items, total, total_pages = ConversationService.list_conversations(
        db=db,
        page=page,
        page_size=page_size,
        status=status_filter,
        channel=channel,
        assigned_agent_id=assigned_agent_id,
        search=search,
    )
    return PaginatedResponse[ConversationRead](
        items=[ConversationRead.model_validate(c) for c in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get conversation detail",
    description=(
        "Retrieve full details for a conversation including messages, "
        "existing analysis, and threat records."
    ),
)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    conversation = ConversationService.get_conversation_detail(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return conversation


@router.patch(
    "/{conversation_id}",
    response_model=ConversationRead,
    status_code=status.HTTP_200_OK,
    summary="Update conversation",
    description="Update metadata, status, or assigned agent for a conversation.",
)
def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
):
    updated = ConversationService.update_conversation(db, conversation_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return updated


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete conversation",
    description=(
        "Delete a conversation and cascade-delete its messages, analysis "
        "records, and threats without deleting users."
    ),
)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    success = ConversationService.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return {
        "success": True,
        "message": f"Conversation '{conversation_id}' deleted successfully.",
    }


# ==========================================
# Message Endpoints
# ==========================================


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create message for conversation",
    description=(
        "Append a new message (from customer, agent, or system) to an "
        "existing conversation."
    ),
)
def create_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
):
    message = ConversationService.create_message(db, conversation_id, payload)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return message


@router.get(
    "/{conversation_id}/messages",
    response_model=List[MessageRead],
    status_code=status.HTTP_200_OK,
    summary="List messages for conversation",
    description=(
        "Retrieve messages belonging to the conversation ordered "
        "chronologically by creation timestamp."
    ),
)
def list_messages(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    messages = ConversationService.list_messages(db, conversation_id)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID '{conversation_id}' not found.",
        )
    return messages
