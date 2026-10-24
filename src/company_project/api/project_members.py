from datetime import datetime

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from ..queries.project_members import (
    get_project_member,
    get_project_members,
    get_employee_project_memberships,
    search_project_members,
    create_project_member,
    update_project_member,
    delete_project_member
)

router=APIRouter()

def _call_project_member_query(query, *args, **kwargs):
    try:
        return query(*args, **kwargs)

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="Project member data conflicts with existing records."
        ) from error


@router.get("/project-members")
def search_project_members_endpoint(
    project_id: int | None = None,
    employee_id: int | None = None,
    role: str | None = None,
    joined_from: datetime | None = None,
    joined_to: datetime | None = None
):
    return _call_project_member_query(
        search_project_members,
        project_id=project_id,
        employee_id=employee_id,
        role=role,
        joined_from=joined_from,
        joined_to=joined_to
    )



@router.get("/project-members/project/{project_id}")
def get_project_members_endpoint(
    project_id: int = Path(..., gt=0)
):
    return _call_project_member_query(
        get_project_members,
        project_id
    )


@router.get("/project-members/employee/{employee_id}")
def get_employee_project_memberships_endpoint(
    employee_id: int = Path(..., gt=0)
):
    return _call_project_member_query(
        get_employee_project_memberships,
        employee_id
    )


@router.get("/project-members/{project_member_id}")
def get_project_member_endpoint(
    project_member_id: int = Path(..., gt=0)
):
    return _call_project_member_query(
        get_project_member,
        project_member_id
    )


class CreateProjectMember(BaseModel):
    project_id: int = Field(..., gt=0)
    employee_id: int = Field(..., gt=0)
    role: str = Field(..., min_length=1, max_length=100)
    joined_at: datetime | None = None


@router.post("/project-members")
def create_project_member_endpoint(
    member: CreateProjectMember
):
    return _call_project_member_query(
        create_project_member,
        project_id=member.project_id,
        employee_id=member.employee_id,
        role=member.role,
        joined_at=member.joined_at
    )

class UpdateProjectMember(BaseModel):
    id: int = Field(..., gt=0)
    role: str = Field(..., min_length=1, max_length=100)


@router.put("/project-members")
def update_project_member_endpoint(
    member: UpdateProjectMember
):
    return _call_project_member_query(
        update_project_member,
        id=member.id,
        role=member.role
    )

@router.delete("/project-members/{project_member_id}")
def delete_project_member_endpoint(
    project_member_id: int = Path(..., gt=0)
):
    return _call_project_member_query(
        delete_project_member,
        project_member_id
    )