from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

# --- Attachment Schemas ---
class AttachmentBase(BaseModel):
    file_name: str
    file_type: str
    file_size: int

class AttachmentCreate(AttachmentBase):
    file_path: str

class AttachmentResponse(AttachmentBase):
    id: int
    ticket_id: int
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Ticket Schemas ---
class TicketBase(BaseModel):
    message: str
    domain: Optional[str] = ""
    channel: Optional[str] = ""
    subject: Optional[str] = ""
    intent: Optional[str] = ""
    issue: Optional[str] = ""
    technique: Optional[str] = ""
    phishing: Optional[bool] = None
    sender: Optional[str] = ""
    label: Optional[str] = ""

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    message: Optional[str] = None
    domain: Optional[str] = None
    channel: Optional[str] = None
    subject: Optional[str] = None
    intent: Optional[str] = None
    issue: Optional[str] = None
    technique: Optional[str] = None
    phishing: Optional[bool] = None
    sender: Optional[str] = None
    label: Optional[str] = None

class TicketResponse(TicketBase):
    id: int
    created_at: datetime
    attachments: List[AttachmentResponse] = []

    model_config = ConfigDict(from_attributes=True)

class PaginatedTicketsResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TicketResponse]
