from fastapi import HTTPException,APIRouter
from pydantic import BaseModel,Field
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from ..queries.announcements import (
    get_announcement,
    search_announcements,
    get_active_announcements,
    get_department_announcements,
    get_employee_announcements,
    create_announcement,
    update_announcement,
    delete_announcement
)

router=APIRouter()

def _call_announcement_query(query,*args,**kwargs):
    try:
        return query(*args,**kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409,detail="Announcement data conflicts with existing records.") from error


@router.get("/announcements")
def search_announcements_endpoint(
    title:str=None,
    content:str=None,
    created_by:int=None,
    department_id:int=None,
    published_from:datetime=None,
    published_to:datetime=None,
    expires_from:datetime=None,
    expires_to:datetime=None
):
    return _call_announcement_query(
        search_announcements,
        title=title,
        content=content,
        created_by=created_by,
        department_id=department_id,
        published_from=published_from,
        published_to=published_to,
        expires_from=expires_from,
        expires_to=expires_to
    )


@router.get("/announcements/active")
def get_active_announcements_endpoint(
    department_id:int=None
):
    return _call_announcement_query(
        get_active_announcements,
        department_id=department_id
    )


@router.get("/announcements/department/{department_id}")
def get_department_announcements_endpoint(
    department_id:int,
    include_expired:bool=False
):
    return _call_announcement_query(
        get_department_announcements,
        department_id=department_id,
        include_expired=include_expired
    )


@router.get("/announcements/employee/{employee_id}")
def get_employee_announcements_endpoint(
    employee_id:int
):
    return _call_announcement_query(get_employee_announcements,employee_id)


@router.get("/announcements/{announcement_id}")
def get_announcement_endpoint(
    announcement_id:int
):
    return _call_announcement_query(get_announcement,announcement_id)


class CreateAnnouncement(BaseModel):
    title:str=Field(...,min_length=1,max_length=200)
    content:str=Field(...,min_length=1)
    created_by:int=Field(...,gt=0)
    department_id:int|None=Field(default=None,gt=0)
    published_at:datetime|None=None
    expires_at:datetime|None=None


@router.post("/announcements")
def create_announcement_endpoint(
    announcement:CreateAnnouncement
):
    return _call_announcement_query(
        create_announcement,
        title=announcement.title,
        content=announcement.content,
        created_by=announcement.created_by,
        department_id=announcement.department_id,
        published_at=announcement.published_at,
        expires_at=announcement.expires_at
    )


class UpdateAnnouncement(BaseModel):
    id:int=Field(...,gt=0)
    title:str|None=Field(default=None,min_length=1,max_length=200)
    content:str|None=Field(default=None,min_length=1)
    department_id:int|None=Field(default=None,gt=0)
    published_at:datetime|None=None
    expires_at:datetime|None=None


@router.put("/announcements")
def update_announcement_endpoint(
    announcement:UpdateAnnouncement
):
    return _call_announcement_query(
        update_announcement,
        id=announcement.id,
        title=announcement.title,
        content=announcement.content,
        department_id=announcement.department_id,
        published_at=announcement.published_at,
        expires_at=announcement.expires_at
    )


@router.delete("/announcements/{announcement_id}")
def delete_announcement_endpoint(
    announcement_id:int
):
    return _call_announcement_query(delete_announcement,announcement_id)