from datetime import datetime

from langchain.tools import tool

from ...queries.department import get_department_info, get_departments


@tool
def get_department_info_tool(
    id: int | None = None,
    name: str | None = None,
):
    """Get the full profile of a single department, looked up by ID or by name.

    Use this when the user asks about one specific department (e.g. "tell me
    about Finance", "info on department 3"). 
    
    Helpful in answering questions like:
    1) Number of employees in a specific department
    2) Number of projects in a specific department
    3) Number of announcements in a specific department
    4) departmemt info like id, name, description, budget, created_at
    Returns a list of matching
    rows, each with: department_id, name, description, budget, created_at,
    and counts of employees, projects, and announcements. It does NOT return
    employee names, job titles, managers, or the contents of projects or
    announcements; it only returns counts.

    Provide exactly one of ``id`` or ``name``, never both and never neither.

    Name lookup is a case-insensitive PARTIAL match, so pass the short,
    distinctive part of the name. Use "Finance", not "Finance Department" or
    "the finance dept". If several departments contain the text, all of them
    are returned. If nothing matches, an empty list is returned (this means
    no such department, not an error); in that case, call
    ``get_departments_tool`` with no filters to see the real department
    names, then retry. An ID that does not exist raises a not-found error.

    Args:
        id: Numeric department ID (integer greater than 0). Use only when the
            user gave an ID. Do not combine with ``name``.
        name: Text to search for within the department name (1-100
            characters, not blank). Case-insensitive, matches anywhere in the
            name. Prefer one key word. Do not combine with ``id``.
    """
    return get_department_info(id=id, name=name)


@tool
def get_departments_tool(
    name: str | None = None,
    budget_min: float | None = None,
    budget_max: float | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    min_employees: int | None = None,
    max_employees: int | None = None,
    min_projects: int | None = None,
    max_projects: int | None = None,
    min_announcements: int | None = None,
    max_announcements: int | None = None,
):
    """List or filter departments. Use for browsing, comparing, ranking, or discovery.

    Use this when the user wants several departments, asks "which departments
    ...", wants to filter by budget, creation date, or size, or when you need
    to discover the exact department names that exist. With no arguments it
    returns ALL departments. All filters are optional and combined with AND.

    Each result row contains: department_id, name, description, budget,
    created_at, and counts of employees, projects, and announcements. It does
    NOT return individual employees, projects, or announcements.

    Range filters are inclusive. You may give just a min, just a max, or
    both; if both, min must be <= max. All counts and budgets must be >= 0.

    Args:
        name: Case-insensitive partial match on the department name (1-100
            characters, not blank). Use a single key word, e.g. "eng" or
            "Finance".
        budget_min: Minimum budget, inclusive.
        budget_max: Maximum budget, inclusive (>= budget_min if both given).
        created_from: Only departments created on or after this timestamp
            (ISO 8601, e.g. "2024-01-31T00:00:00").
        created_to: Only departments created on or before this timestamp
            (must not be earlier than created_from).
        min_employees: Minimum number of employees, inclusive.
        max_employees: Maximum number of employees, inclusive.
        min_projects: Minimum number of projects, inclusive.
        max_projects: Maximum number of projects, inclusive.
        min_announcements: Minimum number of department announcements,
            inclusive.
        max_announcements: Maximum number of department announcements,
            inclusive.
    """
    return get_departments(
        name=name,
        budget_min=budget_min,
        budget_max=budget_max,
        created_from=created_from,
        created_to=created_to,
        min_employees=min_employees,
        max_employees=max_employees,
        min_projects=min_projects,
        max_projects=max_projects,
        min_announcements=min_announcements,
        max_announcements=max_announcements,
    )