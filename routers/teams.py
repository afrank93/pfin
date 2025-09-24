from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import Team
from app.schemas import TeamIn, TeamOut

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("/", response_model=list[TeamOut])
async def list_teams(session: Session = Depends(get_session)) -> list[Team]:
    """List all teams."""
    statement = select(Team).order_by(Team.name, Team.season)
    teams = session.exec(statement).all()
    return list(teams)


@router.post("/", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamIn, session: Session = Depends(get_session)
) -> Team:
    """Create a new team."""
    # Check for duplicate name + season combination
    statement = select(Team).where(
        Team.name == team_data.name, Team.season == team_data.season
    )
    existing_team = session.exec(statement).first()

    if existing_team:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Team '{team_data.name}' already exists for season "
                f"'{team_data.season}'"
            ),
        )

    # Create new team
    team = Team(name=team_data.name, season=team_data.season)
    session.add(team)
    session.commit()
    session.refresh(team)

    return team


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: int, session: Session = Depends(get_session)
) -> Team:
    """Get a specific team by ID."""
    team = session.get(Team, team_id)
    if not team:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found",
        )
    return team
