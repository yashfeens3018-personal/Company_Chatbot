from __future__ import annotations

import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import delete, insert, select

from company_project.database import SessionLocal
from company_project.models import (
    Announcements,
    Assets,
    Department,
    Employees,
    Leave_Balances,
    Leave_Requests,
    Project_Members,
    Projects,
    Ticket_Comments,
    Tickets,
)
from company_project.queries.announcements import create_announcement
from company_project.queries.assets import asset_conditions, asset_statuses, create_asset
from company_project.queries.department import create_department
from company_project.queries.employees import (
    VALID_EMPLOYMENT_STATUSES,
    create_employee,
    update_employee,
)
from company_project.queries.leave_requests import (
    VALID_LEAVE_STATUSES,
    VALID_LEAVE_TYPES,
    create_leave_request,
)
from company_project.queries.project_members import create_project_member
from company_project.queries.projects import VALID_PROJECT_STATUSES, create_project
from company_project.queries.ticket_comments import create_comment
from company_project.queries.tickets import (
    create_ticket,
    ticket_categories,
    ticket_priorities,
    ticket_statuses,
)

fake = Faker()
random.seed(42)
Faker.seed(42)

NUM_DEPARTMENTS = 6
NUM_EMPLOYEES = 60
NUM_TICKETS = 100
NUM_COMMENTS = 150
NUM_ASSETS = 50
NUM_LEAVE_REQUESTS = 40
NUM_PROJECTS = 10
NUM_ANNOUNCEMENTS = 15
CURRENT_YEAR = datetime.now().year


def random_date(start_year: int = 2023, end_year: int = 2026) -> datetime:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def clear_database() -> None:
    with SessionLocal() as session:
        for model in [
            Project_Members,
            Ticket_Comments,
            Announcements,
            Leave_Requests,
            Leave_Balances,
            Assets,
            Tickets,
            Projects,
            Employees,
            Department,
        ]:
            session.execute(delete(model))
        session.commit()


def seed_departments() -> list[int]:
    department_names = [
        "Engineering",
        "Human Resources",
        "Finance",
        "Marketing",
        "Sales",
        "Information Technology",
        "Operations",
        "Research and Development",
    ]

    department_ids: list[int] = []
    for name in department_names[:NUM_DEPARTMENTS]:
        department_id = create_department(
            name=name,
            description=fake.paragraph(nb_sentences=3),
            budget=random.randint(200000, 1000000),
        )
        department_ids.append(department_id)

    return department_ids


def seed_employees(department_ids: list[int]) -> dict[int, int]:
    employee_department: dict[int, int] = {}
    job_titles = [
        "Software Engineer",
        "AI Engineer",
        "Data Scientist",
        "Backend Engineer",
        "Frontend Engineer",
        "Product Manager",
        "HR Specialist",
        "Financial Analyst",
        "Marketing Manager",
        "Operations Manager",
        "DevOps Engineer",
        "QA Engineer",
        "Research Scientist",
        "Business Analyst",
    ]

    for index in range(NUM_EMPLOYEES):
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}.{index + 1}@company.local"
        phone_number = f"+1{(index + 1):010d}"
        department_id = random.choice(department_ids)
        employment_status = random.choice(sorted(VALID_EMPLOYMENT_STATUSES))

        employee_id = create_employee(
            first_name=first_name,
            last_name=last_name,
            gender=random.choice(["Male", "Female", "Other"]),
            email=email,
            phone_number=phone_number,
            address=fake.address(),
            date_of_birth=random_date(1985, 2005),
            date_joined=random_date(2020, 2026),
            job_title=random.choice(job_titles),
            department_id=department_id,
            manager_id=None,
            salary=random.randint(75000, 220000),
            employment_status=employment_status,
        )
        employee_department[employee_id] = department_id

    for employee_id, department_id in employee_department.items():
        possible_managers = [
            candidate_id
            for candidate_id, candidate_department_id in employee_department.items()
            if candidate_id != employee_id and candidate_department_id == department_id
        ]
        if possible_managers:
            manager_id = random.choice(possible_managers)
            update_employee(employee_id, manager_id=manager_id)

    return employee_department


