
from sqlalchemy import select, delete, update, insert, func, or_
from ..models import Employees, Department
from ..database import SessionLocal


VALID_EMPLOYMENT_STATUSES = {
    "active",
    "on leave",
    "resigned",
    "terminated",
    "suspended",
    "retired",
}


def validate_employment_status(employment_status: str) -> str:
    """Validate a status and return its normalized lowercase value."""
    normalized_status = employment_status.strip().lower()

    if normalized_status not in VALID_EMPLOYMENT_STATUSES:
        raise ValueError(
            f"Invalid employment status: {employment_status!r}. "
            f"Choose one of: {', '.join(sorted(VALID_EMPLOYMENT_STATUSES))}."
        )

    return normalized_status


def _normalize_filter_values(
    values: str | list[str] | None,
    filter_name: str,
) -> list[str] | None:
    if values is None:
        return None

    filter_values = [values] if isinstance(values, str) else values
    normalized_values = [value.strip() for value in filter_values if value.strip()]
    if not normalized_values:
        raise ValueError(f"Provide at least one non-empty {filter_name}.")

    return normalized_values


def get_stats(
    gender: str | list[str] = None,
    first_name: str = None,
    last_name: str = None,
    job_titles: list[str] = None,
    employment_status: str | list[str] = None,
):
    """Count employees matching the supplied filters."""
    conditions = []

    genders = _normalize_filter_values(gender, "gender")
    employment_statuses = _normalize_filter_values(
        employment_status,
        "employment status",
    )

    if genders is not None:
        conditions.append(
            or_(*[Employees.gender.ilike(value) for value in genders])
        )

    if first_name is not None:
        conditions.append(Employees.first_name.ilike(first_name.strip()))

    if last_name is not None:
        conditions.append(Employees.last_name.ilike(last_name.strip()))

    if job_titles is not None:
        if not job_titles or not any(title.strip() for title in job_titles):
            raise ValueError("Provide at least one non-empty job title.")

        conditions.append(
            or_(
                *[
                    Employees.job_title.ilike(title.strip())
                    for title in job_titles
                    if title.strip()
                ]
            )
    )

    if employment_statuses is not None:
        normalized_statuses = [
            validate_employment_status(status)
            for status in employment_statuses
        ]
        conditions.append(
            or_(
                *[
                    Employees.employment_status.ilike(status)
                    for status in normalized_statuses
                ]
            )
        )

    stmt = select(
        func.count(Employees.employee_id).label("Total Employees")
    ).where(*conditions)

    with SessionLocal() as session:
        result = session.execute(stmt)
        stats = [dict(row._mapping) for row in result.all()]

    return stats


