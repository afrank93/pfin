from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings


def get_engine() -> Engine:
    """Get SQLModel engine, creating parent directory if needed."""
    settings = get_settings()
    # Ensure parent directory exists (no-op if present)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)
    return engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    engine = get_engine()
    with Session(engine) as session:
        yield session


def create_all() -> None:
    """Create all database tables."""
    try:
        engine = get_engine()
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        raise RuntimeError(f"Failed to create database tables: {e}") from e
