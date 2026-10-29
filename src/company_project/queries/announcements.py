from sqlalchemy import select,update,delete,insert
from datetime import datetime

from ..models import Announcements,Employees,Department
from ..database import SessionLocal


def _require_department(department_id:int):
    session=SessionLocal()
    exists=session.execute(
        select(Department.department_id).where(
            Department.department_id==department_id
        )
    ).scalar_one_or_none()

    if exists is None:
        raise ValueError("Department does not exist.")


def _resolve_department_id(
    department_name: str | None = None,
    department_id: int | None = None,
):
    if department_name is None:
        if department_id is not None:
            _require_department(department_id=department_id)
        return department_id

    with SessionLocal() as session:
        resolved_department_id = session.execute(
            select(Department.department_id).where(
                Department.name == department_name
            )
        ).scalar_one_or_none()

    if resolved_department_id is None:
        raise ValueError("Department does not exist.")

    if (
        department_id is not None
        and department_id != resolved_department_id
    ):
        raise ValueError("Department name and ID do not match.")

    return resolved_department_id
    
def _require_employee(employee_id:int):
    session=SessionLocal()
    exists=session.execute(
        select(Employees.employee_id).where(
            Employees.employee_id==employee_id
        )
    ).scalar_one_or_none()

    if exists is None:
        raise ValueError(f"Employee with id {employee_id} does not exist.")
    
def announcement_id_exists(announcement_id:int):
    session=SessionLocal()
    exists=session.execute(
        select(Announcements.announcement_id).where(
            Announcements.announcement_id==announcement_id
        )
    ).scalar_one_or_none()

    if exists is None:
        raise ValueError(f"Announcement with id {announcement_id} does not exist.")
    

