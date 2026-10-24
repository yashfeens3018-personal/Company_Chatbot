from sqlalchemy import select,update,delete,insert
from datetime import datetime

from ..models import Employees,Leave_Requests
from ..database import SessionLocal

VALID_LEAVE_TYPES={
    "Annual",
    "Sick",
    "Casual",
    "Unpaid",
    "Maternity"
}

VALID_LEAVE_STATUSES={
    "Pending",
    "Approved",
    "Rejected"
}


def _normalize_allowed_value(value:str,allowed_values:set[str],field_name:str):
    normalized_values={
        allowed_value.casefold():allowed_value
        for allowed_value in allowed_values
    }
    normalized_value=value.strip().casefold()

    if normalized_value not in normalized_values:
        allowed=", ".join(sorted(allowed_values))
        raise ValueError(f"Invalid {field_name}. Allowed values: {allowed}.")

    return normalized_values[normalized_value]


def _validate_date_range(start_date:datetime,end_date:datetime):
    if start_date>=end_date:
        raise ValueError("Start date must be before end date.")


def _require_employee(session,employee_id:int,role:str="Employee"):
    employee_exists=session.execute(
        select(Employees.employee_id).where(
            Employees.employee_id==employee_id
        )
    ).scalar_one_or_none()

    if employee_exists is None:
        raise ValueError(f"{role} does not exist.")


