from fastapi import APIRouter,HTTPException,Path,Query
from ..queries.employees import get_employee, search_employees, delete_employee, update_employee, create_employee 
from pydantic import BaseModel,Field,EmailStr, ConfigDict
from datetime import datetime
from sqlalchemy.exc import IntegrityError

router=APIRouter()

def _call_employee_query(query,*args,**kwargs):
    try:
        return query(*args,**kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409,detail="Employee data conflicts with existing records.") from error

@router.get("/employees/{employee_id}")
def get_employee_endpoint(employee_id:int=Path(...,gt=0)):
    return _call_employee_query(get_employee,id=employee_id)

@router.delete("/employees/{employee_id}")
def delete_employee_endpoint(employee_id:int=Path(...,gt=0)):
    return _call_employee_query(delete_employee,id=employee_id)

@router.get("/employees")
def get_employees_endpoint(
    gender:str=Query(default=None,min_length=1,max_length=20),
    first_name:str=Query(default=None,min_length=1,max_length=100),
    last_name:str=Query(default=None,min_length=1,max_length=100),
    job_title:str=Query(default=None,min_length=1,max_length=100),
    employment_status:str=Query(default=None,min_length=1,max_length=30)
):
    return _call_employee_query(
        search_employees,
        gender=gender,
        first_name=first_name,
        last_name=last_name,
        job_title=job_title,
        employment_status=employment_status
    )


class UpdateEmployee(BaseModel):
    id: int = Field(
        ...,
        gt=0,
        description="ID of the employee whose record is being updated"
    )
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    gender: str | None = Field(
        default=None,
        min_length=1,
        max_length=20
    )
    email: EmailStr | None = Field(default=None,max_length=100)
    phone_number: str | None = Field(
        default=None,
        min_length=7,
        max_length=30
    )
    address: str | None = Field(
        default=None,
        min_length=1,
        max_length=255
    )
    date_of_birth: datetime | None = None
    job_title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    department_id: int | None = Field(
        default=None,
        gt=0
    )
    manager_id: int | None = Field(
        default=None,
        gt=0
    )
    salary: float | None = Field(
        default=None,
        ge=0
    )
    employment_status: str | None = Field(
        default=None,
        min_length=1,
        max_length=30
    )

@router.put("/employees")
def update_employee_endpoint(up_emp: UpdateEmployee):
    return _call_employee_query(
        update_employee,
        id=up_emp.id,
        first_name=up_emp.first_name,
        last_name=up_emp.last_name,
        gender=up_emp.gender,
        email=up_emp.email,
        phone_number=up_emp.phone_number,
        address=up_emp.address,
        date_of_birth=up_emp.date_of_birth,
        job_title=up_emp.job_title,
        department_id=up_emp.department_id,
        manager_id=up_emp.manager_id,
        salary=up_emp.salary,
        employment_status=up_emp.employment_status
    )
    
    
class CreateEmployee(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(..., min_length=1, max_length=20)
    email: EmailStr = Field(...,max_length=100)
    phone_number: str = Field(..., min_length=7, max_length=30)
    address: str = Field(..., min_length=1, max_length=255)
    date_of_birth: datetime | None = None
    date_joined: datetime
    job_title: str = Field(..., min_length=1, max_length=100)
    department_id: int = Field(..., gt=0)
    manager_id: int | None = Field(default=None, gt=0)
    salary: float | None = Field(default=None, ge=0)
    employment_status: str = Field(
        default="Active",
        min_length=1,
        max_length=30
    )
    
@router.post("/employees")
def create_employee_endpoint(employee: CreateEmployee):
    return _call_employee_query(
        create_employee,
        first_name=employee.first_name,
        last_name=employee.last_name,
        gender=employee.gender,
        email=employee.email,
        phone_number=employee.phone_number,
        address=employee.address,
        date_of_birth=employee.date_of_birth,
        date_joined=employee.date_joined,
        job_title=employee.job_title,
        department_id=employee.department_id,
        manager_id=employee.manager_id,
        salary=employee.salary,
        employment_status=employee.employment_status
    )