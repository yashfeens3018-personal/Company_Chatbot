import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url is None:
    raise ValueError("DATABASE_URL is not set")

engine_options = {"pool_pre_ping": True}
if not database_url.startswith("sqlite"):
    engine_options.update(pool_size=10, max_overflow=10, pool_recycle=1800)
engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine)
class Base(DeclarativeBase):
    pass