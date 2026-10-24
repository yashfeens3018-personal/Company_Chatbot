from datetime import datetime

from langchain.tools import tool

from ...queries.project_members import (
    get_employee_project_memberships,
    get_project_member,
    get_project_members,
    search_project_members,
)


@tool
def get_project_member_tool(project_member_id: int):
    """Retrieve one project membership by its membership ID.

    Returns the membership ID, project ID, employee ID, assigned role, and
    join date. The ID must be greater than zero. Raises a not-found error if
    no membership has the requested ID.

    Args:
        project_member_id: ID of the project membership to retrieve.
    """
    return get_project_member(project_member_id=project_member_id)


@tool
def get_project_members_tool(project_id: int):
    """List the employees who belong to a project.

    Returns memberships for the project ordered by join date, with each
    employee's ID, first and last name, job title, project role, and join
    date. The project ID must be greater than zero, and the project must
    exist.

    Args:
        project_id: ID of the project whose members should be listed.
    """
    return get_project_members(project_id=project_id)


@tool
def get_employee_project_memberships_tool(employee_id: int):
    """List the projects an employee belongs to.

    Returns the employee's memberships ordered by most recent join date,
    including membership ID, project ID and name, project status, role, and
    join date. The employee ID must be greater than zero, and the employee
    must exist.

    Args:
        employee_id: ID of the employee whose project memberships to retrieve.
    """
    return get_employee_project_memberships(employee_id=employee_id)


@tool
def search_project_members_tool(
    project_id: int | None = None,
    employee_id: int | None = None,
    role: str | None = None,
    joined_from: datetime | None = None,
    joined_to: datetime | None = None,
):
    """Search project memberships using optional project, employee, role, and date filters.

    Returns matching memberships ordered by most recent join date, with
    membership ID, project ID, employee ID, role, and join date. Project and
    employee IDs, when supplied, must be greater than zero. Role matching is
    case-insensitive and partial; a supplied role cannot be blank. Join-date
    bounds are inclusive, and ``joined_from`` cannot be later than
    ``joined_to``. With no filters, returns all project memberships.

    Args:
        project_id: Optional project ID to filter memberships.
        employee_id: Optional employee ID to filter memberships.
        role: Optional case-insensitive partial match for the member's role.
        joined_from: Inclusive earliest membership join date.
        joined_to: Inclusive latest membership join date.
    """
    return search_project_members(
        project_id=project_id,
        employee_id=employee_id,
        role=role,
        joined_from=joined_from,
        joined_to=joined_to,
    )