import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url is None:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)
class Base(DeclarativeBase):
    pass