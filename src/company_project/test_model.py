from company_project.models import (
    Department,
    Employees,
    Tickets,
    Ticket_Comments,
    Assets,
    Leave_Requests,
    Leave_Balances,
    Projects,
    Project_Members,
    Announcements,
)
from sqlalchemy.orm import configure_mappers
configure_mappers()

print("All models imported successfully!")