def get_announcement(announcement_id:int):
    announcement_id_exists(announcement_id)
    stmt=select(
        Announcements.announcement_id,
        Announcements.title,
        Announcements.content,
        Employees.first_name.label("creator_first_name"),
        Employees.last_name.label("creator_last_name"),
        Department.name.label("department_name"),
        Announcements.published_at,
        Announcements.expires_at
    ).join(
        Employees,
        Announcements.created_by==Employees.employee_id
    ).outerjoin(
        Department,
        Announcements.department_id==Department.department_id
    ).where(
        Announcements.announcement_id==announcement_id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        announcement=[dict(row._mapping) for row in result.all()]

    return announcement


def search_announcements(
    title:str=None,
    content:str=None,
    created_by:int=None,
    department_name:str=None,
    published_from:datetime=None,
    published_to:datetime=None,
    expires_from:datetime=None,
    expires_to:datetime=None,
    department_id:int=None,
):
    conditions=[]

    if title is not None:
        conditions.append(
            Announcements.title.ilike(f"%{title}%")
        )

    if content is not None:
        conditions.append(
            Announcements.content.ilike(f"%{content}%")
        )

    if created_by is not None:
        _require_employee(employee_id=created_by)
        conditions.append(
            Announcements.created_by==created_by
        )

    department_id = _resolve_department_id(
        department_name=department_name,
        department_id=department_id,
    )

    if department_id is not None:
        conditions.append(
            Announcements.department_id==department_id
        )

    if published_from is not None:
        conditions.append(
            Announcements.published_at>=published_from
        )

    if published_to is not None:
        conditions.append(
            Announcements.published_at<=published_to
        )

    if expires_from is not None:
        conditions.append(
            Announcements.expires_at>=expires_from
        )

    if expires_to is not None:
        conditions.append(
            Announcements.expires_at<=expires_to
        )

    stmt=select(
        Announcements.announcement_id,
        Announcements.title,
        Announcements.content,
        Employees.first_name.label("creator_first_name"),
        Employees.last_name.label("creator_last_name"),
        Department.name.label("department_name"),
        Announcements.published_at,
        Announcements.expires_at
    ).join(
        Employees,
        Announcements.created_by==Employees.employee_id
    ).outerjoin(
        Department,
        Announcements.department_id==Department.department_id
    ).where(*conditions).order_by(
        Announcements.published_at.desc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        announcements=[dict(row._mapping) for row in result.all()]

    return announcements


def get_active_announcements(
    department_name:str=None,
    *,
    department_id:int=None,
):
    current_time=datetime.utcnow()

    conditions=[
        Announcements.published_at<=current_time,
        (
            (Announcements.expires_at.is_(None)) |
            (Announcements.expires_at>=current_time)
        )
    ]

    department_id = _resolve_department_id(
        department_name=department_name,
        department_id=department_id,
    )

    if department_id is not None:
        conditions.append(
            (
                Announcements.department_id==department_id
            ) |
            (
                Announcements.department_id.is_(None)
            )
        )

    stmt=select(
        Announcements.announcement_id,
        Announcements.title,
        Announcements.content,
        Employees.first_name.label("creator_first_name"),
        Employees.last_name.label("creator_last_name"),
        Department.name.label("department_name"),
        Announcements.published_at,
        Announcements.expires_at
    ).join(
        Employees,
        Announcements.created_by==Employees.employee_id
    ).outerjoin(
        Department,
        Announcements.department_id==Department.department_id
    ).where(*conditions).order_by(
        Announcements.published_at.desc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        announcements=[dict(row._mapping) for row in result.all()]

    return announcements


def get_department_announcements(
    department_name:str=None,
    include_expired:bool=True,
    *,
    department_id:int=None,
):
    department_id = _resolve_department_id(
        department_name=department_name,
        department_id=department_id,
    )
    if department_id is None:
        raise ValueError("Provide a department name.")

    conditions=[
        Announcements.department_id==department_id
    ]

    if not include_expired:
        current_time=datetime.utcnow()

        conditions.extend([
            Announcements.published_at<=current_time,
            (
                (Announcements.expires_at.is_(None)) |
                (Announcements.expires_at>=current_time)
            )
        ])

    stmt=select(
        Announcements.announcement_id,
        Announcements.title,
        Announcements.content,
        Announcements.published_at,
        Announcements.expires_at
    ).where(*conditions).order_by(
        Announcements.published_at.desc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        announcements=[dict(row._mapping) for row in result.all()]

    return announcements


def get_employee_announcements(
    first_name: str,
    last_name: str,
):
    if not first_name.strip() or not last_name.strip():
        raise ValueError("Provide both an employee first name and last name.")

    employee_ids_stmt = select(Employees.employee_id).where(
        Employees.first_name.ilike(first_name.strip()),
        Employees.last_name.ilike(last_name.strip()),
    )

    with SessionLocal() as session:
        employee_ids = session.execute(employee_ids_stmt).scalars().all()

    if not employee_ids:
        raise LookupError(
            f"No employee found with the name {first_name.strip()} "
            f"{last_name.strip()}."
        )

    stmt=select(
        Announcements.announcement_id,
        Announcements.title,
        Announcements.content,
        Department.name.label("department_name"),
        Announcements.published_at,
        Announcements.expires_at,
        Announcements.created_by
    ).outerjoin(
        Department,
        Announcements.department_id==Department.department_id
    ).where(
        Announcements.created_by.in_(employee_ids)
    ).order_by(
        Announcements.published_at.desc()
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        announcements=[dict(row._mapping) for row in result.all()]

    return announcements


def create_announcement(
    title:str,
    content:str,
    created_by:int,
    department_name:str=None,
    published_at:datetime=None,
    expires_at:datetime=None,
    department_id:int=None,
):
    department_id = _resolve_department_id(
        department_name=department_name,
        department_id=department_id,
    )

    if published_at is not None and expires_at is not None:
        if expires_at<published_at:
            raise ValueError("Expiry date cannot be before published date")
    

    with SessionLocal() as session:
        creator_exists=session.execute(
            select(Employees.employee_id).where(
                Employees.employee_id==created_by
            )
        ).scalar_one_or_none()

        if creator_exists is None:
            raise ValueError("Employee does not exist")

    values={
        "title":title,
        "content":content,
        "created_by":created_by,
        "department_id":department_id
    }

    if published_at is not None:
        values["published_at"]=published_at

    if expires_at is not None:
        values["expires_at"]=expires_at

    stmt=insert(Announcements).values(**values)

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()
        announcement_id=result.inserted_primary_key[0]

    return f"Announcement with {announcement_id} has been created successfully!!"


def update_announcement(
    id:int,
    title:str=None,
    content:str=None,
    department_name:str=None,
    published_at:datetime=None,
    expires_at:datetime=None,
    department_id:int=None,
):
    if id is None:
        raise ValueError("Provide announcement ID in order to update the announcement")
    
    announcement_id_exists(announcement_id=id)

    if all(value is None for value in [
        title,
        content,
        department_name,
        department_id,
        published_at,
        expires_at
    ]):
        raise ValueError("Provide at least one field to update")

    department_id = _resolve_department_id(
        department_name=department_name,
        department_id=department_id,
    )

    if department_id is not None:
        values={"department_id": department_id}
    else:
        values={}

    if published_at is not None or expires_at is not None:
        with SessionLocal() as session:
            current=session.execute(
                select(
                    Announcements.published_at,
                    Announcements.expires_at
                ).where(
                    Announcements.announcement_id==id
                )
            ).one_or_none()

        if current is None:
            return 0

        final_published_at=(
            published_at
            if published_at is not None
            else current.published_at
        )

        final_expires_at=(
            expires_at
            if expires_at is not None
            else current.expires_at
        )

        if (
            final_expires_at is not None and
            final_published_at is not None and
            final_expires_at<final_published_at
        ):
            raise ValueError("Expiry date cannot be before published date")

    if title is not None:
        values["title"]=title

    if content is not None:
        values["content"]=content

    if published_at is not None:
        values["published_at"]=published_at

    if expires_at is not None:
        values["expires_at"]=expires_at

    stmt=update(Announcements).where(
        Announcements.announcement_id==id
    ).values(**values)

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    return f"Announcement has been updated successfully!"


def delete_announcement(id:int):
    if id is None:
        raise ValueError("Provide announcement ID in order to delete the announcement")

    stmt=delete(Announcements).where(
        Announcements.announcement_id==id
    )

    with SessionLocal() as session:
        result=session.execute(stmt)
        session.commit()

    if result.rowcount==0:
        raise LookupError(f"Announcement id: {id} does not exist.")
    return f"Announcement with id {id} has been deleted."