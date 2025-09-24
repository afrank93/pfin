"""PDF service for generating lineup PDFs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from app.models import Player, Team
from services.lineup_service import LineupService
from utils.errors import ServiceError


class PDFService:
    """Service for PDF generation operations."""

    @classmethod
    def generate_lineup_pdf(
        cls,
        session: Session,
        template_id: int,
        request: Request,
    ) -> Response:
        """
        Generate a PDF for a lineup template.

        Args:
            session: Database session
            template_id: Template ID
            request: FastAPI request object for URL generation

        Returns:
            Response with PDF content
        """
        try:
            # Get lineup template with slots and players
            template, slots = LineupService.get_lineup_with_slots(
                session, template_id
            )

            # Get team information
            team = session.get(Team, template.team_id)
            if not team:
                raise ServiceError(
                    f"Team with ID {template.team_id} not found"
                )

            # Get player information for assigned slots
            slots_with_players = []
            for slot in slots:
                slot_dict = {
                    "id": slot.id,
                    "template_id": slot.template_id,
                    "slot_type": slot.slot_type,
                    "slot_label": slot.slot_label,
                    "order_index": slot.order_index,
                    "player_id": slot.player_id,
                    "player": None,
                }

                if slot.player_id:
                    player = session.get(Player, slot.player_id)
                    if player:
                        slot_dict["player"] = {
                            "id": player.id,
                            "name": player.name,
                            "position": player.position,
                            "jersey": player.jersey,
                            "hand": player.hand,
                            "status": player.status,
                        }

                slots_with_players.append(slot_dict)

            # Organize slots by type for template rendering
            slots_by_type = cls._organize_slots_by_type(slots_with_players)

            # Prepare template context
            context = {
                "template": {
                    "id": template.id,
                    "name": template.name,
                    "notes": template.notes,
                    "date_saved": template.date_saved,
                },
                "team": {
                    "id": team.id,
                    "name": team.name,
                    "season": team.season,
                },
                "slots": slots_with_players,
                "slots_by_type": slots_by_type,
                "now": datetime.utcnow(),
            }

            # Render HTML template
            html_content = cls._render_pdf_template(context)

            # Generate PDF
            pdf_content = cls._html_to_pdf(html_content)

            # Create response
            response = Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename="
                        f"{team.name.replace(' ', '_')}_"
                        f"{template.name.replace(' ', '_')}_lineup.pdf"
                    )
                },
            )

            return response

        except ServiceError as e:
            raise e
        except Exception as e:
            raise ServiceError(f"PDF generation failed: {str(e)}") from e

    @classmethod
    def _organize_slots_by_type(
        cls, slots: list[dict[str, Any]]
    ) -> dict[str, list[list[dict[str, Any]]]]:
        """
        Organize slots by type and line/pair for template rendering.

        Args:
            slots: List of slot dictionaries with player information

        Returns:
            Dictionary organized by slot type and line/pair
        """
        organized = {"FWD": [], "DEF": [], "G": []}

        # Group by slot type
        fwd_slots = [s for s in slots if s["slot_type"] == "FWD"]
        def_slots = [s for s in slots if s["slot_type"] == "DEF"]
        g_slots = [s for s in slots if s["slot_type"] == "G"]

        # Organize forwards by line (4 lines, 3 positions each)
        for line_num in range(1, 5):
            line_slots = [
                s
                for s in fwd_slots
                if s["slot_label"].startswith(f"FWD{line_num}")
            ]
            # Sort by order_index to get LW, C, RW
            line_slots.sort(key=lambda x: x["order_index"])
            organized["FWD"].append(line_slots)

        # Organize defense by pair (3 pairs, 2 positions each)
        for pair_num in range(1, 4):
            pair_slots = [
                s
                for s in def_slots
                if s["slot_label"].startswith(f"DEF{pair_num}")
            ]
            # Sort by order_index to get L, R
            pair_slots.sort(key=lambda x: x["order_index"])
            organized["DEF"].append(pair_slots)

        # Organize goalies (2 slots: Starter, Backup)
        g_slots.sort(key=lambda x: x["order_index"])
        organized["G"] = g_slots

        return organized

    @classmethod
    def _render_pdf_template(cls, context: dict[str, Any]) -> str:
        """
        Render the PDF template with the given context.

        Args:
            context: Template context dictionary

        Returns:
            Rendered HTML content
        """
        try:
            # Setup Jinja2 environment
            env = Environment(
                loader=FileSystemLoader("templates"),
                autoescape=True,
            )

            # Load and render template
            template = env.get_template("pdf_lineup.html")
            html_content = template.render(**context)

            return html_content

        except Exception as e:
            raise ServiceError(f"Template rendering failed: {str(e)}") from e

    @classmethod
    def _html_to_pdf(cls, html_content: str) -> bytes:
        """
        Convert HTML content to PDF bytes.

        Args:
            html_content: HTML content as string

        Returns:
            PDF content as bytes
        """
        try:
            # Configure font handling
            font_config = FontConfiguration()

            # Create HTML object
            html_doc = HTML(string=html_content)

            # Generate PDF
            pdf_bytes = html_doc.write_pdf(font_config=font_config)

            return pdf_bytes

        except Exception as e:
            raise ServiceError(f"PDF conversion failed: {str(e)}") from e

    @classmethod
    def validate_lineup_for_pdf(
        cls, session: Session, template_id: int
    ) -> dict[str, Any]:
        """
        Validate that a lineup is ready for PDF generation.

        Args:
            session: Database session
            template_id: Template ID

        Returns:
            Dictionary with validation results
        """
        try:
            template, slots = LineupService.get_lineup_with_slots(
                session, template_id
            )

            # Count assigned players
            assigned_count = sum(
                1 for slot in slots if slot.player_id is not None
            )
            total_slots = len(slots)

            # Check for minimum required players
            min_players = 12  # 4 forward lines (3 each) = 12 minimum
            has_minimum = assigned_count >= min_players

            # Check for goalies
            goalie_slots = [s for s in slots if s.slot_type.value == "G"]
            assigned_goalies = sum(
                1 for slot in goalie_slots if slot.player_id is not None
            )
            has_goalies = assigned_goalies > 0

            return {
                "valid": has_minimum and has_goalies,
                "assigned_count": assigned_count,
                "total_slots": total_slots,
                "has_minimum": has_minimum,
                "has_goalies": has_goalies,
                "assigned_goalies": assigned_goalies,
                "warnings": cls._generate_validation_warnings(
                    assigned_count, total_slots, assigned_goalies
                ),
            }

        except Exception as e:
            raise ServiceError(f"Lineup validation failed: {str(e)}") from e

    @classmethod
    def _generate_validation_warnings(
        cls, assigned_count: int, total_slots: int, assigned_goalies: int
    ) -> list[str]:
        """Generate validation warnings for the lineup."""
        warnings = []

        if assigned_count < 12:
            warnings.append(
                f"Only {assigned_count} players assigned "
                f"(minimum 12 recommended)"
            )

        if assigned_goalies == 0:
            warnings.append("No goalies assigned")

        if assigned_goalies == 1:
            warnings.append("Only 1 goalie assigned (2 recommended)")

        if assigned_count < total_slots * 0.8:
            empty_percent = (
                (total_slots - assigned_count) / total_slots * 100
            )
            warnings.append(f"Lineup is {empty_percent:.0f}% empty")

        return warnings
