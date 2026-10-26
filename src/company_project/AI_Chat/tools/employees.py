from langchain.tools import tool

from ...queries.employees import get_employee, search_employees


@tool
def get_employee_tool(
    email: str | None = None,
    id: int | None = None,
):
    """Retrieve one employee by employee ID or exact email address.

    Returns a list containing the matching employee's ID, name, gender, email,
    phone number, join date, job title, employment status, department name, and
    manager ID. Provide exactly one of ``id`` or ``email``. Raises a not-found
    error when no employee matches.

    Args:
        email: Exact employee email address to look up. Do not provide this
            together with ``id``.
        id: Employee ID to look up. Do not provide this together with
            ``email``.
    """
    return get_employee(email=email, id=id)


@tool
def search_employees_tool(
    gender: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    job_title: str | None = None,
    employment_status: str | None = None,
):
    """Get one or more employees using optional demographic and job-related filters.

    Returns matching employees with their ID, name, gender, email, phone
    number, join date, job title, employment status, department name, and
    manager ID. Name and job-title filters are case-insensitive partial
    matches. The gender filter is a case-insensitive suffix match. Employment
    status is matched without regard to case and must be one of: active,
    on leave, resigned, terminated, suspended, or retired. With no filters,
    returns all employees.

    Args:
        gender: Case-insensitive suffix to match against the employee's
            gender value.
        first_name: Case-insensitive partial match for first name.
        last_name: Case-insensitive partial match for last name.
        job_title: Case-insensitive partial match for job title.
        employment_status: Employment status to match: active, on leave,
            resigned, terminated, suspended, or retired.
    """
    return search_employees(
        gender=gender,
        first_name=first_name,
        last_name=last_name,
        job_title=job_title,
        employment_status=employment_status,
    )