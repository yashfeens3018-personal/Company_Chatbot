from sqlalchemy import select,func,insert,update,delete
from datetime import datetime

from ..models import Tickets,Employees
from ..database import SessionLocal

def employee_id_exists(employee_id:int):
    stmt=select(Employees.employee_id).where(Employees.employee_id==employee_id)
    with SessionLocal() as session:
        result=session.execute(stmt)
        employee=result.one_or_none()
    if employee is None:
        raise LookupError(f"Employee with ID {employee_id} does not exist.")


ticket_statuses=["open","in progress","pending","resolved","closed"]
ticket_priorities=["low","medium","high","critical"]
ticket_categories=["it_support","hr","finance","facilities","access_request","software","hardware","network","security","payroll","leave","other"]

def get_ticket(ticket_id:int):
    stmt=select(
        Tickets.ticket_id,
        Tickets.title,
        Tickets.description,
        Tickets.category,
        Tickets.status,
        Tickets.priority,
        Tickets.created_at,
        Tickets.updated_at,
        Tickets.due_at,
        Tickets.resolved_at,
        Tickets.closed_at,
        Tickets.created_by,
        Tickets.assigned_to
    ).where(
        Tickets.ticket_id==ticket_id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        ticket=[dict(row._mapping) for row in result.all()]

    return ticket


def search_tickets(
    assigned_to:int=None,
    created_by:int=None,
    status:str=None,
    priority:str=None,
    category:str=None,
    title:str=None,
    description:str=None,
    created_from:datetime=None,
    created_to:datetime=None,
    resolved_from:datetime=None,
    resolved_to:datetime=None,
    closed_from:datetime=None,
    closed_to:datetime=None
):
    conditions=[]

    if assigned_to is not None:
        employee_id_exists(assigned_to)
        conditions.append(Tickets.assigned_to==assigned_to)

    if created_by is not None:
        employee_id_exists(created_by)
        conditions.append(Tickets.created_by==created_by)

    if status is not None:
        if status.lower() not in ticket_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(ticket_statuses)}")
        conditions.append(Tickets.status==status.lower())

    if priority is not None:
        if priority.lower() not in ticket_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(ticket_priorities)}")
        conditions.append(Tickets.priority==priority.lower())

    if category is not None:
        if category.lower() not in ticket_categories:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(ticket_categories)}")
        conditions.append(Tickets.category==category.lower())
    

    if title is not None:
        conditions.append(Tickets.title.ilike(f"%{title}%"))

    if description is not None:
        conditions.append(Tickets.description.ilike(f"%{description}%"))

    if created_from is not None:
        conditions.append(Tickets.created_at>=created_from)

    if created_to is not None:
        conditions.append(Tickets.created_at<=created_to)

    if resolved_from is not None:
        conditions.append(Tickets.resolved_at>=resolved_from)

    if resolved_to is not None:
        conditions.append(Tickets.resolved_at<=resolved_to)

    if closed_from is not None:
        conditions.append(Tickets.closed_at>=closed_from)

    if closed_to is not None:
        conditions.append(Tickets.closed_at<=closed_to)

    stmt=select(
        Tickets.ticket_id,
        Tickets.title,
        Tickets.category,
        Tickets.status,
        Tickets.priority,
        Tickets.created_at,
        Tickets.due_at,
        Tickets.resolved_at,
        Tickets.closed_at,
        Tickets.created_by,
        Tickets.assigned_to
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        tickets=[dict(row._mapping) for row in result.all()]

    return tickets


def get_unassigned_tickets(
    status:str=None,
    priority:str=None,
    category:str=None
):
    conditions=[
        Tickets.assigned_to.is_(None)
    ]

    if status is not None:
        if status.lower() not in ticket_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(ticket_statuses)}")
        conditions.append(Tickets.status==status.lower())

    if priority is not None:
        if priority.lower() not in ticket_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(ticket_priorities)}")
        conditions.append(Tickets.priority==priority.lower())

    if category is not None:
        if category.lower() not in ticket_categories:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(ticket_categories)}")
        conditions.append(Tickets.category==category.lower())


    stmt=select(
        Tickets.ticket_id,
        Tickets.title,
        Tickets.category,
        Tickets.status,
        Tickets.priority,
        Tickets.created_at,
        Tickets.due_at
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        tickets=[dict(row._mapping) for row in result.all()]

    return tickets


def get_ticket_stats(
    assigned_to:int=None,
    created_by:int=None,
    status:str=None,
    priority:str=None,
    category:str=None,
    created_from:datetime=None,
    created_to:datetime=None
):
    conditions=[]

    if assigned_to is not None:
        employee_id_exists(assigned_to)
        conditions.append(Tickets.assigned_to==assigned_to)

    if created_by is not None:
        employee_id_exists(created_by)
        conditions.append(Tickets.created_by==created_by)

    if created_from is not None:
        conditions.append(Tickets.created_at>=created_from)

    if created_to is not None:
        conditions.append(Tickets.created_at<=created_to)
        
    if status is not None:
        if status.lower() not in ticket_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(ticket_statuses)}")
        conditions.append(Tickets.status==status.lower())

    if priority is not None:
        if priority.lower() not in ticket_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(ticket_priorities)}")
        conditions.append(Tickets.priority==priority.lower())

    if category is not None:
        if category.lower() not in ticket_categories:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(ticket_categories)}")
        conditions.append(Tickets.category==category.lower())


    stmt=select(
        func.count(Tickets.ticket_id).label("Total Tickets")
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        stats=[dict(row._mapping) for row in result.all()]

    return stats


def create_ticket(
    created_by:int,
    title:str,
    description:str,
    category:str,
    status:str="open",
    priority:str="medium",
    assigned_to:int=None,
    due_at:datetime=None
):
    
    if created_by<=0:
        raise ValueError("created_by must be a positive integer")
    if assigned_to is not None and assigned_to<=0:
        raise ValueError("assigned_to must be a positive integer if provided")
    employee_id_exists(created_by)
    employee_id_exists(assigned_to) if assigned_to is not None else None
    if category is not None and category not in ticket_categories:
        raise ValueError(f"Invalid category. Must be one of: {', '.join(ticket_categories)}")
    if status is not None and status not in ticket_statuses:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(ticket_statuses)}")
    if priority is not None and priority not in ticket_priorities:
        raise ValueError(f"Invalid priority. Must be one of: {', '.join(ticket_priorities)}")
    if due_at is not None:
            if due_at <  datetime.utcnow():
                raise ValueError(
                    "due_at cannot be earlier than the ticket creation time")
    stmt=insert(Tickets).values(
        created_by=created_by,
        assigned_to=assigned_to,
        title=title,
        description=description,
        category=category.lower(),
        status=status.lower(),
        priority=priority.lower(),
        due_at=due_at
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()
        ticket_id=result.inserted_primary_key[0]

    return f"Ticket with id: {ticket_id} has been deleted successfully!"

def ticket_id_exists(ticket_id:int):
    stmt=select(Tickets.ticket_id).where(Tickets.ticket_id==ticket_id)
    with SessionLocal() as session:
        result=session.execute(stmt)
        ticket=result.one_or_none()
    if ticket is None:
        raise LookupError(f"Ticket with ID {ticket_id} does not exist.")


def update_ticket(
    id: int,
    title: str = None,
    description: str = None,
    category: str = None,
    status: str = None,
    priority: str = None,
    assigned_to: int = None,
    due_at: datetime = None,
):
    ticket_id_exists(ticket_id=id)

    stmt = select(
        Tickets.status,
        Tickets.created_at,
        Tickets.resolved_at,
        Tickets.closed_at,
        Tickets.due_at
    ).where(
        Tickets.ticket_id == id
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        current_ticket = result.one()

    current_status = current_ticket.status
    current_created_at = current_ticket.created_at
    current_resolved_at = current_ticket.resolved_at
    current_closed_at = current_ticket.closed_at

    if assigned_to is not None:
        if assigned_to <= 0:
            raise ValueError("The employee id to whom the ticket is assigned_to must be a positive integer if provided")

        employee_id_exists(assigned_to)

    if category is not None and category not in ticket_categories:
        raise ValueError(
            f"Invalid category. Must be one of: {', '.join(ticket_categories)}")

    if status is not None and status not in ticket_statuses:
        raise ValueError(
            f"Invalid status. Must be one of: {', '.join(ticket_statuses)}")

    if priority is not None and priority not in ticket_priorities:
        raise ValueError(
            f"Invalid priority. Must be one of: {', '.join(ticket_priorities)}")


    final_status = status if status is not None else current_status


    allowed_transitions = {
        "open": ["open", "in_progress", "pending"],
        "in_progress": ["in_progress", "pending", "resolved"],
        "pending": ["pending", "in_progress"],
        "resolved": ["resolved", "closed", "in_progress"],
        "closed": ["closed"],
    }

    if status is not None:
        if final_status not in allowed_transitions[current_status]:
            raise ValueError(
                f"Invalid status transition: "
                f"{current_status} -> {final_status}"
            )


    values = {}

    if final_status == "resolved":
        if current_resolved_at is None:
            values["resolved_at"] = datetime.utcnow()

    elif final_status == "closed":
        if current_resolved_at is None:
            values["resolved_at"] = datetime.utcnow()

        if current_closed_at is None:
            values["closed_at"] = datetime.utcnow()

    elif final_status in ["open", "in_progress", "pending"]:
        values["closed_at"] = None

    elif final_status == "cancelled":
        values["resolved_at"] = None
        values["closed_at"] = None

    if final_status == "closed" and current_status not in ["resolved", "closed"]:
        raise ValueError(
        "A ticket must be resolved before it can be closed."
    )
    
    


    if due_at is not None:
        if due_at < current_created_at:
            raise ValueError(
                "due_at cannot be earlier than the ticket creation time")

        values["due_at"] = due_at

    if title is not None:
        values["title"] = title

    if description is not None:
        values["description"] = description

    if category is not None:
        values["category"] = category.lower()

    if status is not None:
        values["status"] = status.lower()

    if priority is not None:
        values["priority"] = priority.lower()

    if assigned_to is not None:
        values["assigned_to"] = assigned_to

    if not values:
        return 0

    stmt = update(Tickets).where(
        Tickets.ticket_id == id
    ).values(**values)

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()

    return f"Ticket with id: {id} has been updated successfully!"

def delete_ticket(id:int):
    stmt=delete(Tickets).where(
        Tickets.ticket_id==id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()
    if result.rowcount==0:
        raise LookupError(f"Ticket with ID {id} does not exist.")
    return f"Ticket with id: {id} has been deleted successfully!"