from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from datetime import timedelta

from .api.announcements import router as announcement_router
from .api.assets import router as assets_router
from .api.department import router as department_router
from .api.employees import router as employees_router
from .api.leave_balances import router as leavebalances_router
from .api.leave_requests import router as leaverequests_router
from .api.project_members import router as projectmembers_router
from .api.projects import router as projects_router
from .api.ticket_comments import router as ticketcomments_router
from .api.tickets import router as tickets_router

from .auth.security import (
    verify_password,
    create_token,
    get_user,
    get_user_from_db,
)

app = FastAPI()

app.include_router(announcement_router)
app.include_router(assets_router)
app.include_router(department_router)
app.include_router(employees_router)
app.include_router(leavebalances_router)
app.include_router(leaverequests_router)
app.include_router(projectmembers_router)
app.include_router(projects_router)
app.include_router(ticketcomments_router)
app.include_router(tickets_router)


@app.post("/token/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_email = form_data.username
    password = form_data.password

    if not verify_password(user_email, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_from_db(user_email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user["employment_status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee account is not active",
        )

    token = create_token(
        {"email": user_email},
        expiry_duration=30,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@app.get("/users/me")
def read_users_me(
    current_user: Annotated[dict, Depends(get_user)]
):
    return current_user