def get_employee(email: str = None, id: int = None):
    """Retrieve one employee by email, ID, or both."""
    if email is None and id is None:
        raise ValueError("Provide at least an email address or employee ID.")

    conditions = []

    if id is not None:
        conditions.append(Employees.employee_id == id)

    if email is not None:
        conditions.append(Employees.email == email)

    stmt = (
        select(
            Employees.employee_id,
            Employees.first_name,
            Employees.last_name,
            Employees.gender,
            Employees.email,
            Employees.phone_number,
            Employees.date_joined,
            Employees.job_title,
            Employees.employment_status,
            Department.name.label("department_name"),
            Employees.manager_id,
        )
        .join(
            Department,
            Employees.department_id == Department.department_id,
        )
        .where(*conditions)
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        employees = [dict(row._mapping) for row in result.all()]

    if not employees:
        raise LookupError("Employee does not exist.")

    return employees


def search_employees(
    gender: str | list[str] = None,
    first_name: str = None,
    last_name: str = None,
    job_titles: list[str] | None = None,
    employment_status: str | list[str] = None,
):
    """Search employees using one or more optional filters."""
    conditions = []

    genders = _normalize_filter_values(gender, "gender")
    employment_statuses = _normalize_filter_values(
        employment_status,
        "employment status",
    )

    if genders is not None:
        conditions.append(
            or_(
                *[
                    Employees.gender.ilike(f"%{value}")
                    for value in genders
                ]
            )
        )

    if first_name is not None:
        conditions.append(Employees.first_name.ilike(f"%{first_name.strip()}%"))

    if last_name is not None:
        conditions.append(Employees.last_name.ilike(f"%{last_name.strip()}%"))

    if job_titles is not None:
        if not job_titles or not any(title.strip() for title in job_titles):
            raise ValueError("Provide at least one non-empty job title.")

        conditions.append(
            or_(
                *[
                    Employees.job_title.ilike(title.strip())
                    for title in job_titles
                    if title.strip()
                ]
            )
        )

    if employment_statuses is not None:
        normalized_statuses = [
            validate_employment_status(status)
            for status in employment_statuses
        ]
        conditions.append(
            or_(
                *[
                    Employees.employment_status.ilike(status)
                    for status in normalized_statuses
                ]
            )
        )

    stmt = (
        select(
            Employees.employee_id,
            Employees.first_name,
            Employees.last_name,
            Employees.gender,
            Employees.email,
            Employees.phone_number,
            Employees.date_joined,
            Employees.job_title,
            Employees.employment_status,
            Department.name.label("department_name"),
            Employees.manager_id,
        )
        .join(
            Department,
            Employees.department_id == Department.department_id,
        )
        .where(*conditions)
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        employees = [dict(row._mapping) for row in result.all()]

    return employees


def delete_employee(id: int):
    """Delete an employee by ID."""
    if id is None:
        raise ValueError("Provide an employee ID to delete the record.")

    stmt = delete(Employees).where(Employees.employee_id == id)

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()
        deleted_count = result.rowcount

    if deleted_count == 0:
        raise LookupError(f"Employee with ID {id} does not exist.")

    return f"Employee with ID {id} has been successfully deleted."


def update_employee(
    id: int,
    first_name: str = None,
    last_name: str = None,
    gender: str = None,
    email: str = None,
    phone_number: str = None,
    address: str = None,
    date_of_birth=None,
    job_title: str = None,
    department_id: int = None,
    manager_id: int = None,
    salary: float = None,
    employment_status: str = None,
):
    """Update the supplied fields for an existing employee."""
    values = {}

    with SessionLocal() as session:
        employee_exists = session.execute(
            select(Employees.employee_id).where(
                Employees.employee_id == id
            )
        ).scalar_one_or_none()

    if employee_exists is None:
        raise LookupError(f"Employee with ID {id} does not exist.")

    if department_id is not None:
        with SessionLocal() as session:
            department_exists = session.execute(
                select(Department.department_id).where(
                    Department.department_id == department_id
                )
            ).scalar_one_or_none()

        if department_exists is None:
            raise ValueError("Department does not exist.")

        values["department_id"] = department_id

    if manager_id is not None:
        if manager_id == id:
            raise ValueError("An employee cannot be their own manager.")

        with SessionLocal() as session:
            manager_exists = session.execute(
                select(Employees.employee_id).where(
                    Employees.employee_id == manager_id
                )
            ).scalar_one_or_none()

        if manager_exists is None:
            raise ValueError("Manager does not exist.")

        values["manager_id"] = manager_id

    if first_name is not None:
        values["first_name"] = first_name

    if last_name is not None:
        values["last_name"] = last_name

    if gender is not None:
        values["gender"] = gender

    if email is not None:
        values["email"] = email

    if phone_number is not None:
        values["phone_number"] = phone_number

    if address is not None:
        values["address"] = address

    if date_of_birth is not None:
        values["date_of_birth"] = date_of_birth

    if job_title is not None:
        values["job_title"] = job_title

    if salary is not None:
        values["salary"] = salary

    if employment_status is not None:
        values["employment_status"] = validate_employment_status(
            employment_status
        )

    if not values:
        raise ValueError("Provide at least one field to update.")

    stmt = (
        update(Employees)
        .where(Employees.employee_id == id)
        .values(**values)
    )

    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()

    return f"Employee with ID {id} has been updated successfully."


def create_employee(
    first_name: str,
    last_name: str,
    gender: str,
    email: str,
    phone_number: str,
    address: str,
    date_of_birth,
    date_joined,
    job_title: str,
    department_id: int,
    manager_id: int = None,
    salary: float = None,
    employment_status: str = "Active",
):
    """Create an employee after validating related records."""
    employment_status = validate_employment_status(employment_status)

    with SessionLocal() as session:
        department_exists = session.execute(
            select(Department.department_id).where(
                Department.department_id == department_id
            )
        ).scalar_one_or_none()

        if department_exists is None:
            raise ValueError("Department does not exist.")

        if manager_id is not None:
            manager_exists = session.execute(
                select(Employees.employee_id).where(
                    Employees.employee_id == manager_id
                )
            ).scalar_one_or_none()

            if manager_exists is None:
                raise ValueError("Manager does not exist.")

        stmt = insert(Employees).values(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            email=email,
            phone_number=phone_number,
            address=address,
            date_of_birth=date_of_birth,
            date_joined=date_joined,
            job_title=job_title,
            department_id=department_id,
            manager_id=manager_id,
            salary=salary,
            employment_status=employment_status,
        )

        result = session.execute(stmt)
        session.commit()
        employee_id = result.inserted_primary_key[0]

    return f"Employee with ID {employee_id} has been created successfully."
