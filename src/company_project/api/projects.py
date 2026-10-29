from fastapi import APIRouter,HTTPException,Path,Query
from pydantic import BaseModel,Field
from sqlalchemy.exc import IntegrityError

from ..queries.projects import (
    get_project,
    search_projects,
    get_employee_projects,
    get_project_stats,
    create_project,
    update_project,
    delete_project
)

from datetime import datetime

router=APIRouter()

def _call_project_query(query,*args,**kwargs):
    try:
        return query(*args,**kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409,detail="Project data conflicts with existing records.") from error


@router.get("/projects")
def get_projects_endpoint(
    name:str|None=Query(default=None,min_length=1,max_length=150),
    department_name:str|None=Query(default=None,min_length=1,max_length=100),
    project_manager_first_name:str|None=Query(default=None,min_length=1,max_length=100),
    project_manager_last_name:str|None=Query(default=None,min_length=1,max_length=100),
    status:str|None=Query(default=None,min_length=1,max_length=50),
    start_from:datetime|None=None,
    start_to:datetime|None=None,
    expected_end_from:datetime|None=None,
    expected_end_to:datetime|None=None
):
    return _call_project_query(
        search_projects,
        name=name,
        department_name=department_name,
        project_manager_first_name=project_manager_first_name,
        project_manager_last_name=project_manager_last_name,
        status=status,
        start_from=start_from,
        start_to=start_to,
        expected_end_from=expected_end_from,
        expected_end_to=expected_end_to
    )


@router.get("/projects/employee/{first_name}/{last_name}")
def get_employee_projects_endpoint(first_name:str,last_name:str):
    return _call_project_query(
        get_employee_projects,
        first_name,
        last_name,
    )


@router.get("/projects/stats")
def get_project_stats_endpoint(
    department_name:str|None=Query(default=None,min_length=1,max_length=100),
    project_manager_first_name:str|None=Query(default=None,min_length=1,max_length=100),
    project_manager_last_name:str|None=Query(default=None,min_length=1,max_length=100),
    status:str|None=Query(default=None,min_length=1,max_length=50),
    start_from:datetime|None=None,
    start_to:datetime|None=None
):
    return _call_project_query(
        get_project_stats,
        department_name=department_name,
        project_manager_first_name=project_manager_first_name,
        project_manager_last_name=project_manager_last_name,
        status=status,
        start_from=start_from,
        start_to=start_to
    )


@router.get("/projects/{project_id}")
def get_project_endpoint(project_id:int=Path(...,gt=0)):
    return _call_project_query(get_project,project_id)


@router.delete("/projects/{project_id}")
def delete_project_endpoint(project_id:int=Path(...,gt=0)):
    return _call_project_query(delete_project,project_id)


class UpdateProject(BaseModel):
    id:int=Field(...,gt=0)
    name:str|None=Field(default=None,min_length=1,max_length=150)
    description:str|None=None
    department_id:int|None=Field(default=None,gt=0)
    project_manager_id:int|None=Field(default=None,gt=0)
    status:str|None=Field(default=None,min_length=1,max_length=50)
    start_date:datetime|None=None
    expected_end_date:datetime|None=None


@router.put("/projects")
def update_project_endpoint(project:UpdateProject):
    return _call_project_query(
        update_project,
        id=project.id,
        name=project.name,
        description=project.description,
        department_id=project.department_id,
        project_manager_id=project.project_manager_id,
        status=project.status,
        start_date=project.start_date,
        expected_end_date=project.expected_end_date
    )


class CreateProject(BaseModel):
    name:str=Field(...,min_length=1,max_length=150)
    description:str|None=None
    department_id:int=Field(...,gt=0)
    project_manager_id:int=Field(...,gt=0)
    status:str=Field(default="Planning",min_length=1,max_length=50)
    start_date:datetime
    expected_end_date:datetime|None=None


@router.post("/projects")
def create_project_endpoint(project:CreateProject):
    return _call_project_query(
        create_project,
        name=project.name,
        description=project.description,
        department_id=project.department_id,
        project_manager_id=project.project_manager_id,
        status=project.status,
        start_date=project.start_date,
        expected_end_date=project.expected_end_date
    )