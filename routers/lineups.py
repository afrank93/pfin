"""Lineup router for managing lineup templates and slots."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import LineupTemplate, Player
from app.schemas import (
    BulkSlotUpdateIn,
    LineupDetailOut,
    LineupTemplateIn,
    LineupTemplateOut,
    PlayerOut,
    SlotAssignmentIn,
)
from services.lineup_service import LineupService
from services.pdf_service import PDFService
from utils.errors import (
    ServiceError,
    handle_service_errors,
)

router = APIRouter(prefix="/api", tags=["lineups"])


@router.get("/teams/{team_id}/lineups", response_model=list[LineupTemplateOut])
@handle_service_errors
async def list_lineups(
    team_id: int,
    session: Session = Depends(get_session),
) -> list[LineupTemplate]:
    """List all lineup templates for a team."""
    statement = select(LineupTemplate).where(
        LineupTemplate.team_id == team_id
    ).order_by(LineupTemplate.created_at.desc())
    lineups = session.exec(statement).all()
    return list(lineups)


@router.post(
    "/teams/{team_id}/lineups",
    response_model=LineupTemplateOut,
    status_code=status.HTTP_201_CREATED,
)
@handle_service_errors
async def create_lineup(
    team_id: int,
    lineup_data: LineupTemplateIn,
    session: Session = Depends(get_session),
) -> LineupTemplate:
    """Create a new lineup template with seeded slots."""
    try:
        template = LineupService.create_lineup_template(
            session=session,
            team_id=team_id,
            name=lineup_data.name,
            notes=lineup_data.notes
        )
        return template
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Failed to create lineup: {str(e)}") from e


@router.get("/lineups/{template_id}", response_model=LineupDetailOut)
@handle_service_errors
async def get_lineup_detail(
    template_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get lineup template with all slots and player information."""
    try:
        template, slots = LineupService.get_lineup_with_slots(
            session, template_id
        )

        # Get player information for assigned slots
        slot_data = []
        for slot in slots:
            slot_dict = {
                "id": slot.id,
                "template_id": slot.template_id,
                "slot_type": slot.slot_type,
                "slot_label": slot.slot_label,
                "order_index": slot.order_index,
                "player_id": slot.player_id,
                "player": None
            }

            if slot.player_id:
                player = session.get(Player, slot.player_id)
                if player:
                    slot_dict["player"] = PlayerOut.model_validate(player)

            slot_data.append(slot_dict)

        return {
            "template": LineupTemplateOut.model_validate(template),
            "slots": slot_data
        }
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Failed to get lineup: {str(e)}") from e


@router.put("/lineups/{template_id}/slots")
@handle_service_errors
async def bulk_update_slots(
    template_id: int,
    update_data: BulkSlotUpdateIn,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Bulk update slot assignments."""
    try:
        result = LineupService.bulk_update_slots(
            session=session,
            template_id=template_id,
            slot_assignments=[
                assignment.model_dump()
                for assignment in update_data.assignments
            ]
        )
        return result
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Failed to update slots: {str(e)}") from e


@router.post("/lineups/{template_id}/save", response_model=LineupTemplateOut)
@handle_service_errors
async def save_lineup(
    template_id: int,
    session: Session = Depends(get_session),
) -> LineupTemplate:
    """Mark lineup as saved by setting date_saved."""
    try:
        template = LineupService.save_lineup(session, template_id)
        return template
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Failed to save lineup: {str(e)}") from e


@router.get(
    "/teams/{team_id}/lineups/{template_id}/available-players",
    response_model=list[PlayerOut]
)
@handle_service_errors
async def get_available_players(
    team_id: int,
    template_id: int,
    session: Session = Depends(get_session),
) -> list[Player]:
    """Get players available for lineup assignment."""
    try:
        players = LineupService.get_available_players(
            session=session,
            team_id=team_id,
            template_id=template_id
        )
        return players
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Failed to get available players: {str(e)}") from e


@router.put("/lineups/slots/{slot_id}")
@handle_service_errors
async def assign_player_to_slot(
    slot_id: int,
    assignment: SlotAssignmentIn,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Assign a player to a specific slot."""
    try:
        result = LineupService.assign_player_to_slot(
            session=session,
            slot_id=slot_id,
            player_id=assignment.player_id
        )
        return result
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Failed to assign player to slot: {str(e)}") from e


@router.get("/lineups/{template_id}/export_pdf")
@handle_service_errors
async def export_lineup_pdf(
    template_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> Response:
    """Export lineup template as PDF."""
    try:
        # Validate lineup before generating PDF
        validation = PDFService.validate_lineup_for_pdf(session, template_id)

        if not validation["valid"]:
            # Still allow PDF generation but show warnings
            pass

        # Generate PDF
        response = PDFService.generate_lineup_pdf(
            session=session,
            template_id=template_id,
            request=request
        )

        return response
    except ServiceError as e:
        raise e
    except Exception as e:
        raise ServiceError(f"Failed to export PDF: {str(e)}") from e
