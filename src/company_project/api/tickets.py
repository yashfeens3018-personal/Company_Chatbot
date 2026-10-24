from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from datetime import datetime
from sqlalchemy.exc import IntegrityError


from ..queries.tickets import (
    get_ticket,
    search_tickets,
    get_unassigned_tickets,
    get_ticket_stats,
    create_ticket,
    update_ticket,
    delete_ticket
)

router=APIRouter()

def _call_ticket_member_query(query, *args, **kwargs):
    try:
        return query(*args, **kwargs)

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="Ticket data conflicts with existing records."
        ) from error

@router.get("/tickets")
def get_tickets_endpoint():
    return _call_ticket_member_query(search_tickets)


@router.get("/tickets/unassigned")
def get_unassigned_tickets_endpoint():
    return _call_ticket_member_query(get_unassigned_tickets)


@router.get("/tickets/stats")
def get_ticket_stats_endpoint():
    return _call_ticket_member_query(get_ticket_stats)


@router.get("/tickets/{ticket_id}")
def get_ticket_endpoint(ticket_id:int):
    return _call_ticket_member_query(get_ticket,ticket_id)


@router.delete("/tickets/{ticket_id}")
def delete_ticket_endpoint(ticket_id:int):
    return _call_ticket_member_query(delete_ticket,ticket_id)


class CreateTicket(BaseModel):
    created_by:int=Field(...,gt=0)
    title:str=Field(...,min_length=1,max_length=100)
    description:str=Field(...,min_length=1)
    category:str=Field(...,min_length=1,max_length=100)
    status:str=Field(default="open",min_length=1,max_length=100)
    priority:str=Field(default="medium",min_length=1,max_length=30)
    assigned_to:int|None=Field(default=None,gt=0)
    due_at:datetime|None=None


@router.post("/tickets")
def create_ticket_endpoint(ticket:CreateTicket):
    return _call_ticket_member_query(create_ticket,
        created_by=ticket.created_by,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        status=ticket.status,
        priority=ticket.priority,
        assigned_to=ticket.assigned_to,
        due_at=ticket.due_at)


class UpdateTicket(BaseModel):
    id:int=Field(...,gt=0)
    title:str|None=Field(default=None,min_length=1,max_length=100)
    description:str|None=Field(default=None,min_length=1)
    category:str|None=Field(default=None,min_length=1,max_length=100)
    status:str|None=Field(default=None,min_length=1,max_length=100)
    priority:str|None=Field(default=None,min_length=1,max_length=30)
    assigned_to:int|None=Field(default=None,gt=0)
    due_at:datetime|None=None


@router.put("/tickets/{ticket_id}")
def update_ticket_endpoint(
    ticket_id: int,
    ticket: UpdateTicket
):
    return _call_ticket_member_query(
        update_ticket,
        id=ticket_id,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        status=ticket.status,
        priority=ticket.priority,
        assigned_to=ticket.assigned_to,
        due_at=ticket.due_at
    )