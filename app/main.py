from __future__ import annotations

from fastapi import FastAPI

from .db import create_all


def create_app() -> FastAPI:
    app = FastAPI(title="Coach App")

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize database tables on startup."""
        create_all()

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
