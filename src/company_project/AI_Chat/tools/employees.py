
from langchain.tools import tool

from ...queries.employees import (
    get_employee,
    search_employees,
    get_stats,
)


@tool
def get_employee_tool(email: str):
    """Retrieve one employee using their exact email address.

    Use this tool ONLY when the employee's exact email address is already
    known from the user's message or previous verified results.

    Do NOT use this tool when the user provides only a name or employee ID.
    For a name, use search_employees_tool. For an employee ID, use
    get_employee_by_id_tool.

    Args:
        email: The exact email address identifying the employee.

    Returns:
        A one-item list containing the employee's ID, first name, last name,
        gender, email, phone number, join date, job title, employment status,
        department name, and manager ID.

        Raises LookupError if no employee matches the email.
    """
    return get_employee(email=email)


@tool
def get_employee_by_id_tool(id: int):
    """Retrieve one employee using their unique employee ID.

    Use this tool when the user explicitly provides an employee ID or when
    a previously verified database result identifies the employee by ID.

    Do NOT use this tool when the user provides only a name or email.
    For a name, use search_employees_tool. For an email, use
    get_employee_tool.

    Args:
        id: The unique integer employee ID.

    Returns:
        A one-item list containing the employee's ID, first name, last name,
        gender, email, phone number, join date, job title, employment status,
        department name, and manager ID.

        Raises LookupError if no employee matches the ID.
    """
    return get_employee(id=id)


@tool
def search_employees_tool(
    gender: list[str] | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    job_titles: list[str] | None = None,
    employment_status: list[str] | None = None,
):
    """Search for employees by their name or other available attributes.

    THIS IS THE DEFAULT TOOL FOR EMPLOYEE NAME-BASED QUERIES.

    Use this tool whenever the user identifies an employee by first name,
    last name, or full name, including requests for:
    - An employee's email address, phone number, or department.
    - An employee's job title, manager, or employment status.
    - All available information about a named employee.
    - One or more employees matching specified attributes.

    When the user provides a full name, pass the first and last names
    separately when possible. For example, "Chad Young" becomes
    first_name="Chad", last_name="Young".

    Do NOT ask the user for an email or employee ID merely because they
    supplied a name. Search using the information they provided.

    Multiple matching records may be returned. If the name is not unique,
    use the results to determine whether clarification is needed.

    You may also use this tool to list employees or filter them by gender,
    job title, or employment status. With no filters, it returns all
    employees.

    All supplied filters are combined, so every supplied filter must match.

    Matching behavior:
    - First name: case-insensitive partial match.
    - Last name: case-insensitive partial match.
    - job_titles: Case-insensitive match for any one of the supplied titles.
      This is not a partial-title search.
    - gender: A list of gender suffixes. An employee matches if their gender
      ends with ANY supplied value, ignoring case.
    - employment_status: A list of statuses. An employee matches if their
      status equals ANY supplied value, ignoring case and surrounding
      whitespace. Valid values are active, on leave, resigned, terminated,
      suspended, or retired.

    If job_titles is supplied, it must contain at least one non-empty title.
    If gender or employment_status is supplied, each list must contain at
    least one non-empty value. All filter groups are ANDed; values within each
    gender, job_titles, or employment_status list are ORed.

    Args:
        gender: Optional list of gender suffixes to match, such as
            ["male", "female"]. Any supplied value may match.
        first_name: Optional case-insensitive partial first name.
        last_name: Optional case-insensitive partial last name.
        job_titles: Optional list of case-insensitive title matches. An
            employee matches if their job title matches any listed title.
        employment_status: Optional list of accepted statuses. Any supplied
            status may match; valid values are active, on leave, resigned,
            terminated, suspended, or retired.

    Returns:
        A list of matching employee records containing employee ID,
        first name, last name, gender, email, phone number, join date,
        job title, employment status, department name, and manager ID.

        An empty list means no employees matched the supplied filters.
    """
    return search_employees(
        gender=gender,
        first_name=first_name,
        last_name=last_name,
        job_titles=job_titles,
        employment_status=employment_status,
    )


@tool
def get_employee_stats_tool(
    gender: list[str] | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    job_titles: list[str] | None = None,
    employment_status: list[str] | None = None,
):
    """Count employees matching optional filters.

    Use this tool when the user asks HOW MANY employees match a condition,
    asks for the total employee count, or asks for a count by name,
    gender, job title, or employment status.

    Do NOT use this tool when the user wants employee records or details.
    Use search_employees_tool when the user wants to find or inspect
    employees.

    All supplied filters are combined.

    Matching behavior:
    - First name, last name, and job title: case-insensitive exact matches.
    - job_titles: A list of titles; an employee is counted if their title
      matches ANY listed title.
    - gender: A list of exact gender values; an employee is counted if their
      gender matches ANY listed value, ignoring case.
    - employment_status: A list of statuses; an employee is counted if their
      status equals ANY supplied value, ignoring case and surrounding
      whitespace. Valid values are active, on leave, resigned, terminated,
      suspended, or retired.

    With no filters, this tool counts all employees.
    If job_titles is supplied, it must contain at least one non-empty title.
    If gender or employment_status is supplied, each list must contain at
    least one non-empty value. All filter groups are ANDed; values within each
    gender, job_titles, or employment_status list are ORed.

    Args:
        gender: Optional list of exact gender values, ignoring case. Any
            supplied value may match.
        first_name: Optional exact first name, ignoring case.
        last_name: Optional exact last name, ignoring case.
        job_titles: Optional list of exact title values, ignoring case. Any
            listed title can match.
        employment_status: Optional list of accepted statuses. Any supplied
            status may match; valid values are active, on leave, resigned,
            terminated, suspended, or retired.

    Returns:
        A one-item list containing a mapping with the "Total Employees"
        count.
    """
    return get_stats(
        gender=gender,
        first_name=first_name,
        last_name=last_name,
        job_titles=job_titles,
        employment_status=employment_status,
    )
