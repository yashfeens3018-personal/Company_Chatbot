from company_project.database import SessionLocal
from company_project.models import Department

db = SessionLocal()

department = Department(
    name="Engineering",
    description="Software and AI engineering department",
    budget=500000
)

db.add(department)
db.commit()

print("Department created!")

db.close()