"""Lineup service for managing lineup templates and slots."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.models import LineupSlot, LineupTemplate, Player, SlotType, Team
from utils.errors import ServiceError


class LineupService:
    """Service for lineup operations."""

    # Standard lineup configuration
    FORWARD_LINES = 4
    DEFENSE_PAIRS = 3
    GOALIE_SLOTS = 2

    @classmethod
    def create_lineup_template(
        cls,
        session: Session,
        team_id: int,
        name: str,
        notes: str | None = None,
    ) -> LineupTemplate:
        """
        Create a new lineup template with seeded slots.

        Args:
            session: Database session
            team_id: Team ID
            name: Template name
            notes: Optional notes

        Returns:
            Created LineupTemplate
        """
        # Verify team exists
        team = session.get(Team, team_id)
        if not team:
            raise ServiceError(f"Team with ID {team_id} not found")

        # Create template
        template = LineupTemplate(
            team_id=team_id,
            name=name,
            notes=notes
        )
        session.add(template)
        session.flush()  # Get the ID

        # Seed slots
        cls._seed_lineup_slots(session, template.id)

        session.commit()
        return template

    @classmethod
    def _seed_lineup_slots(cls, session: Session, template_id: int) -> None:
        """Seed lineup slots for a template."""
        slots = []

        # Forward lines (4 lines: LW, C, RW)
        for line_num in range(1, cls.FORWARD_LINES + 1):
            positions = ["LW", "C", "RW"]
            for pos_idx, position in enumerate(positions):
                slot = LineupSlot(
                    template_id=template_id,
                    slot_type=SlotType.FWD,
                    slot_label=f"FWD{line_num} {position}",
                    order_index=line_num * 10 + pos_idx
                )
                slots.append(slot)

        # Defense pairs (3 pairs: L, R)
        for pair_num in range(1, cls.DEFENSE_PAIRS + 1):
            positions = ["L", "R"]
            for pos_idx, position in enumerate(positions):
                slot = LineupSlot(
                    template_id=template_id,
                    slot_type=SlotType.DEF,
                    slot_label=f"DEF{pair_num} {position}",
                    order_index=100 + pair_num * 10 + pos_idx
                )
                slots.append(slot)

        # Goalies (2 slots: Starter, Backup)
        goalie_labels = ["Starter", "Backup"]
        for goalie_idx, label in enumerate(goalie_labels):
            slot = LineupSlot(
                template_id=template_id,
                slot_type=SlotType.G,
                slot_label=f"G {label}",
                order_index=200 + goalie_idx
            )
            slots.append(slot)

        # Add all slots to session
        for slot in slots:
            session.add(slot)

    @classmethod
    def assign_player_to_slot(
        cls,
        session: Session,
        slot_id: int,
        player_id: int | None = None
    ) -> dict[str, Any]:
        """
        Assign a player to a lineup slot.

        Args:
            session: Database session
            slot_id: Slot ID
            player_id: Player ID (None to clear slot)

        Returns:
            Dictionary with assignment result and warnings
        """
        # Get slot
        slot = session.get(LineupSlot, slot_id)
        if not slot:
            raise ServiceError(f"Slot with ID {slot_id} not found")

        # Get template and team
        template = session.get(LineupTemplate, slot.template_id)
        if not template:
            raise ServiceError(
                f"Template with ID {slot.template_id} not found"
            )

        warnings = []

        # If assigning a player
        if player_id is not None:
            # Get player
            player = session.get(Player, player_id)
            if not player:
                raise ServiceError(f"Player with ID {player_id} not found")

            # Validate team match
            if player.team_id != template.team_id:
                raise ServiceError(
                    "Player must be on the same team as the lineup template"
                )

            # Check for duplicates (player already in lineup)
            existing_slot = cls._find_player_in_lineup(
                session, template.id, player_id
            )
            if existing_slot and existing_slot.id != slot_id:
                warnings.append({
                    "type": "duplicate",
                    "message": (
                        f"Player {player.name} is already assigned to "
                        f"{existing_slot.slot_label}"
                    )
                })

            # Check player status
            if player.status.value != "Active":
                warnings.append({
                    "type": "status",
                    "message": (
                        f"Player {player.name} has status "
                        f"'{player.status.value}' (not Active)"
                    )
                })

            # Validate position compatibility
            if not cls._is_position_compatible(
                player.position.value, slot.slot_type.value
            ):
                warnings.append({
                    "type": "position",
                    "message": (
                        f"Player {player.name} is a {player.position.value} "
                        f"but slot is for {slot.slot_type.value}"
                    )
                })

        # Update slot
        slot.player_id = player_id
        session.commit()

        return {
            "success": True,
            "slot_id": slot_id,
            "player_id": player_id,
            "warnings": warnings
        }

    @classmethod
    def _find_player_in_lineup(
        cls, session: Session, template_id: int, player_id: int
    ) -> LineupSlot | None:
        """Find if a player is already assigned to any slot in the lineup."""
        statement = select(LineupSlot).where(
            LineupSlot.template_id == template_id,
            LineupSlot.player_id == player_id
        )
        return session.exec(statement).first()

    @classmethod
    def _is_position_compatible(
        cls, player_position: str, slot_type: str
    ) -> bool:
        """Check if player position is compatible with slot type."""
        # Forward players can go in FWD slots
        if player_position == "F" and slot_type == "FWD":
            return True
        # Defense players can go in DEF slots
        if player_position == "D" and slot_type == "DEF":
            return True
        # Goalies can go in G slots
        if player_position == "G" and slot_type == "G":
            return True
        return False

    @classmethod
    def get_lineup_with_slots(
        cls, session: Session, template_id: int
    ) -> tuple[LineupTemplate, list[LineupSlot]]:
        """
        Get lineup template with all its slots and player information.

        Args:
            session: Database session
            template_id: Template ID

        Returns:
            Tuple of (template, slots)
        """
        # Get template
        template = session.get(LineupTemplate, template_id)
        if not template:
            raise ServiceError(f"Template with ID {template_id} not found")

        # Get slots ordered by order_index
        statement = (
            select(LineupSlot)
            .where(LineupSlot.template_id == template_id)
            .order_by(LineupSlot.order_index)
        )
        slots = session.exec(statement).all()

        return template, list(slots)

    @classmethod
    def bulk_update_slots(
        cls,
        session: Session,
        template_id: int,
        slot_assignments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Bulk update slot assignments.

        Args:
            session: Database session
            template_id: Template ID
            slot_assignments: List of {slot_id, player_id} dictionaries

        Returns:
            Dictionary with update results and warnings
        """
        # Verify template exists
        template = session.get(LineupTemplate, template_id)
        if not template:
            raise ServiceError(f"Template with ID {template_id} not found")

        all_warnings = []
        updated_slots = []

        for assignment in slot_assignments:
            slot_id = assignment.get("slot_id")
            player_id = assignment.get("player_id")

            if slot_id is None:
                continue

            try:
                result = cls.assign_player_to_slot(session, slot_id, player_id)
                updated_slots.append(slot_id)
                all_warnings.extend(result["warnings"])
            except ServiceError as e:
                all_warnings.append({
                    "type": "error",
                    "message": f"Failed to update slot {slot_id}: {str(e)}"
                })

        session.commit()

        return {
            "success": True,
            "updated_slots": updated_slots,
            "warnings": all_warnings
        }

    @classmethod
    def save_lineup(cls, session: Session, template_id: int) -> LineupTemplate:
        """
        Mark lineup as saved by setting date_saved.

        Args:
            session: Database session
            template_id: Template ID

        Returns:
            Updated template
        """
        template = session.get(LineupTemplate, template_id)
        if not template:
            raise ServiceError(f"Template with ID {template_id} not found")

        from datetime import datetime
        template.date_saved = datetime.utcnow()
        session.commit()

        return template

    @classmethod
    def get_available_players(
        cls,
        session: Session,
        team_id: int,
        template_id: int | None = None,
    ) -> list[Player]:
        """
        Get players available for lineup assignment.

        Args:
            session: Database session
            team_id: Team ID
            template_id: Optional template ID to exclude already assigned
                players

        Returns:
            List of available players
        """
        # Get all team players
        statement = select(Player).where(Player.team_id == team_id)
        players = session.exec(statement).all()

        # If template_id provided, exclude already assigned players
        if template_id:
            assigned_player_ids = cls._get_assigned_player_ids(
                session, template_id
            )
            players = [p for p in players if p.id not in assigned_player_ids]

        return list(players)

    @classmethod
    def _get_assigned_player_ids(
        cls, session: Session, template_id: int
    ) -> set[int]:
        """Get set of player IDs already assigned to template slots."""
        statement = select(LineupSlot.player_id).where(
            LineupSlot.template_id == template_id,
            LineupSlot.player_id.is_not(None)
        )
        assigned_ids = session.exec(statement).all()
        return set(assigned_ids)
