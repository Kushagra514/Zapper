"""Database connection and session factory module."""

from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from mech_cad.config import settings

# Create DB parent directory if using SQLite
if "sqlite" in settings.DATABASE_URL:
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)


def init_db():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Provide database session context."""
    with Session(engine) as session:
        yield session
