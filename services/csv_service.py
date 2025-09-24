"""CSV import/export service for players."""

from __future__ import annotations

import csv
import io
import tempfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.models import Hand, Player, PlayerStatus, Position
from utils.errors import ServiceError


class CSVImportResult:
    """Result of CSV import operation."""

    def __init__(self) -> None:
        self.imported: int = 0
        self.skipped: int = 0
        self.errors: list[dict[str, Any]] = []
        self.issues_file_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "imported": self.imported,
            "skipped": self.skipped,
            "errors": self.errors,
            "issues_file_path": self.issues_file_path,
        }


class CSVService:
    """Service for CSV import/export operations."""

    # Expected CSV headers
    EXPECTED_HEADERS = [
        "name",
        "position",
        "jersey",
        "hand",
        "birthdate",
        "email",
        "phone",
        "status",
    ]

    # Optional headers (can be empty)
    OPTIONAL_HEADERS = {"jersey", "hand", "birthdate", "email", "phone"}

    @classmethod
    def import_players(
        cls, session: Session, team_id: int, csv_content: str
    ) -> CSVImportResult:
        """
        Import players from CSV content.

        Args:
            session: Database session
            team_id: Team ID to import players to
            csv_content: CSV file content as string

        Returns:
            CSVImportResult with import statistics and errors
        """
        result = CSVImportResult()

        try:
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            # Validate headers
            if not csv_reader.fieldnames:
                raise ServiceError("CSV file is empty or invalid")

            missing_headers = set(cls.EXPECTED_HEADERS) - set(
                csv_reader.fieldnames
            )
            if missing_headers:
                raise ServiceError(
                    f"Missing required headers: "
                    f"{', '.join(missing_headers)}"
                )

            # Process each row
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    player_data = cls._parse_player_row(row, team_id)
                    cls._validate_player_data(player_data)

                    # Check for duplicates
                    existing_player = cls._find_duplicate_player(
                        session, player_data
                    )
                    if existing_player:
                        result.errors.append({
                            "row": row_num,
                            "field": "name",
                            "reason": f"Duplicate player: "
                            f"{player_data['name']}",
                            "value": player_data["name"]
                        })
                        result.skipped += 1
                        continue

                    # Create player
                    player = Player(**player_data)
                    session.add(player)
                    result.imported += 1

                except Exception as e:
                    result.errors.append({
                        "row": row_num,
                        "field": "general",
                        "reason": str(e),
                        "value": str(row)
                    })
                    result.skipped += 1

            # Commit all valid players
            if result.imported > 0:
                session.commit()

            # Create issues file if there are errors
            if result.errors:
                result.issues_file_path = cls._create_issues_file(
                    result.errors
                )

        except Exception as e:
            session.rollback()
            raise ServiceError(f"CSV import failed: {str(e)}") from e

        return result

    @classmethod
    def export_players(cls, session: Session, team_id: int) -> str:
        """
        Export players to CSV format.

        Args:
            session: Database session
            team_id: Team ID to export players from

        Returns:
            CSV content as string
        """
        try:
            # Get players for the team
            statement = select(Player).where(Player.team_id == team_id)
            players = session.exec(statement).all()

            # Create CSV content
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=cls.EXPECTED_HEADERS)
            writer.writeheader()

            for player in players:
                row = {
                    "name": player.name,
                    "position": player.position.value,
                    "jersey": player.jersey or "",
                    "hand": player.hand.value if player.hand else "",
                    "birthdate": (
                        player.birthdate.strftime("%Y-%m-%d")
                        if player.birthdate else ""
                    ),
                    "email": player.email or "",
                    "phone": player.phone or "",
                    "status": player.status.value,
                }
                writer.writerow(row)

            return output.getvalue()

        except Exception as e:
            raise ServiceError(
                f"CSV export failed: {str(e)}"
            ) from e

    @classmethod
    def _parse_player_row(
        cls, row: dict[str, str], team_id: int
    ) -> dict[str, Any]:
        """Parse a single CSV row into player data."""
        player_data = {
            "team_id": team_id,
            "name": row["name"].strip(),
            "position": row["position"].strip().upper(),
        }

        # Parse optional fields
        if row.get("jersey", "").strip():
            try:
                player_data["jersey"] = int(row["jersey"].strip())
            except ValueError as e:
                raise ValueError("Invalid jersey number") from e

        if row.get("hand", "").strip():
            hand_value = row["hand"].strip().upper()
            if hand_value in ["L", "LEFT"]:
                player_data["hand"] = Hand.L
            elif hand_value in ["R", "RIGHT"]:
                player_data["hand"] = Hand.R
            else:
                raise ValueError(
                    "Invalid hand value (must be L/Left or R/Right)"
                )

        if row.get("birthdate", "").strip():
            try:
                birthdate_str = row["birthdate"].strip()
                # Try different date formats
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        player_data["birthdate"] = datetime.strptime(
                            birthdate_str, fmt
                        ).date()
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("Invalid date format")
            except ValueError as e:
                raise ValueError(f"Invalid birthdate: {str(e)}") from e

        if row.get("email", "").strip():
            player_data["email"] = row["email"].strip()

        if row.get("phone", "").strip():
            player_data["phone"] = row["phone"].strip()

        if row.get("status", "").strip():
            status_value = row["status"].strip()
            # Map common status variations
            status_map = {
                "ACTIVE": PlayerStatus.ACTIVE,
                "AFFILIATE": PlayerStatus.AFFILIATE,
                "INJURED": PlayerStatus.INJURED,
                "INACTIVE": PlayerStatus.INACTIVE,
                "ACT": PlayerStatus.ACTIVE,
                "AFF": PlayerStatus.AFFILIATE,
                "INJ": PlayerStatus.INJURED,
                "INA": PlayerStatus.INACTIVE,
            }
            player_data["status"] = status_map.get(
                status_value.upper(), PlayerStatus.ACTIVE
            )

        return player_data

    @classmethod
    def _validate_player_data(cls, player_data: dict[str, Any]) -> None:
        """Validate parsed player data."""
        # Required fields
        if not player_data.get("name"):
            raise ValueError("Name is required")

        # Validate position
        try:
            Position(player_data["position"])
        except ValueError as e:
            raise ValueError(
                f"Invalid position: {player_data['position']}"
            ) from e

        # Validate jersey number
        if ("jersey" in player_data and player_data["jersey"] is not None
                and not (1 <= player_data["jersey"] <= 99)):
            raise ValueError(
                "Jersey number must be between 1 and 99"
            )

        # Validate email format (basic)
        if "email" in player_data and player_data["email"]:
            email = player_data["email"]
            if "@" not in email or "." not in email.split("@")[1]:
                raise ValueError("Invalid email format")

        # Validate phone format (basic)
        if "phone" in player_data and player_data["phone"]:
            phone = player_data["phone"]
            # Remove common phone formatting characters
            clean_phone = "".join(c for c in phone if c.isdigit())
            if len(clean_phone) < 10:
                raise ValueError("Phone number too short")

    @classmethod
    def _find_duplicate_player(
        cls, session: Session, player_data: dict[str, Any]
    ) -> Player | None:
        """Find existing player with same name and team."""
        statement = select(Player).where(
            Player.team_id == player_data["team_id"],
            Player.name == player_data["name"]
        )
        return session.exec(statement).first()

    @classmethod
    def _create_issues_file(cls, errors: list[dict[str, Any]]) -> str | None:
        """Create a CSV file with import issues."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False
            ) as temp_file:
                writer = csv.DictWriter(
                    temp_file, fieldnames=["row", "field", "reason", "value"]
                )
                writer.writeheader()
                writer.writerows(errors)
                return temp_file.name

        except Exception:
            # If we can't create the issues file, just return None
            return None

    @classmethod
    def get_issues_file_content(cls, file_path: str) -> str:
        """Get content of issues file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    @classmethod
    def cleanup_issues_file(cls, file_path: str) -> None:
        """Clean up temporary issues file."""
        with suppress(Exception):
            Path(file_path).unlink(missing_ok=True)
