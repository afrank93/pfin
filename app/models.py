from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel


class Position(str, Enum):
    """Player position enum."""
    F = "F"  # Forward
    D = "D"  # Defense
    G = "G"  # Goalie


class Hand(str, Enum):
    """Player handedness enum."""
    L = "L"  # Left
    R = "R"  # Right


class PlayerStatus(str, Enum):
    """Player status enum."""
    ACTIVE = "Active"
    AFFILIATE = "Affiliate"
    INJURED = "Injured"
    INACTIVE = "Inactive"


class SlotType(str, Enum):
    """Lineup slot type enum."""
    FWD = "FWD"  # Forward
    DEF = "DEF"  # Defense
    G = "G"      # Goalie


class Team(SQLModel, table=True):
    """Team model."""
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    season: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    players: list[Player] = Relationship(back_populates="team")
    lineup_templates: list[LineupTemplate] = Relationship(back_populates="team")
    
    class Config:
        # Ensure unique constraint on name + season
        __table_args__ = (
            {"sqlite_autoincrement": True},
        )


class Player(SQLModel, table=True):
    """Player model."""
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    name: str = Field(index=True)
    position: Position
    jersey: int | None = Field(default=None, ge=1, le=99)
    hand: Hand | None = Field(default=None)
    birthdate: date | None = Field(default=None)
    email: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    status: PlayerStatus = Field(default=PlayerStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    team: Team = Relationship(back_populates="players")
    lineup_slots: list[LineupSlot] = Relationship(back_populates="player")
    
    class Config:
        __table_args__ = (
            {"sqlite_autoincrement": True},
        )


class LineupTemplate(SQLModel, table=True):
    """Lineup template model."""
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    name: str = Field(index=True)
    notes: str | None = Field(default=None)
    date_saved: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    team: Team = Relationship(back_populates="lineup_templates")
    slots: list[LineupSlot] = Relationship(back_populates="template")
    
    class Config:
        __table_args__ = (
            {"sqlite_autoincrement": True},
        )


class LineupSlot(SQLModel, table=True):
    """Lineup slot model."""
    id: int | None = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="lineuptemplate.id", index=True)
    slot_type: SlotType
    slot_label: str
    order_index: int
    player_id: int | None = Field(default=None, foreign_key="player.id", index=True)
    
    # Relationships
    template: LineupTemplate = Relationship(back_populates="slots")
    player: Player | None = Relationship(back_populates="lineup_slots")
    
    class Config:
        __table_args__ = (
            {"sqlite_autoincrement": True},
        )
