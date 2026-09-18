from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Tuple
from . import models, schemas
from .priority import PRIORITY_RANKS, assign_priority

# FIFO priority queue: priority tier first, oldest within a tier on top.
_PRIORITY_ORDER = case(
    PRIORITY_RANKS,
    value=models.Ticket.priority,
    else_=max(PRIORITY_RANKS.values()),
)

# --- Ticket Operations ---

def get_ticket(db: Session, ticket_id: int) -> Optional[models.Ticket]:
    return db.query(models.Ticket).options(joinedload(models.Ticket.attachments)).filter(models.Ticket.id == ticket_id).first()

def _base_filters(query, intent: Optional[str], search: Optional[str], phishing: Optional[bool]):
    """Apply the shared list filters used by both listing and facet queries."""
    if intent:
        query = query.filter(models.Ticket.intent == intent)
    if phishing is not None:
        query = query.filter(models.Ticket.phishing == phishing)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (models.Ticket.message.ilike(search_filter)) |
            (models.Ticket.subject.ilike(search_filter)) |
            (models.Ticket.issue.ilike(search_filter))
        )
    return query


def get_tickets(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    intent: Optional[str] = None,
    search: Optional[str] = None,
    phishing: Optional[bool] = None,
    priority: Optional[str] = None
):
    query = _base_filters(
        db.query(models.Ticket).options(joinedload(models.Ticket.attachments)),
        intent, search, phishing
    )
    if priority:
        query = query.filter(models.Ticket.priority == priority.upper())

    total = query.count()
    items = (
        query
        .order_by(_PRIORITY_ORDER.asc(), models.Ticket.created_at.asc(), models.Ticket.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return total, items

def get_ticket_facets(db: Session) -> Tuple[int, int, List[str], dict]:
    """Return (total, phishing_count, sorted_distinct_intents) for inbox tab badges."""
    total = db.query(func.count(models.Ticket.id)).scalar() or 0
    phishing_count = (
        db.query(func.count(models.Ticket.id))
        .filter(models.Ticket.phishing == True)  # noqa: E712
        .scalar() or 0
    )
    intents = [
        row[0] for row in
        db.query(models.Ticket.intent)
        .filter(models.Ticket.intent != "")
        .distinct()
        .order_by(models.Ticket.intent)
        .all()
    ]
    priority_counts = {
        tier: count
        for tier, count in (
            db.query(models.Ticket.priority, func.count(models.Ticket.id))
            .group_by(models.Ticket.priority)
            .all()
        )
    }
    return total, phishing_count, intents, priority_counts


def get_ticket_stats(db: Session, top_intents_limit: int = 8) -> dict:
    """Pre-aggregated dataset statistics for the dashboard bridge."""
    total, phishing_count, intents, priority_counts = get_ticket_facets(db)
    intent_rows = (
        db.query(models.Ticket.intent, func.count(models.Ticket.id).label("n"))
        .filter(models.Ticket.intent != "")
        .group_by(models.Ticket.intent)
        .order_by(desc("n"))
        .limit(top_intents_limit)
        .all()
    )
    return {
        "total_records": total,
        "phishing_flagged": phishing_count,
        "priority_counts": priority_counts,
        "top_intents": [
            {"issue": row[0], "count": row[1]} for row in intent_rows
        ],
    }


def create_ticket(db: Session, ticket: schemas.TicketCreate) -> models.Ticket:
    priority = (ticket.priority or "").upper()
    if priority not in PRIORITY_RANKS:
        priority = assign_priority(
            phishing=ticket.phishing,
            technique=ticket.technique,
            intent=ticket.intent,
            issue=ticket.issue,
            label=ticket.label,
        )
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
        label=ticket.label or "",
        priority=priority,
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

    # Re-derive priority when any signal the rules read has changed.
    if any(k in update_dict for k in ("phishing", "technique", "intent", "issue", "label")):
        db_ticket.priority = assign_priority(
            phishing=db_ticket.phishing,
            technique=db_ticket.technique,
            intent=db_ticket.intent,
            issue=db_ticket.issue,
            label=db_ticket.label,
        )

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
