from sqlalchemy import select,delete,update,insert

from ..models import Employees,Department
from ..database import SessionLocal

VALID_EMPLOYMENT_STATUSES={
    "active",
    "on leave",
    "resigned",
    "terminated",
    "suspended",
    "retired"
}


def get_employee(email:str=None,id:int=None):
    if id is None and email is None:
        raise ValueError(f"Provide atleast email or id to search")
    elif id is not None and email is not None:
        raise ValueError("Provide either employee ID or email, not both")
    elif id is not None:
        stmt=select(Employees.employee_id,Employees.first_name,Employees.last_name,Employees.gender,Employees.email,Employees.phone_number,Employees.date_joined,Employees.job_title,Employees.employment_status,Department.name.label("department_name"),Employees.manager_id).join(Department,Employees.department_id==Department.department_id).where(Employees.employee_id==id)
    else:
        stmt=select(Employees.employee_id,Employees.first_name,Employees.last_name,Employees.gender,Employees.email,Employees.phone_number,Employees.date_joined,Employees.job_title,Employees.employment_status,Department.name.label("department_name"),Employees.manager_id).join(Department,Employees.department_id==Department.department_id).where(Employees.email==email)

    with SessionLocal() as session:
        result=session.execute(stmt)
        result=[dict(row._mapping) for row in result.all()]

    if not result:
        raise LookupError("Employee does not exist.")
    return result


def search_employees(gender:str=None,first_name:str=None,last_name:str=None,job_title:str=None,employment_status:str=None):
    conditions=[]

    if employment_status is not None and employment_status.lower() not in VALID_EMPLOYMENT_STATUSES:
        raise ValueError("Invalid employment status")

    if gender is not None:
        conditions.append(Employees.gender.ilike(f"%{gender}"))
    if first_name is not None:
        conditions.append(Employees.first_name.ilike(f"%{first_name}%"))
    if last_name is not None:
        conditions.append(Employees.last_name.ilike(f"%{last_name}%"))
    if job_title is not None:
        conditions.append(Employees.job_title.ilike(f"%{job_title}%"))
    if employment_status is not None:
        if employment_status not in VALID_EMPLOYMENT_STATUSES:
            ValueError("{employment_status} is not a valid employment status. Choose one from {(" ").join(VALID_EMPLOYMENT_STATUSES).}")
        conditions.append(Employees.employment_status==employment_status.lower())

    stmt=select(Employees.employee_id,Employees.first_name,Employees.last_name,Employees.gender,Employees.email,Employees.phone_number,Employees.date_joined,Employees.job_title,Employees.employment_status,Department.name.label("department_name"),Employees.manager_id).join(Department,Employees.department_id==Department.department_id).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        employees=[dict(row._mapping) for row in result.all()]

    return employees


def delete_employee(id:int):
    if id is None:
        raise ValueError(f"Provide Employee ID in order to delete the record")
    else:
        stmt=delete(Employees).where(Employees.employee_id==id)

        with SessionLocal() as session:
            result = session.execute(stmt)
            session.commit()

        if result.rowcount==0:
            raise LookupError(f"Employee with id {id} does not exist.")
        return f"Employee with employee id: {id} has been successfully deleted!!"


def update_employee(
    id: int,
    first_name: str = None,
    last_name: str = None,
    gender: str = None,
    email: str = None,
    phone_number: str = None,
    address: str = None,
    date_of_birth = None,
    job_title: str = None,
    department_id: int = None,
    manager_id: int = None,
    salary: float = None,
    employment_status: str = None
):
    values = {}
    with SessionLocal() as session:
        employee_exists=session.execute(
            select(Employees.employee_id).where(
                Employees.employee_id==id
            )
        ).scalar_one_or_none()

    if employee_exists is None:
        raise LookupError(f"Employee with id {id} does not exist.")

    if department_id is not None:
        with SessionLocal() as session:
            department_exists=session.execute(
                select(Department.department_id).where(
                    Department.department_id==department_id
                )
            ).scalar_one_or_none()

        if department_exists is None:
            raise ValueError("Department does not exist")

        values["department_id"] = department_id

    if manager_id is not None:
        if manager_id==id:
            raise ValueError("An employee cannot be their own manager")

        with SessionLocal() as session:
            manager_exists=session.execute(
                select(Employees.employee_id).where(
                    Employees.employee_id==manager_id
                )
            ).scalar_one_or_none()

        if manager_exists is None:
            raise ValueError("Manager does not exist")

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
        if employment_status.lower() not in VALID_EMPLOYMENT_STATUSES:
            raise ValueError("Invalid employment status")
        values["employment_status"] = employment_status

    if not values:
        raise ValueError("Provide at least one field to update.")

    stmt = update(Employees).where(
        Employees.employee_id == id
    ).values(**values)

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()

    return f"Employee with employee id:{id} has been updated successfully!"


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
    employment_status: str = "Active"
):
    if employment_status.lower() not in VALID_EMPLOYMENT_STATUSES:
        raise ValueError("Invalid employment status")

    with SessionLocal() as session:

        department_exists=session.execute(
            select(Department.department_id).where(
                Department.department_id==department_id
            )
        ).scalar_one_or_none()

        if department_exists is None:
            raise ValueError("Department does not exist")

        if manager_id is not None:
            manager_exists=session.execute(
                select(Employees.employee_id).where(
                    Employees.employee_id==manager_id
                )
            ).scalar_one_or_none()

            if manager_exists is None:
                raise ValueError("Manager does not exist")

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
        employment_status=employment_status
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()

    return f"Employee with employee id:{result.inserted_primary_key[0]} has been updated successfully!"