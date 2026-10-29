from sqlalchemy import select,func,update,delete,insert
from ..models import Department,Projects,Employees,Announcements
from ..database import SessionLocal
from datetime import datetime

def get_department_info(id:int=None,name:str=None):
    if id is None and name is None:
        raise ValueError(f"Provide atleast name or id of the department to get its info.")
    if id is not None and name is not None:
        raise ValueError(f"Provide only name or only id of the department not both to get its info.")
    if id is not None and id<=0:
        raise ValueError("Department ID must be greater than 0.")
    if name is not None and (not name.strip() or len(name)>100):
        raise ValueError("Department name must contain 1 to 100 characters.")
    if id is not None:
        if id is not None:
            stmt=select(Department).where(Department.department_id==id)
            with SessionLocal() as session:
                result=session.execute(stmt)
                department=result.one_or_none()
            if department is None:
                raise LookupError(f"Department with id {id} does not exist.")
        stmt=select(
                Department.department_id,
                Department.name,
                Department.description,
                Department.created_at,
                Department.budget,
                select(
                    func.count(Projects.project_id)
                ).where(
                    Projects.department_id==Department.department_id
                ).scalar_subquery().label("Number Of Projects"),
                select(
                    func.count(Employees.employee_id)
                ).where(
                    Employees.department_id==Department.department_id
                    ).scalar_subquery().label("Number Of Employees"),
                select(
                    func.count(Announcements.announcement_id)
                ).where(
                    Announcements.department_id==Department.department_id
                    ).scalar_subquery().label("Number Of Announcements")
                ).where(Department.department_id==id)
    else:
        stmt=select(Department.department_id,
                    Department.name,
                    Department.description,
                    Department.created_at,
                    Department.budget,
                    select(
                        func.count(Projects.project_id)
                    ).where(
                        Projects.department_id==Department.department_id
                    ).scalar_subquery().label("Number Of Projects"),
                    select(
                        func.count(Employees.employee_id)
                    ).where(
                        Employees.department_id==Department.department_id
                        ).scalar_subquery().label("Number Of Employees"),
                    select(
                        func.count(Announcements.announcement_id)
                    ).where(
                        Announcements.department_id==Department.department_id
                        ).scalar_subquery().label("Number Of Announcements")
                    ).where(Department.name.ilike(f"%{name}%"))
    with SessionLocal() as session:
        result=session.execute(stmt)
        department=[dict(row._mapping) for row in result.all()]
    if department is None:
        raise LookupError("Department does not exist.")
    return department


