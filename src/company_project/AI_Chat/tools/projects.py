from datetime import datetime

from langchain.tools import tool

from ...queries.projects import (
    get_employee_projects,
    get_project,
    get_project_stats,
    search_projects,
)


@tool
def get_project_tool(project_id: int):
    """Fetch ONE project by its numeric project ID.

    Use this ONLY when the user gives a project ID (e.g. "project 12"). If the
    user gives a project name, a department, a manager, a status, or dates,
    do NOT use this tool; use ``search_projects_tool`` instead. Never guess
    an ID.

    Returns the project ID, name, description, department name, project
    manager's name, status, start date, expected end date, and creation date.
    An ID that does not exist raises a not-found error.

    Args:
        project_id: Numeric project ID (integer greater than 0).
    """
    return get_project(project_id=project_id)


@tool
def search_projects_tool(
    name: str | None = None,
    department_name: str | None = None,
    project_manager_first_name: str | None = None,
    project_manager_last_name: str | None = None,
    status: str | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
    expected_end_from: datetime | None = None,
    expected_end_to: datetime | None = None,
):
    """List or search projects by name, department, manager, status, or dates.

    This is the default tool for any project request that does not give a
    project ID, including a project mentioned by name (e.g. "the Apollo
    project"). All filters are optional and combined with AND. With NO
    arguments it returns ALL projects. Always returns a list, even for one
    match, newest start date first.

    Do NOT use this for counts like "how many projects" (use
    ``get_project_stats_tool``), or for projects a particular employee is a
    member of (use ``get_employee_projects_tool``). Filtering by manager here
    means the person who manages the project, not a team member.

    Each row contains: project ID, name, description, department name,
    project manager's name, status, start date, expected end date.

    Args:
        name: Text to find inside the project name. Case-insensitive partial
            match, so a single key word is enough, e.g. "Apollo". Must not be
            blank.
        department_name: Exact department name, e.g. "Engineering". Needs the
            name, not a department ID.
        project_manager_first_name: Manager's exact first name. Always give
            it together with ``project_manager_last_name``.
        project_manager_last_name: Manager's exact last name. Always give it
            together with ``project_manager_first_name``. If several
            employees share the full name, projects of all of them are
            returned.
        status: Must be exactly one of: "Planning", "Active", "On Hold",
            "Completed". Case is ignored, but the words must match (write
            "On Hold" with a space). Any other value causes an error.
        start_from: Only projects starting on or after this date (ISO 8601,
            e.g. "2026-01-01T00:00:00").
        start_to: Only projects starting on or before this date. Must not be
            earlier than ``start_from``.
        expected_end_from: Only projects expected to end on or after this
            date.
        expected_end_to: Only projects expected to end on or before this
            date. Must not be earlier than ``expected_end_from``.
    """
    return search_projects(
        name=name,
        department_name=department_name,
        project_manager_first_name=project_manager_first_name,
        project_manager_last_name=project_manager_last_name,
        status=status,
        start_from=start_from,
        start_to=start_to,
        expected_end_from=expected_end_from,
        expected_end_to=expected_end_to,
    )


@tool
def get_employee_projects_tool(first_name: str, last_name: str):
    """List the projects one employee works on as a team member, given their full name.

    Use for "which projects is Maria Lopez on" or "what is John Smith working
    on". Both ``first_name`` and ``last_name`` are required. If the user gave
    only one of them, do not guess the other. To find projects that a person
    MANAGES, use ``search_projects_tool`` with the manager name filters
    instead.

    Returns memberships, newest project start date first. Each row contains:
    project ID, name, description, department name, the employee's role on
    the project, the date they joined, project status, start date, expected
    end date. If several employees share the name, memberships of all of them
    are returned.

    Args:
        first_name: Employee's exact first name, e.g. "Maria". Case is
            ignored.
        last_name: Employee's exact last name, e.g. "Lopez". Case is ignored.
    """
    return get_employee_projects(first_name=first_name, last_name=last_name)


@tool
def get_project_stats_tool(
    department_name: str | None = None,
    project_manager_first_name: str | None = None,
    project_manager_last_name: str | None = None,
    status: str | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
):
    """Count projects, optionally by department, manager, status, or start date.

    Use for "how many projects", "how many active projects in Engineering", or
    "how many projects did Sara Khan manage". It returns ONE number only, NOT
    the list of projects; to see the actual projects, use
    ``search_projects_tool``. All filters are optional and combined with AND.
    With NO arguments it counts all projects.

    Returns a single total-project count.

    Args:
        department_name: Exact department name, e.g. "Engineering". Needs the
            name, not a department ID.
        project_manager_first_name: Manager's exact first name. Always give
            it together with ``project_manager_last_name``.
        project_manager_last_name: Manager's exact last name. Always give it
            together with ``project_manager_first_name``. Projects of all
            employees with that full name are counted.
        status: Must be exactly one of: "Planning", "Active", "On Hold",
            "Completed". Case is ignored, but the words must match (write
            "On Hold" with a space). Any other value causes an error.
        start_from: Only count projects starting on or after this date
            (ISO 8601, e.g. "2026-01-01T00:00:00").
        start_to: Only count projects starting on or before this date. Must
            not be earlier than ``start_from``.
    """
    return get_project_stats(
        department_name=department_name,
        project_manager_first_name=project_manager_first_name,
        project_manager_last_name=project_manager_last_name,
        status=status,
        start_from=start_from,
        start_to=start_to,
    )