from datetime import datetime

from fastapi import APIRouter,HTTPException,Path,Query
from pydantic import BaseModel,Field
from sqlalchemy.exc import IntegrityError

from ..queries.ticket_comments import (
    create_comment,
    delete_comment,
    get_comment,
    get_comment_count,
    get_latest_ticket_comment,
    get_ticket_comments,
    search_ticket_comments,
    update_comment
)

router=APIRouter()


def _call_ticket_comment_query(query,*args,**kwargs):
    try:
        return query(*args,**kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409,detail="Ticket comment data conflicts with existing records.") from error


@router.get("/ticket-comments")
def search_ticket_comments_endpoint(
    ticket_id:int|None=Query(default=None,gt=0),
    author_id:int|None=Query(default=None,gt=0),
    comment:str|None=Query(default=None,min_length=1),
    created_from:datetime|None=None,
    created_to:datetime|None=None
):
    return _call_ticket_comment_query(
        search_ticket_comments,
        ticket_id=ticket_id,
        author_id=author_id,
        comment=comment,
        created_from=created_from,
        created_to=created_to
    )


@router.get("/ticket-comments/ticket/{ticket_id}")
def get_ticket_comments_endpoint(ticket_id:int=Path(...,gt=0)):
    return _call_ticket_comment_query(get_ticket_comments,ticket_id)


@router.get("/ticket-comments/ticket/{ticket_id}/latest")
def get_latest_ticket_comment_endpoint(ticket_id:int=Path(...,gt=0)):
    return _call_ticket_comment_query(get_latest_ticket_comment,ticket_id)


@router.get("/ticket-comments/ticket/{ticket_id}/count")
def get_ticket_comment_count_endpoint(ticket_id:int=Path(...,gt=0)):
    return _call_ticket_comment_query(get_comment_count,ticket_id)


@router.get("/ticket-comments/{comment_id}")
def get_comment_endpoint(comment_id:int=Path(...,gt=0)):
    return _call_ticket_comment_query(get_comment,comment_id)


class CreateTicketComment(BaseModel):
    ticket_id:int=Field(...,gt=0)
    author_id:int=Field(...,gt=0)
    comment:str=Field(...,min_length=1)


@router.post("/ticket-comments")
def create_comment_endpoint(request:CreateTicketComment):
    return _call_ticket_comment_query(
        create_comment,
        ticket_id=request.ticket_id,
        author_id=request.author_id,
        comment=request.comment
    )


class UpdateTicketComment(BaseModel):
    id:int=Field(...,gt=0)
    comment:str=Field(...,min_length=1)


@router.put("/ticket-comments")
def update_comment_endpoint(request:UpdateTicketComment):
    return _call_ticket_comment_query(
        update_comment,
        id=request.id,
        comment=request.comment
    )


@router.delete("/ticket-comments/{comment_id}")
def delete_comment_endpoint(comment_id:int=Path(...,gt=0)):
    return _call_ticket_comment_query(delete_comment,comment_id)
