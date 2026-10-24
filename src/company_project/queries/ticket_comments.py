from sqlalchemy import select,func,insert,update,delete
from datetime import datetime

from ..models import Employees,Ticket_Comments,Tickets
from ..database import SessionLocal


def _require_ticket(session,ticket_id:int):
    ticket_exists=session.execute(
        select(Tickets.ticket_id).where(
            Tickets.ticket_id==ticket_id
        )
    ).scalar_one_or_none()

    if ticket_exists is None:
        raise LookupError(f"Ticket with id {ticket_id} does not exist.")


def _require_employee(session,employee_id:int):
    employee_exists=session.execute(
        select(Employees.employee_id).where(
            Employees.employee_id==employee_id
        )
    ).scalar_one_or_none()

    if employee_exists is None:
        raise LookupError(f"Employee with id {employee_id} does not exist.")


def _validate_comment(comment:str):
    if not comment.strip():
        raise ValueError("Comment cannot be blank.")


def get_comment(comment_id:int):
    stmt=select(
        Ticket_Comments.comment_id,
        Ticket_Comments.ticket_id,
        Ticket_Comments.author_id,
        Ticket_Comments.comment,
        Ticket_Comments.created_at
    ).where(
        Ticket_Comments.comment_id==comment_id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        comment=result.one_or_none()

    if comment is None:
        raise LookupError(f"Comment with id {comment_id} does not exist.")

    return comment


def get_ticket_comments(ticket_id:int):
    with SessionLocal() as session:
        _require_ticket(session,ticket_id)

    stmt=select(
        Ticket_Comments.comment_id,
        Ticket_Comments.ticket_id,
        Ticket_Comments.author_id,
        Ticket_Comments.comment,
        Ticket_Comments.created_at
    ).where(
        Ticket_Comments.ticket_id==ticket_id
    ).order_by(
        Ticket_Comments.created_at.asc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        comments=[dict(row._mapping) for row in result.all()]

    return comments


def search_ticket_comments(
    ticket_id:int=None,
    author_id:int=None,
    comment:str=None,
    created_from:datetime=None,
    created_to:datetime=None
):
    conditions=[]

    if created_from is not None and created_to is not None and created_from>created_to:
        raise ValueError("Created-from date cannot be after created-to date.")

    with SessionLocal() as session:
        if ticket_id is not None:
            _require_ticket(session,ticket_id)
        if author_id is not None:
            _require_employee(session,author_id)

    if ticket_id is not None:
        conditions.append(Ticket_Comments.ticket_id==ticket_id)

    if author_id is not None:
        conditions.append(Ticket_Comments.author_id==author_id)

    if comment is not None:
        conditions.append(
            Ticket_Comments.comment.ilike(f"%{comment}%")
        )

    if created_from is not None:
        conditions.append(
            Ticket_Comments.created_at>=created_from
        )

    if created_to is not None:
        conditions.append(
            Ticket_Comments.created_at<=created_to
        )

    stmt=select(
        Ticket_Comments.comment_id,
        Ticket_Comments.ticket_id,
        Ticket_Comments.author_id,
        Ticket_Comments.comment,
        Ticket_Comments.created_at
    ).where(*conditions).order_by(
        Ticket_Comments.created_at.asc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        comments=[dict(row._mapping) for row in result.all()]

    return comments


def get_latest_ticket_comment(ticket_id:int):
    with SessionLocal() as session:
        _require_ticket(session,ticket_id)

    stmt=select(
        Ticket_Comments.comment_id,
        Ticket_Comments.ticket_id,
        Ticket_Comments.author_id,
        Ticket_Comments.comment,
        Ticket_Comments.created_at
    ).where(
        Ticket_Comments.ticket_id==ticket_id
    ).order_by(
        Ticket_Comments.created_at.desc()
    ).limit(1)

    with SessionLocal() as session:
        result=session.execute(stmt)
        comment=[dict(row._mapping) for row in result.all()]

    return comment


def get_comment_count(ticket_id:int):
    with SessionLocal() as session:
        _require_ticket(session,ticket_id)

    stmt=select(
        func.count(Ticket_Comments.comment_id)
    ).where(
        Ticket_Comments.ticket_id==ticket_id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        count=[dict(row._mapping) for row in result.all()]

    return count


def create_comment(
    ticket_id:int,
    author_id:int,
    comment:str
):
    _validate_comment(comment)

    with SessionLocal() as session:
        _require_ticket(session,ticket_id)
        _require_employee(session,author_id)

    stmt=insert(Ticket_Comments).values(
        ticket_id=ticket_id,
        author_id=author_id,
        comment=comment
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()
        comment_id=result.inserted_primary_key[0]

    return f"New comment with id: {comment_id} has been created successfully!"


def update_comment(
    id:int,
    comment:str=None
):
    if comment is None:
        raise ValueError("Provide a comment to update.")

    _validate_comment(comment)

    stmt=update(Ticket_Comments).where(
        Ticket_Comments.comment_id==id
    ).values(
        comment=comment
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    if result.rowcount==0:
        raise LookupError(f"Comment with id {id} does not exist.")

    return f"Comment with id: {id} has been updated successfully!"


def delete_comment(id:int):
    stmt=delete(Ticket_Comments).where(
        Ticket_Comments.comment_id==id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    if result.rowcount==0:
        raise LookupError(f"Comment with id {id} does not exist.")

    return f"Comment with id: {id} has been deleted successfully!"
