import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas

router = APIRouter(tags=["Attachments"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "")
if not UPLOAD_DIR:
    # Default to <backend>/uploads so the API runs anywhere (Docker sets UPLOAD_DIR=/app/uploads)
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except OSError as exc:
    raise RuntimeError(
        f"Cannot create upload directory '{UPLOAD_DIR}'. "
        "Set the UPLOAD_DIR environment variable to a writable path."
    ) from exc

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpeg",
    "image/jpg": ".jpg"
}

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

@router.post("/tickets/{ticket_id}/attachments", response_model=schemas.AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF or Image (PNG, JPEG) attachment linked to a specific ticket ID.
    Strict MIME type validation is enforced.
    """
    # 1. Verify ticket exists
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )

    # 2. Extract and sanitize file information
    filename = file.filename or "file"
    file_ext = os.path.splitext(filename)[1].lower()
    content_type = (file.content_type or "").lower()

    # Normalize image/jpg content type
    if content_type == "image/jpg":
        content_type = "image/jpeg"

    # 3. Validate MIME type & file extension
    is_valid_mime = content_type in ALLOWED_MIME_TYPES
    is_valid_ext = file_ext in ALLOWED_EXTENSIONS

    if not is_valid_mime or not is_valid_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file type '{file.content_type}'. "
                f"Only PDFs (application/pdf) and Images (image/png, image/jpeg) are accepted."
            )
        )

    # 4. Save file to disk
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    contents = await file.read()
    file_size = len(contents)

    with open(file_path, "wb") as f:
        f.write(contents)

    # 5. Save record in database
    attachment = crud.create_attachment(
        db=db,
        ticket_id=ticket_id,
        file_name=filename,
        file_type=content_type,
        file_path=file_path,
        file_size=file_size
    )

    return attachment

@router.get("/tickets/{ticket_id}/attachments", response_model=List[schemas.AttachmentResponse])
def list_ticket_attachments(ticket_id: int, db: Session = Depends(get_db)):
    """
    List all file attachments belonging to a ticket.
    """
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )
    return crud.get_attachments_by_ticket(db, ticket_id)

@router.get("/attachments/{attachment_id}")
def download_attachment(attachment_id: int, db: Session = Depends(get_db)):
    """
    Retrieve/download an uploaded attachment file by attachment ID.
    """
    attachment = crud.get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment with ID {attachment_id} not found."
        )

    if not os.path.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content not found on server disk."
        )

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.file_name,
        media_type=attachment.file_type
    )

@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_200_OK)
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    """
    Delete an attachment file from disk and database.
    """
    attachment = crud.get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment with ID {attachment_id} not found."
        )

    if os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except Exception:
            pass

    crud.delete_attachment(db, attachment_id)
    return {"message": f"Attachment {attachment_id} deleted successfully."}
