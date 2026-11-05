from datetime import datetime

from langchain.tools import tool

from ...queries.leave_requests import (
    get_employee_leave_requests,
    get_leave_request,
    search_leave_requests,
)


@tool
def get_leave_request_tool(leave_request_id: int):
    """Retrieve a leave request by its ID.

    Returns a list containing the request ID, employee ID, leave type,
    start and end dates, reason, status, approver ID, and creation/update
    timestamps. Raises a not-found error if no request has this ID.

    Args:
        leave_request_id: ID of the leave request to retrieve.
    """
    return get_leave_request(leave_request_id=leave_request_id)


@tool
def search_leave_requests_tool(
    employee_id: int | None = None,
    approved_by: int | None = None,
    leave_type: str | None = None,
    status: str | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
    end_from: datetime | None = None,
    end_to: datetime | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    """Search leave requests using employee, status, type, and date filters.

    Returns matching requests ordered by start date, including request and
    employee IDs, leave type, start/end dates, reason, status, approver ID,
    and creation/update timestamps. Leave types are Annual, Sick, Casual,
    Unpaid, or Maternity; statuses are Pending, Approved, or Rejected.
    Matching for these values is case-insensitive. Date bounds are inclusive.
    For each date field (request start, request end, and request creation),
    the lower bound cannot be later than the upper bound. If an employee or
    approver ID is supplied, that employee must exist. With no filters, all
    requests are returned.

    Args:
        employee_id: Optional ID of the employee who submitted the request.
        approved_by: Optional ID of the employee who approved or rejected it.
        leave_type: Optional leave category: Annual, Sick, Casual, Unpaid, or
            Maternity. Matching ignores letter case.
        status: Optional request status: Pending, Approved, or Rejected.
            Matching ignores letter case.
        start_from: Inclusive earliest request start date.
        start_to: Inclusive latest request start date.
        end_from: Inclusive earliest request end date.
        end_to: Inclusive latest request end date.
        created_from: Inclusive earliest request creation timestamp.
        created_to: Inclusive latest request creation timestamp.
    """
    return search_leave_requests(
        employee_id=employee_id,
        approved_by=approved_by,
        leave_type=leave_type,
        status=status,
        start_from=start_from,
        start_to=start_to,
        end_from=end_from,
        end_to=end_to,
        created_from=created_from,
        created_to=created_to,
    )


@tool
def get_employment_tool(employee_id: int):
    """List all leave requests submitted by the employee with this ID.

    Includes requests of every leave type and status, ordered by start date.
    Returns request ID, employee ID, leave type, dates, reason, status,
    approver ID, and creation/update timestamps. Raises an error if the
    employee ID does not exist.

    Args:
        employee_id: Positive integer ID of the employee who submitted the
            requests.
    """
    return get_employee_leave_requests(employee_id)