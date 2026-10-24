from sqlalchemy import select, insert, update, delete
from datetime import datetime, timezone

from ..models import Project_Members, Projects, Employees
from ..database import SessionLocal


def _validate_positive_id(value: int, field_name: str):
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0.")


def _validate_role(role: str):
    if not role or not role.strip():
        raise ValueError("Role cannot be empty.")

    if len(role.strip()) > 100:
        raise ValueError("Role cannot exceed 100 characters.")

    return role.strip()


def _validate_date_range(
    joined_from: datetime = None,
    joined_to: datetime = None
):
    if (
        joined_from is not None
        and joined_to is not None
        and joined_from > joined_to
    ):
        raise ValueError("Joined date range cannot start after it ends.")


def _require_project(session, project_id: int):
    project_exists = session.execute(
        select(Projects.project_id).where(
            Projects.project_id == project_id
        )
    ).scalar_one_or_none()

    if project_exists is None:
        raise ValueError("Project does not exist.")


def _require_employee(session, employee_id: int):
    employee_exists = session.execute(
        select(Employees.employee_id).where(
            Employees.employee_id == employee_id
        )
    ).scalar_one_or_none()

    if employee_exists is None:
        raise ValueError("Employee does not exist.")


def _require_project_member(session, project_member_id: int):
    result= session.execute(
        select(Project_Members.project_member_id).where(
            Project_Members.project_member_id == project_member_id
        )
    )
    member_exists=[dict(row._mapping) for row in result.all()]

    if not member_exists:
        raise LookupError(
            f"Project member with id {project_member_id} does not exist."
        )


def get_project_member(project_member_id: int):
    _validate_positive_id(
        project_member_id,
        "Project member ID"
    )

    stmt = select(
        Project_Members.project_member_id,
        Project_Members.project_id,
        Project_Members.employee_id,
        Project_Members.role,
        Project_Members.joined_at
    ).where(
        Project_Members.project_member_id == project_member_id
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        member = [dict(row._mapping) for row in result.all()]

    if not member:
        raise LookupError("Project member does not exist.")

    return member


def get_project_members(project_id: int):
    _validate_positive_id(project_id, "Project ID")

    stmt = select(
        Project_Members.project_member_id,
        Employees.employee_id,
        Employees.first_name,
        Employees.last_name,
        Employees.job_title,
        Project_Members.role,
        Project_Members.joined_at
    ).join(
        Employees,
        Project_Members.employee_id == Employees.employee_id
    ).where(
        Project_Members.project_id == project_id
    ).order_by(
        Project_Members.joined_at.asc()
    )

    with SessionLocal() as session:
        _require_project(session, project_id)

        result = session.execute(stmt)
        members = [dict(row._mapping) for row in result.all()]

    return members


def get_employee_project_memberships(employee_id: int):
    _validate_positive_id(employee_id, "Employee ID")

    stmt = select(
        Project_Members.project_member_id,
        Projects.project_id,
        Projects.name,
        Projects.status,
        Project_Members.role,
        Project_Members.joined_at
    ).join(
        Projects,
        Project_Members.project_id == Projects.project_id
    ).where(
        Project_Members.employee_id == employee_id
    ).order_by(
        Project_Members.joined_at.desc()
    )

    with SessionLocal() as session:
        _require_employee(session, employee_id)

        result = session.execute(stmt)
        memberships = [dict(row._mapping) for row in result.all()]

    return memberships


def search_project_members(
    project_id: int = None,
    employee_id: int = None,
    role: str = None,
    joined_from: datetime = None,
    joined_to: datetime = None
):
    conditions = []

    if project_id is not None:
        _validate_positive_id(project_id, "Project ID")
        conditions.append(
            Project_Members.project_id == project_id
        )

    if employee_id is not None:
        _validate_positive_id(employee_id, "Employee ID")
        conditions.append(
            Project_Members.employee_id == employee_id
        )

    if role is not None:
        role = role.strip()

        if not role:
            raise ValueError("Role search value cannot be empty.")

        conditions.append(
            Project_Members.role.ilike(f"%{role}%")
        )

    _validate_date_range(joined_from, joined_to)

    if joined_from is not None:
        conditions.append(
            Project_Members.joined_at >= joined_from
        )

    if joined_to is not None:
        conditions.append(
            Project_Members.joined_at <= joined_to
        )

    stmt = select(
        Project_Members.project_member_id,
        Project_Members.project_id,
        Project_Members.employee_id,
        Project_Members.role,
        Project_Members.joined_at
    ).where(*conditions).order_by(
        Project_Members.joined_at.desc()
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        members = [dict(row._mapping) for row in result.all()]

    return members


def create_project_member(
    project_id: int,
    employee_id: int,
    role: str,
    joined_at: datetime = None
):
    _validate_positive_id(project_id, "Project ID")
    _validate_positive_id(employee_id, "Employee ID")

    role = _validate_role(role)

    if joined_at is not None and joined_at > datetime.now(timezone.utc):
        raise ValueError("Joined date cannot be in the future.")

    with SessionLocal() as session:

        _require_project(session, project_id)
        _require_employee(session, employee_id)

        existing_membership = session.execute(
            select(Project_Members.project_member_id).where(
                Project_Members.project_id == project_id,
                Project_Members.employee_id == employee_id
            )
        ).scalar_one_or_none()

        if existing_membership is not None:
            raise ValueError(
                "This employee is already a member of this project."
            )

        values = {
            "project_id": project_id,
            "employee_id": employee_id,
            "role": role
        }

        if joined_at is not None:
            values["joined_at"] = joined_at

        stmt = insert(Project_Members).values(**values)

        result = session.execute(stmt)
        session.commit()

        project_member_id = result.inserted_primary_key[0]

    return f"Project with project id: {project_member_id} has been created successfully!"


def update_project_member(
    id: int,
    role: str = None
):
    _validate_positive_id(id, "Project member ID")

    if role is None:
        raise ValueError("Provide a role to update.")

    role = _validate_role(role)

    stmt = update(Project_Members).where(
        Project_Members.project_member_id == id
    ).values(
        role=role
    )

    with SessionLocal() as session:
        _require_project_member(session, id)

        result = session.execute(stmt)
        session.commit()
    if result.rowcount==0:
        raise LookupError(f"Project with project id: {id} does not exist!")
    
    return f"Project with project id: {id} has been updated successfully!"


def delete_project_member(id: int):
    _validate_positive_id(id, "Project member ID")

    stmt = delete(Project_Members).where(
        Project_Members.project_member_id == id
    )

    with SessionLocal() as session:
        _require_project_member(session, id)

        result = session.execute(stmt)
        session.commit()
    if result.rowcount==0:
        raise LookupError(f"Project with project id: {id} does not exist!")

    return f"Project with project id: {id} has been deleted successfully!"