def get_departments(
    name:str=None,
    budget_min:float=None,
    budget_max:float=None,
    created_from:datetime=None,
    created_to:datetime=None,
    min_employees:int=None,
    max_employees:int=None,
    min_projects:int=None,
    max_projects:int=None,
    min_announcements:int=None,
    max_announcements:int=None
):
    if name is not None and (not name.strip() or len(name)>100):
        raise ValueError("Department name filter must contain 1 to 100 characters.")
    if budget_min is not None and budget_min<0:
        raise ValueError("Minimum budget cannot be negative.")
    if budget_max is not None and budget_max<0:
        raise ValueError("Maximum budget cannot be negative.")
    if budget_min is not None and budget_max is not None and budget_min>budget_max:
        raise ValueError("Minimum budget cannot be greater than maximum budget.")
    if created_from is not None and created_to is not None and created_from>created_to:
        raise ValueError("Creation start date cannot be after creation end date.")
    if min_employees is not None and min_employees<0:
        raise ValueError("Minimum employee count cannot be negative.")
    if max_employees is not None and max_employees<0:
        raise ValueError("Maximum employee count cannot be negative.")
    if min_employees is not None and max_employees is not None and min_employees>max_employees:
        raise ValueError("Minimum employee count cannot be greater than maximum employee count.")
    if min_projects is not None and min_projects<0:
        raise ValueError("Minimum project count cannot be negative.")
    if max_projects is not None and max_projects<0:
        raise ValueError("Maximum project count cannot be negative.")
    if min_projects is not None and max_projects is not None and min_projects>max_projects:
        raise ValueError("Minimum project count cannot be greater than maximum project count.")
    if min_announcements is not None and min_announcements<0:
        raise ValueError("Minimum announcement count cannot be negative.")
    if max_announcements is not None and max_announcements<0:
        raise ValueError("Maximum announcement count cannot be negative.")
    if min_announcements is not None and max_announcements is not None and min_announcements>max_announcements:
        raise ValueError("Minimum announcement count cannot be greater than maximum announcement count.")

    employee_count=select(
        func.count(Employees.employee_id)
    ).where(
        Employees.department_id==Department.department_id
    ).scalar_subquery()

    project_count=select(
        func.count(Projects.project_id)
    ).where(
        Projects.department_id==Department.department_id
    ).scalar_subquery()

    announcement_count=select(
        func.count(Announcements.announcement_id)
    ).where(
        Announcements.department_id==Department.department_id
    ).scalar_subquery()

    conditions=[]

    if name is not None:
        conditions.append(Department.name.ilike(f"%{name}%"))

    if budget_min is not None:
        conditions.append(Department.budget>=budget_min)

    if budget_max is not None:
        conditions.append(Department.budget<=budget_max)

    if created_from is not None:
        conditions.append(Department.created_at>=created_from)

    if created_to is not None:
        conditions.append(Department.created_at<=created_to)

    if min_employees is not None:
        conditions.append(employee_count>=min_employees)

    if max_employees is not None:
        conditions.append(employee_count<=max_employees)

    if min_projects is not None:
        conditions.append(project_count>=min_projects)

    if max_projects is not None:
        conditions.append(project_count<=max_projects)

    if min_announcements is not None:
        conditions.append(announcement_count>=min_announcements)

    if max_announcements is not None:
        conditions.append(announcement_count<=max_announcements)

    stmt=select(
        Department.department_id,
        Department.name,
        Department.description,
        Department.budget,
        Department.created_at,
        employee_count.label("Number Of Employees"),
        project_count.label("Number Of Projects"),
        announcement_count.label("Number Of Announcements")
    ).where(*conditions)

    with SessionLocal() as session:
        result=session.execute(stmt)
        departments=[dict(row._mapping) for row in result.all()]

    return departments
    
def update_department(
    id:int,
    name:str=None,
    budget:float=None,
    description:str=None
    ):
    if id is None:
        raise ValueError(f"Provide id in order to update the department")
    if id<=0:
        raise ValueError("Department ID must be greater than 0.")
    if name is not None and (not name.strip() or len(name)>100):
        raise ValueError("Department name must contain 1 to 100 characters.")
    if budget is not None and budget<0:
        raise ValueError("Department budget cannot be negative.")
    if description is not None and not description.strip():
        raise ValueError("Department description cannot be empty.")
    if id is not None:
        stmt=select(Department).where(Department.department_id==id)
        with SessionLocal() as session:
            result=session.execute(stmt)
            department=result.one_or_none()
        if department is None:
            raise LookupError(f"Department with id {id} does not exist.")
    if name is None and budget is None and description is None:
        raise ValueError(f'Provide atleast name or budget or description to get updated')
    Values={}
    if name is not None:
        Values['name']=name
    if budget is not None:
        Values['budget']=budget
    if description is not None:
        Values['description']=description
    stmt=update(Department).where(Department.department_id==id).values(**Values)
    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()
    return f"The department with department id: {id} has been updated successfully!"

def create_department(
    name:str,
    description:str=None,
    budget:float=None
    ):
    if not isinstance(name,str) or not name.strip() or len(name)>100:
        raise ValueError("Department name must contain 1 to 100 characters.")
    if description is not None and (not isinstance(description,str) or not description.strip()):
        raise ValueError("Department description cannot be empty.")
    if budget is not None and budget<0:
        raise ValueError("Department budget cannot be negative.")
    stmt=insert(Department).values(
        name=name,
        description=description,
        budget=budget
    )
    a=0
    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()
        a=result.inserted_primary_key[0]
    return f"The department with department id: {a} has been created successfully!"

def delete_department(id:int):
    if id is None:
            raise ValueError(f"Provide department ID in order to delete the record")
    if id<=0:
            raise ValueError("Department ID must be greater than 0.")
    
    else:
        stmt=delete(Department).where(Department.department_id==id)
        with SessionLocal() as session:
            result = session.execute(stmt)
            session.commit()

        if result.rowcount==0:
            raise LookupError(f"Department with id {id} does not exist.")
        return f"The department with department id: {id} has been deleted successfully!"
    
