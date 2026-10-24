from fastapi import APIRouter,HTTPException,Path,Query

from ..queries.leave_balances import (
    get_leave_balance,
    search_leave_balances
)

router=APIRouter()

def _call_leave_balance_query(query,*args,**kwargs):
    try:
        return query(*args,**kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error


@router.get("/leave-balances")
def search_leave_balances_endpoint(
    employee_id:int|None=Query(default=None,gt=0),
    leave_type:str|None=Query(default=None,min_length=1,max_length=50),
    year:int|None=Query(default=None,ge=1,le=9999),
    min_remaining_days:int|None=Query(default=None,ge=0),
    max_remaining_days:int|None=Query(default=None,ge=0)
):
    return _call_leave_balance_query(
        search_leave_balances,
        employee_id=employee_id,
        leave_type=leave_type,
        year=year,
        min_remaining_days=min_remaining_days,
        max_remaining_days=max_remaining_days
    )


@router.get("/leave-balances/employee/{employee_id}/balance")
def get_leave_balance_endpoint(
    employee_id:int=Path(...,gt=0),
    leave_type:str|None=Query(default=None,min_length=1,max_length=50),
    year:int|None=Query(default=None,ge=1,le=9999)
):
    return _call_leave_balance_query(
        get_leave_balance,
        employee_id=employee_id,
        leave_type=leave_type,
        year=year
    )