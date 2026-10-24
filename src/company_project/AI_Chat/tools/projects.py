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
    """Retrieve a project by its ID.

    Returns the project ID, name, description, department name, project
    manager's name, status, start date, expected end date, and creation date.
    Raises a not-found error if the project does not exist.

    Args:
        project_id: ID of the project to retrieve.
    """
    return get_project(project_id=project_id)


@tool
def search_projects_tool(
    name: str | None = None,
    department_id: int | None = None,
    project_manager_id: int | None = None,
    status: str | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
    expected_end_from: datetime | None = None,
    expected_end_to: datetime | None = None,
):
    """Search projects by name, department, manager, status, or date ranges.

    Returns matching projects ordered by descending start date, including
    project ID, name, description, department, manager name, status, start
    date, and expected end date. Name matching is case-insensitive and
    partial. Status must be Planning, Active, On Hold, or Completed; matching
    ignores case and surrounding whitespace. Date bounds are inclusive. For
    each date range, the lower bound cannot be later than the upper bound.
    With no filters, returns all projects.

    Args:
        name: Optional case-insensitive partial match for the project name.
            Must not be blank when provided.
        department_id: Optional department ID to filter projects.
        project_manager_id: Optional employee ID of the project manager.
        status: Optional status: Planning, Active, On Hold, or Completed.
        start_from: Inclusive earliest project start date.
        start_to: Inclusive latest project start date.
        expected_end_from: Inclusive earliest expected end date.
        expected_end_to: Inclusive latest expected end date.
    """
    return search_projects(
        name=name,
        department_id=department_id,
        project_manager_id=project_manager_id,
        status=status,
        start_from=start_from,
        start_to=start_to,
        expected_end_from=expected_end_from,
        expected_end_to=expected_end_to,
    )


@tool
def get_employee_projects_tool(employee_id: int):
    """List projects an employee belongs to as a project member.

    Returns the employee's memberships ordered by descending project start
    date, including project ID, name, description, department name, the
    employee's role, join date, status, start date, and expected end date.
    The employee must exist.

    Args:
        employee_id: ID of the employee whose project memberships to retrieve.
    """
    return get_employee_projects(employee_id=employee_id)


@tool
def get_project_stats_tool(
    department_id: int | None = None,
    project_manager_id: int | None = None,
    status: str | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
):
    """Count projects matching optional department, manager, status, and start-date filters.

    Returns a single total-project count. Status must be Planning, Active,
    On Hold, or Completed; matching ignores case and surrounding whitespace.
    Start-date bounds are inclusive, and ``start_from`` cannot be later than
    ``start_to``. With no filters, counts all projects.

    Args:
        department_id: Optional department ID to filter the count.
        project_manager_id: Optional employee ID of the project manager.
        status: Optional status: Planning, Active, On Hold, or Completed.
        start_from: Inclusive earliest project start date.
        start_to: Inclusive latest project start date.
    """
    return get_project_stats(
        department_id=department_id,
        project_manager_id=project_manager_id,
        status=status,
        start_from=start_from,
        start_to=start_to,
    )