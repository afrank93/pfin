from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: Path = Path.home() / ".coach_app"
    
    @property
    def db_path(self) -> Path:
        """Compute database path dynamically from data_dir."""
        return self.data_dir / "data.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