def seed_tickets(employee_ids: list[int]) -> list[int]:
    ticket_ids: list[int] = []
    for _ in range(NUM_TICKETS):
        created_by = random.choice(employee_ids)
        assigned_to = random.choice(employee_ids) if random.random() < 0.8 else None
        status = random.choice(ticket_statuses)
        priority = random.choice(ticket_priorities)
        due_at = datetime.utcnow() + timedelta(days=random.randint(1, 30))

        ticket_id = create_ticket(
            created_by=created_by,
            title=fake.sentence(nb_words=6)[:100],
            description=fake.paragraph(nb_sentences=3),
            category=random.choice(ticket_categories),
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            due_at=due_at,
        )
        ticket_ids.append(ticket_id)

    return ticket_ids


def seed_ticket_comments(ticket_ids: list[int], employee_ids: list[int]) -> None:
    for _ in range(NUM_COMMENTS):
        ticket_id = random.choice(ticket_ids)
        author_id = random.choice(employee_ids)
        comment = fake.paragraph(nb_sentences=random.randint(1, 3)).strip()
        create_comment(ticket_id=ticket_id, author_id=author_id, comment=comment)


def seed_assets(employee_ids: list[int]) -> None:
    with SessionLocal() as session:
        employee_names = {
            employee.employee_id: (employee.first_name, employee.last_name)
            for employee in session.execute(
                select(
                    Employees.employee_id,
                    Employees.first_name,
                    Employees.last_name,
                )
            )
        }

    for index in range(NUM_ASSETS):
        status = random.choice(asset_statuses)
        assigned_to = random.choice(employee_ids) if status == "assigned" else None

        if status in {"lost", "disposed"}:
            assigned_to = None

        assigned_employee = (
            employee_names[assigned_to]
            if assigned_to is not None
            else (None, None)
        )

        purchase_date = random_date(2022, 2026)
        warranty_expiry = purchase_date + timedelta(days=random.randint(365, 1825))

        create_asset(
            asset_tag=f"NX-{index + 1000:05d}",
            asset_type=random.choice(["Laptop", "Desktop", "Monitor", "Phone", "Tablet", "Keyboard", "Headset"]),
            serial_number=f"SN-{index + 10000:08d}",
            status=status,
            condition=random.choice(asset_conditions),
            brand=random.choice(["Dell", "HP", "Lenovo", "Apple", "Samsung"]),
            model=f"{fake.word().title()} {random.randint(1, 20)}",
            purchase_date=purchase_date,
            purchase_cost=random.randint(20000, 500000),
            assigned_to_first_name=assigned_employee[0],
            assigned_to_last_name=assigned_employee[1],
            warranty_expiry=warranty_expiry,
        )


def seed_leave_requests(employee_ids: list[int]) -> None:
    for _ in range(NUM_LEAVE_REQUESTS):
        employee_id = random.choice(employee_ids)
        leave_type = random.choice(list(VALID_LEAVE_TYPES))
        start_date = random_date(2025, 2026)
        end_date = start_date + timedelta(days=random.randint(1, 7))
        status = random.choice(list(VALID_LEAVE_STATUSES))
        approved_by = random.choice(employee_ids) if status in {"Approved", "Rejected"} else None

        create_leave_request(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=fake.sentence(),
            status=status,
            approved_by=approved_by,
        )


def seed_leave_balances(employee_ids: list[int]) -> None:
    with SessionLocal() as session:
        for employee_id in employee_ids:
            for leave_type in ["Annual", "Sick", "Casual"]:
                total_days = random.choice([10, 12, 15, 20, 30])
                used_days = random.randint(0, total_days)
                remaining_days = total_days - used_days
                session.execute(
                    insert(Leave_Balances).values(
                        employee_id=employee_id,
                        leave_type=leave_type,
                        total_days=total_days,
                        used_days=used_days,
                        remaining_days=remaining_days,
                        year=CURRENT_YEAR,
                    )
                )
        session.commit()


def seed_projects(department_ids: list[int], employee_department: dict[int, int]) -> list[int]:
    project_ids: list[int] = []
    for _ in range(NUM_PROJECTS):
        department_id = random.choice(department_ids)
        manager_candidates = [
            employee_id
            for employee_id, emp_department_id in employee_department.items()
            if emp_department_id == department_id
        ]
        if not manager_candidates:
            manager_candidates = list(employee_department)

        manager_id = random.choice(manager_candidates)
        start_date = random_date(2024, 2026)
        expected_end_date = start_date + timedelta(days=random.randint(60, 365))

        project_id = create_project(
            name=f"{fake.company()} {random.choice(['Platform', 'Refresh', 'Launch', 'Migration', 'Expansion'])}",
            description=fake.paragraph(nb_sentences=3),
            department_id=department_id,
            project_manager_id=manager_id,
            status=random.choice(list(VALID_PROJECT_STATUSES)),
            start_date=start_date,
            expected_end_date=expected_end_date,
        )
        project_ids.append(project_id)

    return project_ids


