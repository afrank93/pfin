from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: Path = Path.home() / ".coach_app"
    db_path: Path = (Path.home() / ".coach_app" / "data.db")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