def get_leave_request(leave_request_id:int):
    stmt=select(
        Leave_Requests.leave_request_id,
        Leave_Requests.employee_id,
        Leave_Requests.leave_type,
        Leave_Requests.start_date,
        Leave_Requests.end_date,
        Leave_Requests.reason,
        Leave_Requests.status,
        Leave_Requests.approved_by,
        Leave_Requests.created_at,
        Leave_Requests.updated_at
    ).where(
        Leave_Requests.leave_request_id==leave_request_id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        leave_request=[dict(row._mapping) for row in result.all()]

    if not leave_request:
        raise LookupError("Leave request does not exist.")

    return leave_request


def search_leave_requests(
    employee_id:int=None,
    approved_by:int=None,
    leave_type:str=None,
    status:str=None,
    start_from:datetime=None,
    start_to:datetime=None,
    end_from:datetime=None,
    end_to:datetime=None,
    created_from:datetime=None,
    created_to:datetime=None
):
    conditions=[]

    if leave_type is not None:
        leave_type=_normalize_allowed_value(
            leave_type,
            VALID_LEAVE_TYPES,
            "leave type"
        )

    if status is not None:
        status=_normalize_allowed_value(
            status,
            VALID_LEAVE_STATUSES,
            "leave status"
        )

    for start_date,end_date,label in [
        (start_from,start_to,"start date"),
        (end_from,end_to,"end date"),
        (created_from,created_to,"created date")
    ]:
        if start_date is not None and end_date is not None and start_date>end_date:
            raise ValueError(f"Start of {label} range cannot be after its end.")

    if employee_id is not None:
        with SessionLocal() as session:
            _require_employee(session=session,employee_id=employee_id)
        conditions.append(Leave_Requests.employee_id==employee_id)

    if approved_by is not None:
        with SessionLocal() as session:
            _require_employee(session=session,employee_id=approved_by)
        conditions.append(Leave_Requests.approved_by==approved_by)

    if leave_type is not None:
        conditions.append(Leave_Requests.leave_type==leave_type)

    if status is not None:
        conditions.append(Leave_Requests.status==status)

    if start_from is not None:
        conditions.append(Leave_Requests.start_date>=start_from)

    if start_to is not None:
        conditions.append(Leave_Requests.start_date<=start_to)

    if end_from is not None:
        conditions.append(Leave_Requests.end_date>=end_from)

    if end_to is not None:
        conditions.append(Leave_Requests.end_date<=end_to)

    if created_from is not None:
        conditions.append(Leave_Requests.created_at>=created_from)

    if created_to is not None:
        conditions.append(Leave_Requests.created_at<=created_to)

    stmt=select(
        Leave_Requests.leave_request_id,
        Leave_Requests.employee_id,
        Leave_Requests.leave_type,
        Leave_Requests.start_date,
        Leave_Requests.end_date,
        Leave_Requests.reason,
        Leave_Requests.status,
        Leave_Requests.approved_by,
        Leave_Requests.created_at,
        Leave_Requests.updated_at
    ).where(*conditions).order_by(
        Leave_Requests.start_date.asc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        leave_requests=[dict(row._mapping) for row in result.all()]

    return leave_requests



def get_current_leaves(
    employee_id:int=None,
    leave_type:str=None
):
    if leave_type is not None:
        leave_type=_normalize_allowed_value(
            leave_type,
            VALID_LEAVE_TYPES,
            "leave type"
        )

    if employee_id is not None:
        with SessionLocal() as session:
            _require_employee(session,employee_id)

    current_date=datetime.utcnow()

    conditions=[
        Leave_Requests.start_date<=current_date,
        Leave_Requests.end_date>=current_date,
        Leave_Requests.status=="Approved"
    ]

    if employee_id is not None:
        conditions.append(Leave_Requests.employee_id==employee_id)

    if leave_type is not None:
        conditions.append(Leave_Requests.leave_type==leave_type)

    stmt=select(
        Leave_Requests.leave_request_id,
        Leave_Requests.employee_id,
        Leave_Requests.leave_type,
        Leave_Requests.start_date,
        Leave_Requests.end_date,
        Leave_Requests.reason
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        leave_requests=[dict(row._mapping) for row in result.all()]

    return leave_requests

def create_leave_request(
    employee_id:int,
    leave_type:str,
    start_date:datetime,
    end_date:datetime,
    reason:str=None,
    status:str="Pending",
    approved_by:int=None
):
    leave_type=_normalize_allowed_value(
        leave_type,
        VALID_LEAVE_TYPES,
        "leave type"
    )
    status=_normalize_allowed_value(
        status,
        VALID_LEAVE_STATUSES,
        "leave status"
    )
    _validate_date_range(start_date,end_date)

    if status in {"Approved","Rejected"} and approved_by is None:
        raise ValueError("An approver is required for approved or rejected leave requests.")

    with SessionLocal() as session:
        _require_employee(session,employee_id)

        if approved_by is not None:
            _require_employee(session,approved_by,"Approver")

    stmt=insert(Leave_Requests).values(
        employee_id=employee_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status=status,
        approved_by=approved_by
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    return f"A leave request with id: {result.inserted_primary_key[0]} has been created successfully!"


def update_leave_request(
    id:int,
    leave_type:str=None,
    start_date:datetime=None,
    end_date:datetime=None,
    reason:str=None,
    status:str=None,
    approved_by:int=None
):
    if id is None:
        raise ValueError("Provide leave request ID in order to update the request")

    if all(value is None for value in [
        leave_type,
        start_date,
        end_date,
        reason,
        status,
        approved_by
    ]):
        raise ValueError("Provide at least one field to update")

    if leave_type is not None:
        leave_type=_normalize_allowed_value(
            leave_type,
            VALID_LEAVE_TYPES,
            "leave type"
        )

    if status is not None:
        status=_normalize_allowed_value(
            status,
            VALID_LEAVE_STATUSES,
            "leave status"
        )

    with SessionLocal() as session:
        current=session.execute(
            select(
                Leave_Requests.employee_id,
                Leave_Requests.start_date,
                Leave_Requests.end_date,
                Leave_Requests.status,
                Leave_Requests.approved_by
            ).where(
                Leave_Requests.leave_request_id==id
            )
        ).one_or_none()

        if current is None:
            raise LookupError(f"Leave request with id {id} does not exist.")

        _require_employee(session,current.employee_id)

        if approved_by is not None:
            _require_employee(session,approved_by,"Approver")

    final_start_date=(
        start_date
        if start_date is not None
        else current.start_date
    )
    final_end_date=(
        end_date
        if end_date is not None
        else current.end_date
    )
    _validate_date_range(final_start_date,final_end_date)

    final_status=status if status is not None else current.status
    final_approved_by=(
        approved_by
        if approved_by is not None
        else current.approved_by
    )
    if final_status in {"Approved","Rejected"} and final_approved_by is None:
        raise ValueError("An approver is required for approved or rejected leave requests.")

    values={}

    if leave_type is not None:
        values["leave_type"]=leave_type
    if start_date is not None:
        values["start_date"]=start_date
    if end_date is not None:
        values["end_date"]=end_date
    if reason is not None:
        values["reason"]=reason
    if status is not None:
        values["status"]=status
    if approved_by is not None:
        values["approved_by"]=approved_by

    stmt=update(Leave_Requests).where(
        Leave_Requests.leave_request_id==id
    ).values(**values)

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    if result.rowcount==0:
        raise LookupError(f"Leave request with id {id} does not exist.")

    return f"Leave request with id: {id} has been updated successfully!"


def delete_leave_request(id:int):
    if id is None:
        raise ValueError("Provide leave request ID in order to delete the record")

    stmt=delete(Leave_Requests).where(
        Leave_Requests.leave_request_id==id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    if result.rowcount==0:
        raise LookupError(f"Leave request with id {id} does not exist.")

    return f"Leave request with id: {id} has been deleted successfully!"