def seed_project_members(project_ids: list[int], employee_ids: list[int]) -> None:
    for project_id in project_ids:
        member_count = random.randint(3, min(8, len(employee_ids)))
        selected_employees = random.sample(employee_ids, k=member_count)
        for employee_id in selected_employees:
            joined_at = datetime.utcnow() - timedelta(days=random.randint(1, 365))
            create_project_member(
                project_id=project_id,
                employee_id=employee_id,
                role=random.choice(["Developer", "Designer", "Analyst", "Engineer", "Researcher", "Team Lead"]),
                joined_at=joined_at,
            )


def seed_announcements(employee_ids: list[int], department_ids: list[int]) -> None:
    for index in range(NUM_ANNOUNCEMENTS):
        created_by = random.choice(employee_ids)
        department_id = random.choice(department_ids) if random.random() < 0.6 else None
        published_at = random_date(2025, 2026)
        expires_at = published_at + timedelta(days=random.randint(7, 90))

        create_announcement(
            title=f"{fake.catch_phrase()} {index + 1}",
            content=fake.paragraph(nb_sentences=4),
            created_by=created_by,
            department_id=department_id,
            published_at=published_at,
            expires_at=expires_at,
        )


def seed_database() -> None:
    print("Clearing existing data...")
    clear_database()
    print("Existing data cleared.")

    print("Creating departments...")
    department_ids = seed_departments()
    print(f"Created {len(department_ids)} departments.")

    print("Creating employees...")
    employee_department = seed_employees(department_ids)
    employee_ids = list(employee_department)
    print(f"Created {len(employee_ids)} employees.")

    print("Creating tickets...")
    ticket_ids = seed_tickets(employee_ids)
    print(f"Created {len(ticket_ids)} tickets.")

    print("Creating ticket comments...")
    seed_ticket_comments(ticket_ids, employee_ids)
    print(f"Created {NUM_COMMENTS} ticket comments.")

    print("Creating assets...")
    seed_assets(employee_ids)
    print(f"Created {NUM_ASSETS} assets.")

    print("Creating leave requests...")
    seed_leave_requests(employee_ids)
    print(f"Created {NUM_LEAVE_REQUESTS} leave requests.")

    print("Creating leave balances...")
    seed_leave_balances(employee_ids)
    print(f"Created {len(employee_ids) * 3} leave balances.")

    print("Creating projects...")
    project_ids = seed_projects(department_ids, employee_department)
    print(f"Created {len(project_ids)} projects.")

    print("Creating project members...")
    project_member_total = 0
    for project_id in project_ids:
        member_count = 0
        for _ in range(random.randint(3, min(8, len(employee_ids)))):
            member_count += 1
        project_member_total += member_count
    seed_project_members(project_ids, employee_ids)
    print(f"Created {project_member_total} project memberships.")

    print("Creating announcements...")
    seed_announcements(employee_ids, department_ids)
    print(f"Created {NUM_ANNOUNCEMENTS} announcements.")

    print("\n" + "=" * 50)
    print("DATABASE SEEDING COMPLETE!")
    print("=" * 50)
    print(f"Departments:       {len(department_ids)}")
    print(f"Employees:         {len(employee_ids)}")
    print(f"Tickets:           {len(ticket_ids)}")
    print(f"Comments:          {NUM_COMMENTS}")
    print(f"Assets:            {NUM_ASSETS}")
    print(f"Leave Requests:    {NUM_LEAVE_REQUESTS}")
    print(f"Leave Balances:    {len(employee_ids) * 3}")
    print(f"Projects:          {len(project_ids)}")
    print(f"Project Members:   {project_member_total}")
    print(f"Announcements:     {NUM_ANNOUNCEMENTS}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        seed_database()
    except Exception as exc:
        print("ERROR:")
        print(exc)
        raise
