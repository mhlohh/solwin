from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.get("/facets", response_model=schemas.FacetsResponse)
def get_facets(db: Session = Depends(get_db)):
    """Totals, phishing count, distinct intents, and priority counts for inbox badges."""
    total, phishing_count, intents, priority_counts = crud.get_ticket_facets(db)
    return {
        "total": total,
        "phishing": phishing_count,
        "intents": intents,
        "priority_counts": priority_counts,
    }

@router.get("/stats", response_model=schemas.TicketStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Pre-aggregated dataset statistics for the dashboard bridge."""
    return crud.get_ticket_stats(db)

@router.get("", response_model=schemas.PaginatedTicketsResponse)
def list_tickets(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
    intent: Optional[str] = Query(None, description="Filter by intent category"),
    search: Optional[str] = Query(None, description="Search term in subject, message, or issue"),
    phishing: Optional[bool] = Query(None, description="Filter by phishing flag"),
    priority: Optional[str] = Query(None, description="Filter by priority tier (CRITICAL/HIGH/MEDIUM/LOW)"),
    db: Session = Depends(get_db)
):
    """
    Retrieve tickets list with pagination and optional filtering by intent or search term.
    """
    total, items = crud.get_tickets(
        db, skip=skip, limit=limit, intent=intent, search=search,
        phishing=phishing, priority=priority,
    )
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }

@router.get("/{ticket_id}", response_model=schemas.TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details of a single ticket by ID, including linked file attachments.
    """
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )
    return ticket

@router.post("", response_model=schemas.TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    """
    Create a new ticket.
    """
    return crud.create_ticket(db, ticket)

@router.put("/{ticket_id}", response_model=schemas.TicketResponse)
def update_ticket(ticket_id: int, ticket_update: schemas.TicketUpdate, db: Session = Depends(get_db)):
    """
    Update an existing ticket's subject, message, intent, or issue.
    """
    updated_ticket = crud.update_ticket(db, ticket_id, ticket_update)
    if not updated_ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )
    return updated_ticket

@router.delete("/{ticket_id}", status_code=status.HTTP_200_OK)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """
    Delete a ticket and its associated file attachments.
    """
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )

    # Delete local attachment files if present
    for attachment in ticket.attachments:
        import os
        if os.path.exists(attachment.file_path):
            try:
                os.remove(attachment.file_path)
            except Exception:
                pass

    crud.delete_ticket(db, ticket_id)
    return {"message": f"Ticket {ticket_id} and associated attachments successfully deleted."}
