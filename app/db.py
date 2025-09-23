from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings


def get_engine():
    settings = get_settings()
    # Ensure parent directory exists (no-op if present)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)
    return engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    engine = get_engine()
    with Session(engine) as session:
        yield session


def get_session() -> Generator[Session, None, None]:
    engine = get_engine()
    with Session(engine) as session:
        yield session


def create_all() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
