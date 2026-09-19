import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.attachment import Attachment
from app.models.conversation import Conversation
from app.models.enums import UserRole
from app.models.message import Message
from app.schemas.attachment import AttachmentRead
from app.services.attachments.local_storage import get_storage_backend
from app.services.attachments.storage import StorageBackend
from app.services.attachments.validation import (
    calculate_sha256,
    validate_file_content,
)

router = APIRouter(
    tags=["Attachments"],
)


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an attachment for a conversation message",
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
async def upload_attachment(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="The attachment file")],
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> AttachmentRead:
    # 1. Verify conversation exists
    conversation = db.scalar(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    # 2. Verify message exists and belongs to this conversation
    message = db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found in conversation {conversation_id}.",
        )

    # 3. Read content and validate
    content = await file.read()
    sanitized_filename, validated_mime = validate_file_content(
        content=content,
        original_filename=file.filename or "attachment",
        declared_content_type=file.content_type,
    )

    # 4. Generate metadata & storage key
    checksum = calculate_sha256(content)
    attachment_id = uuid.uuid4()
    storage_key = f"{conversation_id}/{attachment_id}"

    # 5. Save file to storage backend
    await storage.save(storage_key, content)

    now = datetime.now(timezone.utc)
    # 6. Persist metadata record in PostgreSQL
    attachment = Attachment(
        id=attachment_id,
        conversation_id=conversation_id,
        message_id=message_id,
        original_filename=sanitized_filename,
        content_type=validated_mime,
        file_size=len(content),
        storage_key=storage_key,
        checksum=checksum,
        created_at=now,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return AttachmentRead.model_validate(attachment)


@router.get(
    "/attachments/{attachment_id}",
    summary="Download attachment content",
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
async def download_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    attachment = db.scalar(select(Attachment).where(Attachment.id == attachment_id))
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment {attachment_id} not found.",
        )

    try:
        content = await storage.get(attachment.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment data file missing from storage.",
        )

    filename = attachment.original_filename
    return Response(
        content=content,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attachment",
    dependencies=[
        Depends(
            require_role(
                UserRole.SUPPORT_MANAGER,
                UserRole.ADMIN,
            )
        )
    ],
)
async def delete_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> None:
    attachment = db.scalar(select(Attachment).where(Attachment.id == attachment_id))
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment {attachment_id} not found.",
        )

    # Delete from storage backend
    await storage.delete(attachment.storage_key)

    # Delete metadata from database
    db.delete(attachment)
    db.commit()
