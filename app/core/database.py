"""Enterprise Core Database Connection and Session Layer."""

from typing import Generator
from sqlalchemy.orm import Session

from app.database import (
    Base,
    SessionLocal,
    init_db as db_init,
    init_async_db,
    close_async_db,
    async_engine,
    sync_engine,
)


def init_db() -> None:
    """Initialize database tables idempotently."""
    db_init()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency providing a transactional SQLAlchemy Session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "Base",
    "SessionLocal",
    "get_db",
    "init_db",
    "init_async_db",
    "close_async_db",
    "async_engine",
    "sync_engine",
]

