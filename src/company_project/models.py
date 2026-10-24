from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Department(Base):
    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    budget: Mapped[float | None] = mapped_column(
        Numeric(15, 2),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    employees: Mapped[list["Employees"]] = relationship(
        back_populates="department"
    )
    projects: Mapped[list["Projects"]] = relationship(
        back_populates="department"
    )

    announcements: Mapped[list["Announcements"]] = relationship(
        back_populates="department"
    )
    
class Employees(Base):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    gender: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )
    email: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )
    
    password_hash: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        unique=True
    )
    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    date_of_birth: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    date_joined: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    job_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id"),
        nullable=False
    )
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=True
    )
    salary: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )
    employment_status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    department: Mapped[Department] = relationship(
        back_populates="employees"
    )
    manager: Mapped["Employees | None"] = relationship(
        remote_side=[employee_id],
        back_populates="direct_reports"
    )
    direct_reports: Mapped[list["Employees"]] = relationship(
        back_populates="manager"
    )
    created_tickets:Mapped[list['Tickets']]=relationship(
        foreign_keys="Tickets.created_by",
        back_populates='creator'
    )
    assigned_tickets:Mapped[list['Tickets']]=relationship(
            foreign_keys="Tickets.assigned_to",
            back_populates='assignee'
    )
    ticket_commentted:Mapped[list['Ticket_Comments']]=relationship(
            back_populates="ticket_author"
    )
    assets: Mapped[list["Assets"]] = relationship(
        foreign_keys="Assets.assigned_to",
        back_populates="assigned_employee"
    )

    leave_requests: Mapped[list["Leave_Requests"]] = relationship(
        foreign_keys="Leave_Requests.employee_id",
        back_populates="employee"
    )

    approved_leave_requests: Mapped[list["Leave_Requests"]] = relationship(
        foreign_keys="Leave_Requests.approved_by",
        back_populates="approver"
    )

    leave_balances: Mapped[list["Leave_Balances"]] = relationship(
        back_populates="employee"
    )

    managed_projects: Mapped[list["Projects"]] = relationship(
        foreign_keys="Projects.project_manager_id",
        back_populates="project_manager"
    )

    project_memberships: Mapped[list["Project_Members"]] = relationship(
        back_populates="employee"
    )

    announcements: Mapped[list["Announcements"]] = relationship(
        back_populates="creator"
    )
    
        
class Tickets(Base):
    __tablename__="tickets"
    ticket_id:Mapped[int]= mapped_column(
        Integer,
        primary_key=True,
        nullable=False
        )
    created_by:Mapped[int]=mapped_column(
        ForeignKey('employees.employee_id'),
        nullable=False
    )
    assigned_to:Mapped[int|None]=mapped_column(
        ForeignKey('employees.employee_id'),
        nullable=True
    )
    title:Mapped[str]=mapped_column(
        String(100),
        nullable=False
    )
    description:Mapped[str]=mapped_column(
        Text,
        nullable=False
    )
    category:Mapped[str]=mapped_column(
        String(100),
        nullable=False
    )
    status:Mapped[str]=mapped_column(
        String(100),
        nullable=False
    )
    created_at:Mapped[datetime]=mapped_column(
       DateTime,
       default= datetime.utcnow,
       nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    resolved_at:Mapped[datetime|None]=mapped_column(
       DateTime,
       nullable=True
    )
    closed_at:Mapped[datetime|None]=mapped_column(
       DateTime,
       nullable=True
    )
    creator:Mapped[Employees]=relationship(
        foreign_keys=[created_by],
        back_populates="created_tickets"
    )
    assignee:Mapped[Employees|None]=relationship(
            foreign_keys=[assigned_to],
            back_populates="assigned_tickets"
    )
    ticket_comment:Mapped[list["Ticket_Comments"]]=relationship(
            back_populates="ticket_info"
    )
    priority: Mapped[str] = mapped_column(
    String(30),
    default="medium",
    nullable=False
    )
    due_at:Mapped[datetime|None]=mapped_column(
    DateTime,
    nullable=True
    )
    
class Ticket_Comments(Base):
    __tablename__ = "ticket_comments"
    comment_id:Mapped[int]=mapped_column(
        Integer,
        primary_key=True
        )
    ticket_id:Mapped[int]=mapped_column(
        ForeignKey("tickets.ticket_id"),
        nullable=False
    )
    author_id:Mapped[int]=mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )
    comment:Mapped[str]=mapped_column(
        Text,
        nullable=False
    )
    created_at:Mapped[datetime]=mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    ticket_info:Mapped[Tickets]=relationship(
        back_populates="ticket_comment"
    )
    ticket_author:Mapped[Employees]=relationship(
        back_populates="ticket_commentted"
    )


class Assets(Base):
    __tablename__ = "assets"

    asset_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    asset_tag: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    asset_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    serial_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    purchase_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    purchase_cost: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=True
    )

    condition: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    warranty_expiry: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    assigned_employee: Mapped["Employees | None"] = relationship(
        foreign_keys=[assigned_to],
        back_populates="assets"
    )



class Leave_Requests(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint(
            "leave_type IN ('Annual', 'Sick', 'Casual', 'Unpaid', 'Maternity')",
            name="ck_leave_requests_leave_type"
        ),
        CheckConstraint(
            "status IN ('Pending', 'Approved', 'Rejected')",
            name="ck_leave_requests_status"
        ),
        CheckConstraint(
            "start_date < end_date",
            name="ck_leave_requests_date_order"
        ),
    )

    leave_request_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    leave_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    end_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    employee: Mapped["Employees"] = relationship(
        foreign_keys=[employee_id],
        back_populates="leave_requests"
    )

    approver: Mapped["Employees | None"] = relationship(
        foreign_keys=[approved_by],
        back_populates="approved_leave_requests"
    )


class Leave_Balances(Base):
    __tablename__ = "leave_balances"

    leave_balance_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    leave_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    total_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    used_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    remaining_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    employee: Mapped["Employees"] = relationship(
        back_populates="leave_balances"
    )

class Projects(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Planning', 'Active', 'On Hold', 'Completed')",
            name="ck_projects_status"
        ),
        CheckConstraint(
            "expected_end_date IS NULL OR start_date < expected_end_date",
            name="ck_projects_date_order"
        ),
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id"),
        nullable=False
    )

    project_manager_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    expected_end_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    department: Mapped["Department"] = relationship(
        back_populates="projects"
    )

    project_manager: Mapped["Employees"] = relationship(
        foreign_keys=[project_manager_id],
        back_populates="managed_projects"
    )

    project_members: Mapped[list["Project_Members"]] = relationship(
        back_populates="project"
    )

class Project_Members(Base):
    __tablename__ = "project_members"
    __table_args__ = (
    UniqueConstraint("project_id","employee_id"),)

    project_member_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.project_id"),
        nullable=False
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    project: Mapped["Projects"] = relationship(
        back_populates="project_members"
    )

    employee: Mapped["Employees"] = relationship(
        back_populates="project_memberships"
    )



class Announcements(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        Index(
            "uq_announcements_title_department_id",
            "title",
            "department_id",
            unique=True
        ),
    )

    announcement_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.department_id"),
        nullable=True
    )

    published_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    creator: Mapped["Employees"] = relationship(
        back_populates="announcements"
    )

    department: Mapped["Department | None"] = relationship(
        back_populates="announcements"
    )
