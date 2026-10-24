from fastapi import APIRouter,HTTPException,Path
from pydantic import BaseModel,Field
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from ..queries.leave_requests import (
    get_leave_request,
    search_leave_requests,
    get_current_leaves,
    create_leave_request,
    update_leave_request,
    delete_leave_request
)

router=APIRouter()

def _call_leave_request_query(query,*args,**kwargs):
    try:
        return query(*args,**kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409,detail="Leave request data conflicts with existing records.") from error


@router.get("/leave-requests/")
def get_leave_requests_endpoint():
    return _call_leave_request_query(search_leave_requests)


@router.get("/leave-requests/current")
def get_current_leaves_endpoint():
    return _call_leave_request_query(get_current_leaves)


@router.delete("/leave-requests/{leave_request_id}")
def delete_leave_request_endpoint(leave_request_id:int=Path(...,gt=0)):
    return _call_leave_request_query(delete_leave_request,leave_request_id)

@router.get("/leave-requests/{leave_request_id}")
def get_leave_request_endpoint(leave_request_id:int=Path(...,gt=0)):
    return _call_leave_request_query(get_leave_request,leave_request_id)



class UpdateLeaveRequest(BaseModel):
    id:int=Field(...,gt=0)
    leave_type:str|None=Field(default=None,min_length=1,max_length=50)
    start_date:datetime|None=None
    end_date:datetime|None=None
    reason:str|None=None
    status:str|None=Field(default=None,min_length=1,max_length=50)
    approved_by:int|None=Field(default=None,gt=0)


@router.put("/leave-requests")
def update_leave_request_endpoint(request:UpdateLeaveRequest):
    return _call_leave_request_query(
        update_leave_request,
        id=request.id,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
        status=request.status,
        approved_by=request.approved_by
    )


class CreateLeaveRequest(BaseModel):
    employee_id:int=Field(...,gt=0)
    leave_type:str=Field(...,min_length=1,max_length=50)
    start_date:datetime
    end_date:datetime
    reason:str|None=None


@router.post("/leave-requests")
def create_leave_request_endpoint(request:CreateLeaveRequest):
    return _call_leave_request_query(
        create_leave_request,
        employee_id=request.employee_id,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason
    )