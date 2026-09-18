from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from . import models, schemas

# --- Ticket Operations ---

def get_ticket(db: Session, ticket_id: int) -> Optional[models.Ticket]:
    return db.query(models.Ticket).options(joinedload(models.Ticket.attachments)).filter(models.Ticket.id == ticket_id).first()

def get_tickets(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    intent: Optional[str] = None,
    search: Optional[str] = None
):
    query = db.query(models.Ticket).options(joinedload(models.Ticket.attachments))
    if intent:
        query = query.filter(models.Ticket.intent == intent)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (models.Ticket.message.ilike(search_filter)) |
            (models.Ticket.subject.ilike(search_filter)) |
            (models.Ticket.issue.ilike(search_filter))
        )
    
    total = query.count()
    items = query.order_by(models.Ticket.id.desc()).offset(skip).limit(limit).all()
    return total, items

def create_ticket(db: Session, ticket: schemas.TicketCreate) -> models.Ticket:
    db_ticket = models.Ticket(
        message=ticket.message,
        domain=ticket.domain or "",
        channel=ticket.channel or "",
        subject=ticket.subject or "",
        intent=ticket.intent or "",
        issue=ticket.issue or "",
        technique=ticket.technique or "",
        phishing=ticket.phishing,
        sender=ticket.sender or "",
        label=ticket.label or ""
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

def update_ticket(db: Session, ticket_id: int, ticket_data: schemas.TicketUpdate) -> Optional[models.Ticket]:
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return None

    update_dict = ticket_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            setattr(db_ticket, key, value)

    db.commit()
    db.refresh(db_ticket)
    return db_ticket

def delete_ticket(db: Session, ticket_id: int) -> bool:
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return False
    
    db.delete(db_ticket)
    db.commit()
    return True


# --- Attachment Operations ---

def create_attachment(
    db: Session,
    ticket_id: int,
    file_name: str,
    file_type: str,
    file_path: str,
    file_size: int
) -> models.Attachment:
    db_attachment = models.Attachment(
        ticket_id=ticket_id,
        file_name=file_name,
        file_type=file_type,
        file_path=file_path,
        file_size=file_size
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment

def get_attachment(db: Session, attachment_id: int) -> Optional[models.Attachment]:
    return db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()

def get_attachments_by_ticket(db: Session, ticket_id: int) -> List[models.Attachment]:
    return db.query(models.Attachment).filter(models.Attachment.ticket_id == ticket_id).all()

def delete_attachment(db: Session, attachment_id: int) -> bool:
    attachment = get_attachment(db, attachment_id)
    if not attachment:
        return False
    db.delete(attachment)
    db.commit()
    return True
