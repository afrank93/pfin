from __future__ import annotations

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.lineups import router as lineups_router
from routers.players import router as players_router
from routers.teams import router as teams_router

from .config import Settings
from .db import create_all
from services.backup_service import BackupService
from utils.errors import ServiceError, handle_service_errors


def create_app() -> FastAPI:
    app = FastAPI(title="Coach App")

    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Setup templates
    templates = Jinja2Templates(directory="templates")

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize database tables on startup."""
        create_all()

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Dashboard route
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse(
            "dashboard.html", {"request": request}
        )

    # Lineup builder route
    @app.get(
        "/teams/{team_id}/lineups/{template_id}/builder",
        response_class=HTMLResponse
    )
    async def lineup_builder(
        request: Request, team_id: int, template_id: int
    ):
        # This will be handled by the lineups router, but we need the template
        # For now, return a placeholder
        return templates.TemplateResponse(
            "lineup_builder.html",
            {
                "request": request,
                "template": {
                    "id": template_id,
                    "name": "Lineup Template",
                    "notes": ""
                },
                "team": {"id": team_id, "name": "Team", "season": "2024-25"},
                "slots": [],
                "available_players": [],
                "slots_by_type": {"FWD": [], "DEF": [], "G": []}
            }
        )

    # Backup/restore routes
    @app.get("/api/backup")
    @handle_service_errors
    async def download_backup():
        """Download a backup of the current database."""
        try:
            settings = Settings()
            backup_info = BackupService.create_backup(settings)

            return Response(
                content=backup_info["content"],
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename={backup_info['filename']}"
                    )
                }
            )
        except ServiceError as e:
            raise e
        except Exception as e:
            raise ServiceError(f"Backup download failed: {str(e)}") from e

    @app.post("/api/restore")
    @handle_service_errors
    async def restore_backup(file: UploadFile = File(...)):
        """Restore database from backup file."""
        try:
            settings = Settings()
            restore_info = BackupService.restore_backup(settings, file)
            return restore_info
        except ServiceError as e:
            raise e
        except Exception as e:
            raise ServiceError(f"Backup restore failed: {str(e)}") from e

    @app.get("/api/backup/info")
    @handle_service_errors
    async def get_backup_info():
        """Get information about the current database."""
        try:
            settings = Settings()
            return BackupService.get_database_info(settings)
        except ServiceError as e:
            raise e
        except Exception as e:
            raise ServiceError(f"Failed to get backup info: {str(e)}") from e

    # Include routers
    app.include_router(teams_router)
    app.include_router(players_router)
    app.include_router(lineups_router)

    return app


app = create_app()
