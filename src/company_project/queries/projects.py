from sqlalchemy import select,func,update,delete,insert
from datetime import datetime
from ..models import Projects,Department,Employees,Project_Members
from ..database import SessionLocal

VALID_PROJECT_STATUSES={
    "Planning",
    "Active",
    "On Hold",
    "Completed"
}


def _normalize_project_status(status:str):
    normalized_status=status.strip().casefold()
    for allowed_status in VALID_PROJECT_STATUSES:
        if normalized_status==allowed_status.casefold():
            return allowed_status

    allowed=", ".join(sorted(VALID_PROJECT_STATUSES))
    raise ValueError(f"Invalid project status. Allowed values: {allowed}.")


def _validate_project_name(name:str):
    if not name.strip():
        raise ValueError("Project name cannot be blank.")


def _require_department(session,department_id:int):
    exists=session.execute(
        select(Department.department_id).where(
            Department.department_id==department_id
        )
    ).scalar_one_or_none()

    if exists is None:
        raise ValueError("Department does not exist.")


def _require_employee(session,employee_id:int,role:str):
    exists=session.execute(
        select(Employees.employee_id).where(
            Employees.employee_id==employee_id
        )
    ).scalar_one_or_none()

    if exists is None:
        raise ValueError(f"{role} does not exist.")


def _find_employee_ids(session,first_name:str,last_name:str):
    if not first_name.strip() or not last_name.strip():
        raise ValueError("Provide both the employee's first and last name.")

    return session.execute(
        select(Employees.employee_id).where(
            Employees.first_name.ilike(first_name.strip()),
            Employees.last_name.ilike(last_name.strip()),
        )
    ).scalars().all()


def _validate_date_range(start_date:datetime,end_date:datetime|None):
    if end_date is not None and start_date>=end_date:
        raise ValueError("Expected end date must be after the start date.")


