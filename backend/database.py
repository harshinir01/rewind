"""
SQLAlchemy database setup for Rewind backend.
Uses SQLite for persistence. Data survives server restarts.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import DATABASE_URL

# SQLite — connect_args only needed for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables. Safe to call on every startup — won't drop existing data."""
    from backend import models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=engine)
