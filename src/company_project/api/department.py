from datetime import datetime
from fastapi import APIRouter,HTTPException
from ..queries.department import get_department_info, get_departments,delete_department,update_department,create_department
from pydantic import BaseModel,Field
from sqlalchemy.exc import IntegrityError

router=APIRouter()

def _call_department_query(query,*args,**kwargs):
    try:
        return query(*args,**kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409,detail="A department with that name already exists.") from error

@router.get("/departments/{department_id}")
def get_department_endpoint(department_id:int):
    return _call_department_query(get_department_info,id=department_id)

@router.get("/departments")
def get_departments_endpoint(
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
    return _call_department_query(
        get_departments,
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
        max_announcements=max_announcements
    )

@router.delete("/departments/{department_id}")
def delete_department_endpoint(department_id:int):
    return _call_department_query(delete_department,id=department_id)

class UpdateDepartment(BaseModel):
    id:int=Field(...,description="The id of the department whose record is to be updated",gt=0)
    name:str|None=Field(default=None,min_length=1,max_length=100)
    description:str|None=Field(default=None,min_length=1)
    budget:float|None=Field(default=None, ge=0)
    
@router.put("/departments")
def update_department_endpoint(UpDep:UpdateDepartment):
    return _call_department_query(
        update_department,
        id=UpDep.id,
        name=UpDep.name,
        budget=UpDep.budget,
        description=UpDep.description)

class CreateDepartment(BaseModel):
    name:str=Field(...,min_length=1,max_length=100)
    description:str|None=Field(default=None,min_length=1)
    budget:float|None=Field(default=None,ge=0)

@router.post("/departments")
def create_department_endpoint(department:CreateDepartment):
    return _call_department_query(
        create_department,
        name=department.name,
        description=department.description,
        budget=department.budget
    )