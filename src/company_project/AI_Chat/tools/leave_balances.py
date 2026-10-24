from langchain.tools import tool

from ...queries.leave_balances import get_leave_balance, search_leave_balances


@tool
def get_leave_balance_tool(
    employee_id: int,
    leave_type: str | None = None,
    year: int | None = None,
):
    """Retrieve an employee's leave balances, optionally narrowed by type and year.

    The employee must exist. Returns matching balance records with their
    balance ID, employee ID, leave type, total days, used days, remaining
    days, and year. Leave type matching is case-insensitive and accepts
    Annual, Sick, Casual, Unpaid, or Maternity. If ``leave_type`` or ``year``
    is omitted, balances for all corresponding types or years are returned.

    Args:
        employee_id: ID of the employee whose leave balances to retrieve.
        leave_type: Optional leave category: Annual, Sick, Casual, Unpaid, or
            Maternity. Matching ignores letter case.
        year: Optional calendar year to filter the employee's balances.
    """
    return get_leave_balance(
        employee_id=employee_id,
        leave_type=leave_type,
        year=year,
    )


@tool
def search_leave_balances_tool(
    employee_id: int | None = None,
    leave_type: str | None = None,
    year: int | None = None,
    min_remaining_days: int | None = None,
    max_remaining_days: int | None = None,
):
    """Search leave-balance records using optional employee and balance filters.

    Returns matching records with their balance ID, employee ID, leave type,
    total days, used days, remaining days, and year. Leave type matching is
    case-insensitive and accepts Annual, Sick, Casual, Unpaid, or Maternity.
    Remaining-day bounds are inclusive; when both are provided, the minimum
    cannot exceed the maximum. With no filters, returns all leave balances.
    If ``employee_id`` is provided, that employee must exist.

    Args:
        employee_id: Optional employee ID to limit results to one employee.
        leave_type: Optional leave category: Annual, Sick, Casual, Unpaid, or
            Maternity. Matching ignores letter case.
        year: Optional calendar year to filter balances.
        min_remaining_days: Inclusive minimum number of remaining leave days.
        max_remaining_days: Inclusive maximum number of remaining leave days.
    """
    return search_leave_balances(
        employee_id=employee_id,
        leave_type=leave_type,
        year=year,
        min_remaining_days=min_remaining_days,
        max_remaining_days=max_remaining_days,
    )