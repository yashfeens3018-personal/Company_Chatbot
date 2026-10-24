import jwt
from fastapi import status, Depends, HTTPException
from jwt.exceptions import InvalidTokenError
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import timedelta, timezone, datetime
import os
from pwdlib import PasswordHash
from ..models import Employees, Department
from ..database import SessionLocal
from sqlalchemy import select

ALGORITHM = 'HS256'
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
EXPIRY_MINUTES = 30

oauth = OAuth2PasswordBearer(tokenUrl='/token/login')

def get_user_from_db(user_email: str):
    stmt = select(
        Employees.employee_id,
        Employees.first_name,
        Employees.last_name,
        Employees.gender,
        Employees.email,
        Employees.phone_number,
        Employees.date_joined,
        Employees.job_title,
        Employees.employment_status,
        Department.name.label("department_name"),
        Employees.manager_id
    ).join(
        Department,
        Employees.department_id == Department.department_id
    ).where(Employees.email == user_email)

    with SessionLocal() as session:
        result = session.execute(stmt).mappings().one_or_none()

    return dict(result) if result else None


password_hash = PasswordHash.recommended()

def create_token(data: dict, expiry_duration: int | None = None):
    dataa = data.copy()

    if expiry_duration is not None:
        exp = datetime.now(timezone.utc) + timedelta(minutes=expiry_duration)
    else:
        exp = datetime.now(timezone.utc) + timedelta(minutes=EXPIRY_MINUTES)

    dataa.update({'exp': exp})
    token = jwt.encode(dataa, SECRET_KEY, algorithm=ALGORITHM)
    return token


def get_user(token: Annotated[str, Depends(oauth)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get('email')

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unable to validate the credentials',
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_from_db(user_email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user["employment_status"] != "Active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee account is not active",
        )

    return user


def verify_password(user_email: str, password: str):
    stmt = select(Employees.password_hash).where(
        Employees.email == user_email
    )

    with SessionLocal() as session:
        hashed_password = session.execute(stmt).scalar_one_or_none()

    if hashed_password is None:
        return False

    try:
        return password_hash.verify(password, hashed_password)
    except Exception:
        return False