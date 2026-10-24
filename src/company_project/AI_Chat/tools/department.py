from datetime import datetime

from langchain.tools import tool

from ...queries.department import get_department_info, get_departments


@tool
def get_department_info_tool(
    id: int | None = None,
    name: str | None = None,
):
    """Retrieve one department by its ID or exact name.

    Returns the department's ID, name, description, creation date, and counts
    of its employees, projects, and department-specific announcements. Provide
    exactly one of ``id`` or ``name``. A missing ID raises a not-found error;
    a name with no exact match returns an empty list.

    Args:
        id: Department ID to look up. Must be greater than zero. Do not provide
            this together with ``name``.
        name: Exact department name to look up (1–100 non-whitespace
            characters). Do not provide this together with ``id``.
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
    """Search departments using optional details, budget, date, and size filters.

    Returns matching departments with their ID, name, description, budget,
    creation date, and employee, project, and announcement counts. Name
    matching is case-insensitive and partial. Numeric ranges are inclusive.
    Supply either bound independently or both; when both are supplied, the
    minimum must not exceed the maximum. With no filters, returns all
    departments.

    Args:
        name: Case-insensitive partial match for the department name. If
            provided, it must contain 1–100 non-whitespace characters.
        budget_min: Inclusive minimum department budget; must be non-negative.
        budget_max: Inclusive maximum department budget; must be
            non-negative and at least ``budget_min`` when both are provided.
        created_from: Inclusive earliest creation timestamp.
        created_to: Inclusive latest creation timestamp; must not precede
            ``created_from`` when both are provided.
        min_employees: Inclusive minimum employee count; must be non-negative.
        max_employees: Inclusive maximum employee count; must be
            non-negative and at least ``min_employees`` when both are provided.
        min_projects: Inclusive minimum project count; must be non-negative.
        max_projects: Inclusive maximum project count; must be
            non-negative and at least ``min_projects`` when both are provided.
        min_announcements: Inclusive minimum department announcement count;
            must be non-negative.
        max_announcements: Inclusive maximum department announcement count;
            must be non-negative and at least ``min_announcements`` when both
            are provided.
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