def get_project(project_id:int):
    stmt=select(
        Projects.project_id,
        Projects.name,
        Projects.description,
        Department.name.label("department_name"),
        Employees.first_name.label("manager_first_name"),
        Employees.last_name.label("manager_last_name"),
        Projects.status,
        Projects.start_date,
        Projects.expected_end_date,
        Projects.created_at
    ).join(
        Department,
        Projects.department_id==Department.department_id
    ).join(
        Employees,
        Projects.project_manager_id==Employees.employee_id
    ).where(
        Projects.project_id==project_id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        project=[dict(row._mapping) for row in result.all()]

    if not project:
        raise LookupError(f"Project with id {project_id} does not exist.")

    return project


def search_projects(
    name:str=None,
    department_name:str=None,
    project_manager_first_name:str=None,
    project_manager_last_name:str=None,
    status:str=None,
    start_from:datetime=None,
    start_to:datetime=None,
    expected_end_from:datetime=None,
    expected_end_to:datetime=None
):
    conditions=[]

    if status is not None:
        status=_normalize_project_status(status)

    for start_date,end_date,label in [
        (start_from,start_to,"start date"),
        (expected_end_from,expected_end_to,"expected end date")
    ]:
        if start_date is not None and end_date is not None and start_date>end_date:
            raise ValueError(f"Start of {label} range cannot be after its end.")

    if name is not None:
        _validate_project_name(name)
        conditions.append(Projects.name.ilike(f"%{name}%"))
    if department_name is not None:
        with SessionLocal() as session:
            department_id=session.execute(
                select(Department.department_id).where(
                    Department.name.ilike(department_name.strip())
                )
            ).scalar_one_or_none()
        if department_id is None:
            conditions.append(Projects.department_id.in_([]))
        else:
            conditions.append(Projects.department_id==department_id)

    if (project_manager_first_name is None) != (project_manager_last_name is None):
        raise ValueError(
            "Provide both the project manager's first and last name."
        )
    if project_manager_first_name is not None:
        with SessionLocal() as session:
            employee_ids=_find_employee_ids(
                session,
                project_manager_first_name,
                project_manager_last_name,
            )
        conditions.append(Projects.project_manager_id.in_(employee_ids))
    if status is not None:
        conditions.append(Projects.status==status)
    if start_from is not None:
        conditions.append(Projects.start_date>=start_from)
    if start_to is not None:
        conditions.append(Projects.start_date<=start_to)
    if expected_end_from is not None:
        conditions.append(Projects.expected_end_date>=expected_end_from)
    if expected_end_to is not None:
        conditions.append(Projects.expected_end_date<=expected_end_to)

    stmt=select(
        Projects.project_id,
        Projects.name,
        Projects.description,
        Department.name.label("department_name"),
        Employees.first_name.label("manager_first_name"),
        Employees.last_name.label("manager_last_name"),
        Projects.status,
        Projects.start_date,
        Projects.expected_end_date
    ).join(
        Department,
        Projects.department_id==Department.department_id
    ).join(
        Employees,
        Projects.project_manager_id==Employees.employee_id
    ).where(*conditions).order_by(
        Projects.start_date.desc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        projects=[dict(row._mapping) for row in result.all()]

    return projects


def get_employee_projects(first_name:str,last_name:str):
    with SessionLocal() as session:
        employee_ids=_find_employee_ids(session,first_name,last_name)

    if not employee_ids:
        raise ValueError(f"Employee {first_name} {last_name} does not exist.")

    stmt=select(
        Projects.project_id,
        Projects.name,
        Projects.description,
        Department.name.label("department_name"),
        Project_Members.role,
        Project_Members.joined_at,
        Projects.status,
        Projects.start_date,
        Projects.expected_end_date
    ).join(
        Project_Members,
        Projects.project_id==Project_Members.project_id
    ).join(
        Department,
        Projects.department_id==Department.department_id
    ).where(
        Project_Members.employee_id.in_(employee_ids)
    ).order_by(
        Projects.start_date.desc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        projects=result.all()

    return projects


def get_project_stats(
    department_name:str=None,
    project_manager_first_name:str=None,
    project_manager_last_name:str=None,
    status:str=None,
    start_from:datetime=None,
    start_to:datetime=None
):
    conditions=[]

    if status is not None:
        status=_normalize_project_status(status)

    if start_from is not None and start_to is not None and start_from>start_to:
        raise ValueError("Start of start date range cannot be after its end.")

    if department_name is not None:
        with SessionLocal() as session:
            department_id=session.execute(
                select(Department.department_id).where(
                    Department.name.ilike(department_name.strip())
                )
            ).scalar_one_or_none()
        if department_id is None:
            conditions.append(Projects.department_id.in_([]))
        else:
            conditions.append(Projects.department_id==department_id)

    if (project_manager_first_name is None) != (project_manager_last_name is None):
        raise ValueError(
            "Provide both the project manager's first and last name."
        )
    if project_manager_first_name is not None:
        with SessionLocal() as session:
            employee_ids=_find_employee_ids(
                session,
                project_manager_first_name,
                project_manager_last_name,
            )
        conditions.append(Projects.project_manager_id.in_(employee_ids))
    if status is not None:
        conditions.append(Projects.status==status)
    if start_from is not None:
        conditions.append(Projects.start_date>=start_from)
    if start_to is not None:
        conditions.append(Projects.start_date<=start_to)

    stmt=select(
        func.count(Projects.project_id).label("Total Projects")
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        stats=[dict(row._mapping) for row in result.all()]

    return stats


def create_project(
    name:str,
    description:str=None,
    department_id:int=None,
    project_manager_id:int=None,
    status:str="Planning",
    start_date:datetime=None,
    expected_end_date:datetime=None
):
    _validate_project_name(name)
    status=_normalize_project_status(status)
    if start_date is None:
        raise ValueError("Project start date is required.")
    _validate_date_range(start_date,expected_end_date)

    with SessionLocal() as session:
        _require_department(session,department_id)
        _require_employee(session,project_manager_id,"Project manager")

    stmt=insert(Projects).values(
        name=name,
        description=description,
        department_id=department_id,
        project_manager_id=project_manager_id,
        status=status,
        start_date=start_date,
        expected_end_date=expected_end_date
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    return f"The project with id: {result.inserted_primary_key[0]} has been created successfully!"


def update_project(
    id:int,
    name:str=None,
    description:str=None,
    department_id:int=None,
    project_manager_id:int=None,
    status:str=None,
    start_date:datetime=None,
    expected_end_date:datetime=None
):
    if id is None:
        raise ValueError("Provide project ID in order to update the project")

    if all(value is None for value in [
        name,
        description,
        department_id,
        project_manager_id,
        status,
        start_date,
        expected_end_date
    ]):
        raise ValueError("Provide at least one field to update")

    if name is not None:
        _validate_project_name(name)

    if status is not None:
        status=_normalize_project_status(status)

    with SessionLocal() as session:
        current=session.execute(
            select(
                Projects.start_date,
                Projects.expected_end_date
            ).where(
                Projects.project_id==id
            )
        ).one_or_none()

        if current is None:
            raise LookupError(f"Project with id {id} does not exist.")

        if department_id is not None:
            _require_department(session,department_id)

        if project_manager_id is not None:
            _require_employee(session,project_manager_id,"Project manager")

    final_start_date=(
        start_date
        if start_date is not None
        else current.start_date
    )
    final_expected_end_date=(
        expected_end_date
        if expected_end_date is not None
        else current.expected_end_date
    )
    _validate_date_range(final_start_date,final_expected_end_date)

    values={}

    if name is not None:
        values["name"]=name
    if description is not None:
        values["description"]=description
    if department_id is not None:
        values["department_id"]=department_id
    if project_manager_id is not None:
        values["project_manager_id"]=project_manager_id
    if status is not None:
        values["status"]=status
    if start_date is not None:
        values["start_date"]=start_date
    if expected_end_date is not None:
        values["expected_end_date"]=expected_end_date

    stmt=update(Projects).where(
        Projects.project_id==id
    ).values(**values)

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    if result.rowcount==0:
        raise LookupError(f"Project with id {id} does not exist.")

    return f"The project with id: {id} has been updated successfully!"


def delete_project(id:int):
    if id is None:
        raise ValueError("Provide project ID in order to delete the record")

    stmt=delete(Projects).where(
        Projects.project_id==id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    if result.rowcount==0:
        raise LookupError(f"Project with id {id} does not exist.")

    return f"The project with id: {id} has been deleted successfully!"