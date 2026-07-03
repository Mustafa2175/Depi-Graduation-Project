"""
Database connection module.

Reads the PG* environment variables already established by the project
(.env file) and creates a SQLAlchemy engine + session factory.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env from the project root (one level above this file's folder).
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "jobmarket")
PGPASSWORD = os.getenv("PGPASSWORD", "jobmarket")
PGDATABASE = os.getenv("PGDATABASE", "job_market_tracker")

DATABASE_URL = (
    f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}"
    f"@{PGHOST}:{PGPORT}/{PGDATABASE}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a DB session, closing it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
