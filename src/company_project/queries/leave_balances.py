from sqlalchemy import select

from ..models import Employees,Leave_Balances
from ..database import SessionLocal
from .leave_requests import VALID_LEAVE_TYPES


def _normalize_leave_type(leave_type:str):
    normalized_types={
        allowed_type.casefold():allowed_type
        for allowed_type in VALID_LEAVE_TYPES
    }
    normalized_leave_type=leave_type.strip().casefold()

    if normalized_leave_type not in normalized_types:
        allowed=", ".join(sorted(VALID_LEAVE_TYPES))
        raise ValueError(f"Invalid leave type. Allowed values: {allowed}.")

    return normalized_types[normalized_leave_type]


def _require_employee(session,employee_id:int):
    employee_exists=session.execute(
        select(Employees.employee_id).where(
            Employees.employee_id==employee_id
        )
    ).scalar_one_or_none()

    if employee_exists is None:
        raise LookupError(f"Employee with id {employee_id} does not exist.")


def _validate_remaining_days_range(
    min_remaining_days:int|None,
    max_remaining_days:int|None
):
    if (
        min_remaining_days is not None and
        max_remaining_days is not None and
        min_remaining_days>max_remaining_days
    ):
        raise ValueError(
            "Minimum remaining days cannot be greater than maximum remaining days."
        )


def get_leave_balance(
    employee_id:int,
    leave_type:str=None,
    year:int=None
):
    if leave_type is not None:
        leave_type=_normalize_leave_type(leave_type)

    with SessionLocal() as session:
        _require_employee(session,employee_id)

    conditions=[
        Leave_Balances.employee_id==employee_id
    ]

    if leave_type is not None:
        conditions.append(Leave_Balances.leave_type==leave_type)

    if year is not None:
        conditions.append(Leave_Balances.year==year)

    stmt=select(
        Leave_Balances.leave_balance_id,
        Leave_Balances.employee_id,
        Leave_Balances.leave_type,
        Leave_Balances.total_days,
        Leave_Balances.used_days,
        Leave_Balances.remaining_days,
        Leave_Balances.year
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        balance=[dict(row._mapping) for row in result.all()]

    return balance


def search_leave_balances(
    employee_id:int=None,
    leave_type:str=None,
    year:int=None,
    min_remaining_days:int=None,
    max_remaining_days:int=None
):
    conditions=[]

    _validate_remaining_days_range(
        min_remaining_days,
        max_remaining_days
    )

    if leave_type is not None:
        leave_type=_normalize_leave_type(leave_type)

    if employee_id is not None:
        with SessionLocal() as session:
            _require_employee(session,employee_id)

        conditions.append(Leave_Balances.employee_id==employee_id)

    if leave_type is not None:
        conditions.append(Leave_Balances.leave_type==leave_type)

    if year is not None:
        conditions.append(Leave_Balances.year==year)

    if min_remaining_days is not None:
        conditions.append(
            Leave_Balances.remaining_days>=min_remaining_days
        )

    if max_remaining_days is not None:
        conditions.append(
            Leave_Balances.remaining_days<=max_remaining_days
        )

    stmt=select(
        Leave_Balances.leave_balance_id,
        Leave_Balances.employee_id,
        Leave_Balances.leave_type,
        Leave_Balances.total_days,
        Leave_Balances.used_days,
        Leave_Balances.remaining_days,
        Leave_Balances.year
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        balances=[dict(row._mapping) for row in result.all()]

    return balances