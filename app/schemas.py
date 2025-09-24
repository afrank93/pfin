from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from .models import Hand, PlayerStatus, Position, SlotType


class TeamIn(BaseModel):
    """Input schema for creating a team."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Team name"
    )
    season: str = Field(
        ..., min_length=1, max_length=50, description="Season identifier"
    )


class TeamOut(BaseModel):
    """Output schema for team data."""

    id: int
    name: str
    season: str
    created_at: datetime

    class Config:
        from_attributes = True


class PlayerIn(BaseModel):
    """Input schema for creating a player."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Player name"
    )
    position: Position = Field(..., description="Player position")
    jersey: int | None = Field(
        None, ge=1, le=99, description="Jersey number (1-99)"
    )
    hand: Hand | None = Field(None, description="Player handedness")
    birthdate: date | None = Field(None, description="Player birthdate")
    email: str | None = Field(
        None, max_length=255, description="Player email"
    )
    phone: str | None = Field(
        None, max_length=20, description="Player phone number"
    )
    status: PlayerStatus = Field(
        PlayerStatus.ACTIVE, description="Player status"
    )


class PlayerOut(BaseModel):
    """Output schema for player data."""

    id: int
    team_id: int
    name: str
    position: Position
    jersey: int | None
    hand: Hand | None
    birthdate: date | None
    email: str | None
    phone: str | None
    status: PlayerStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PlayerUpdate(BaseModel):
    """Input schema for updating a player."""

    name: str | None = Field(None, min_length=1, max_length=100)
    position: Position | None = None
    jersey: int | None = Field(None, ge=1, le=99)
    hand: Hand | None = None
    birthdate: date | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    status: PlayerStatus | None = None


class LineupTemplateIn(BaseModel):
    """Input schema for creating a lineup template."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Template name"
    )
    notes: str | None = Field(
        None, max_length=500, description="Optional notes"
    )


class LineupTemplateOut(BaseModel):
    """Output schema for lineup template data."""

    id: int
    team_id: int
    name: str
    notes: str | None
    date_saved: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class LineupSlotOut(BaseModel):
    """Output schema for lineup slot data."""

    id: int
    template_id: int
    slot_type: SlotType
    slot_label: str
    order_index: int
    player_id: int | None

    class Config:
        from_attributes = True


class LineupSlotWithPlayerOut(BaseModel):
    """Output schema for lineup slot with player data."""

    id: int
    template_id: int
    slot_type: SlotType
    slot_label: str
    order_index: int
    player_id: int | None
    player: PlayerOut | None = None

    class Config:
        from_attributes = True


class LineupDetailOut(BaseModel):
    """Output schema for detailed lineup with slots and players."""

    template: LineupTemplateOut
    slots: list[LineupSlotWithPlayerOut]


class SlotAssignmentIn(BaseModel):
    """Input schema for slot assignment."""

    slot_id: int
    player_id: int | None = None


class BulkSlotUpdateIn(BaseModel):
    """Input schema for bulk slot updates."""

    assignments: list[SlotAssignmentIn]
