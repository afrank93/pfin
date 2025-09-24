from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    Response,
    status,
)
from fastapi.datastructures import UploadFile
from sqlmodel import Session, select

from app.db import get_session
from app.models import Player, Team
from app.schemas import PlayerIn, PlayerOut, PlayerUpdate
from services.csv_service import CSVService
from utils.errors import (
    ServiceError,
    create_not_found_error,
    create_validation_error,
    handle_service_errors,
)
from utils.validators import (
    ValidationError as ValidatorError,
)
from utils.validators import (
    validate_player_data,
)

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/teams/{team_id}/players", response_model=list[PlayerOut])
@handle_service_errors
async def list_players(
    team_id: int,
    session: Session = Depends(get_session),
    position: str | None = Query(
        None, description="Filter by position (F, D, G)"
    ),
    hand: str | None = Query(
        None, description="Filter by handedness (L, R)"
    ),
    birth_year: int | None = Query(None, description="Filter by birth year"),
    sort_by: str = Query(
        "name", description="Sort by: name, position, jersey, birthdate"
    ),
    sort_order: str = Query(
        "asc", description="Sort order: asc, desc"
    ),
) -> list[Player]:
    """List players for a team with optional filters and sorting."""
    # Verify team exists
    team = session.get(Team, team_id)
    if not team:
        raise create_not_found_error("Team", team_id)

    # Validate sort parameters
    valid_sort_fields = ["name", "position", "jersey", "birthdate"]
    if sort_by not in valid_sort_fields:
        raise create_validation_error(
            f"Invalid sort field. Must be one of: "
            f"{', '.join(valid_sort_fields)}",
            field="sort_by",
        )

    if sort_order.lower() not in ["asc", "desc"]:
        raise create_validation_error(
            "Invalid sort order. Must be 'asc' or 'desc'",
            field="sort_order",
        )

    # Build query
    statement = select(Player).where(Player.team_id == team_id)

    # Apply filters
    if position:
        statement = statement.where(Player.position == position)
    if hand:
        statement = statement.where(Player.hand == hand)
    if birth_year:
        # Filter by birth year using string matching on date
        from sqlalchemy import func

        statement = statement.where(
            func.strftime("%Y", Player.birthdate) == str(birth_year)
        )

    # Apply sorting
    from typing import Any

    if sort_by == "name":
        order_field: Any = Player.name
    elif sort_by == "position":
        order_field = Player.position
    elif sort_by == "jersey":
        order_field = Player.jersey
    elif sort_by == "birthdate":
        order_field = Player.birthdate
    else:
        order_field = Player.name  # Default fallback

    if sort_order.lower() == "desc":
        statement = statement.order_by(order_field.desc())
    else:
        statement = statement.order_by(order_field.asc())

    players = session.exec(statement).all()
    return list(players)


@router.post(
    "/teams/{team_id}/players",
    response_model=PlayerOut,
    status_code=status.HTTP_201_CREATED,
)
@handle_service_errors
async def create_player(
    team_id: int,
    player_data: PlayerIn,
    session: Session = Depends(get_session),
) -> Player:
    """Create a new player for a team."""
    # Verify team exists
    team = session.get(Team, team_id)
    if not team:
        raise create_not_found_error("Team", team_id)

    # Validate player data
    try:
        validated_data = validate_player_data(player_data.model_dump())
    except ValidatorError as e:
        raise create_validation_error(str(e)) from e

    # Create new player
    player = Player(
        team_id=team_id,
        name=validated_data["name"],
        position=validated_data["position"],
        jersey=validated_data.get("jersey"),
        hand=validated_data.get("hand"),
        birthdate=validated_data.get("birthdate"),
        email=validated_data.get("email"),
        phone=validated_data.get("phone"),
        status=validated_data.get("status", "Active"),
    )

    session.add(player)
    session.commit()
    session.refresh(player)

    return player


@router.put("/players/{player_id}", response_model=PlayerOut)
@handle_service_errors
async def update_player(
    player_id: int,
    player_data: PlayerUpdate,
    session: Session = Depends(get_session),
) -> Player:
    """Update a player."""
    player = session.get(Player, player_id)
    if not player:
        raise create_not_found_error("Player", player_id)

    # Validate update data
    try:
        validated_data = validate_player_data(
            player_data.model_dump(exclude_unset=True)
        )
    except ValidatorError as e:
        raise create_validation_error(str(e)) from e

    # Update only provided fields
    for field, value in validated_data.items():
        setattr(player, field, value)

    session.add(player)
    session.commit()
    session.refresh(player)

    return player


@router.delete("/players/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def delete_player(
    player_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete a player."""
    player = session.get(Player, player_id)
    if not player:
        raise create_not_found_error("Player", player_id)

    session.delete(player)
    session.commit()


@router.post("/teams/{team_id}/players/import_csv", response_model=None)
@handle_service_errors
async def import_players_csv(
    team_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Import players from CSV file."""
    # Verify team exists
    team = session.get(Team, team_id)
    if not team:
        raise create_not_found_error("Team", team_id)

    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise create_validation_error("File must be a CSV file")

    try:
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')

        # Import players
        result = CSVService.import_players(session, team_id, csv_content)

        return result.to_dict()

    except UnicodeDecodeError as e:
        raise create_validation_error("File must be UTF-8 encoded") from e
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Import failed: {str(e)}") from e


@router.get("/teams/{team_id}/players/export_csv")
@handle_service_errors
async def export_players_csv(
    team_id: int,
    session: Session = Depends(get_session),
) -> Response:
    """Export players to CSV file."""
    # Verify team exists
    team = session.get(Team, team_id)
    if not team:
        raise create_not_found_error("Team", team_id)

    try:
        # Export players
        csv_content = CSVService.export_players(session, team_id)

        # Create response
        response = Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; "
                f"filename={team.name}_players.csv"
            }
        )

        return response

    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Export failed: {str(e)}") from e


@router.get("/players/{player_id}", response_model=PlayerOut)
@handle_service_errors
async def get_player(
    player_id: int,
    session: Session = Depends(get_session),
) -> Player:
    """Get a single player by ID."""
    player = session.get(Player, player_id)
    if not player:
        raise create_not_found_error("Player", player_id)

    return player
