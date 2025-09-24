from __future__ import annotations

from datetime import date
from typing import Any


class ValidationError(Exception):
    """Custom validation error for business logic validation."""

    pass


def validate_jersey_number(jersey: int | None) -> int | None:
    """Validate jersey number is in valid range (1-99)."""
    if jersey is None:
        return None

    if not isinstance(jersey, int):
        raise ValidationError("Jersey number must be an integer")

    if jersey < 1 or jersey > 99:
        raise ValidationError("Jersey number must be between 1 and 99")

    return jersey


def validate_iso_date(date_str: str | None) -> date | None:
    """Validate and parse ISO date string (YYYY-MM-DD)."""
    if not date_str:
        return None

    if not isinstance(date_str, str):
        raise ValidationError("Date must be a string")

    try:
        # Parse ISO date format
        parsed_date = date.fromisoformat(date_str)
        return parsed_date
    except ValueError as e:
        raise ValidationError(
            f"Invalid date format. Expected YYYY-MM-DD: {e}"
        ) from e


def validate_birth_year(birth_year: int | None) -> int | None:
    """Validate birth year is reasonable (1900-2024)."""
    if birth_year is None:
        return None

    if not isinstance(birth_year, int):
        raise ValidationError("Birth year must be an integer")

    current_year = date.today().year
    if birth_year < 1900 or birth_year > current_year:
        raise ValidationError(
            f"Birth year must be between 1900 and {current_year}"
        )

    return birth_year


def validate_email_format(email: str | None) -> str | None:
    """Basic email format validation."""
    if not email:
        return None

    if not isinstance(email, str):
        raise ValidationError("Email must be a string")

    # Basic email validation - contains @ and has reasonable length
    if "@" not in email or len(email) < 5 or len(email) > 255:
        raise ValidationError("Invalid email format")

    # Check for basic structure
    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValidationError("Invalid email format")

    if "." not in parts[1]:
        raise ValidationError("Invalid email format")

    return email


def validate_phone_format(phone: str | None) -> str | None:
    """Basic phone number format validation."""
    if not phone:
        return None

    if not isinstance(phone, str):
        raise ValidationError("Phone must be a string")

    # Remove common separators and check if all digits
    clean_phone = "".join(c for c in phone if c.isdigit())

    if len(clean_phone) < 10 or len(clean_phone) > 15:
        raise ValidationError("Phone number must be 10-15 digits")

    return phone


def validate_player_data(data: dict[str, Any]) -> dict[str, Any]:
    """Validate player data and return cleaned data."""
    cleaned_data = data.copy()

    # Validate jersey number
    if "jersey" in cleaned_data:
        try:
            cleaned_data["jersey"] = validate_jersey_number(
                cleaned_data["jersey"]
            )
        except ValidationError as e:
            raise ValidationError(f"Jersey validation failed: {e}") from e

    # Validate birthdate
    if "birthdate" in cleaned_data:
        try:
            if isinstance(cleaned_data["birthdate"], str):
                cleaned_data["birthdate"] = validate_iso_date(
                    cleaned_data["birthdate"]
                )
        except ValidationError as e:
            raise ValidationError(f"Birthdate validation failed: {e}") from e

    # Validate email
    if "email" in cleaned_data:
        try:
            cleaned_data["email"] = validate_email_format(
                cleaned_data["email"]
            )
        except ValidationError as e:
            raise ValidationError(f"Email validation failed: {e}") from e

    # Validate phone
    if "phone" in cleaned_data:
        try:
            cleaned_data["phone"] = validate_phone_format(
                cleaned_data["phone"]
            )
        except ValidationError as e:
            raise ValidationError(f"Phone validation failed: {e}") from e

    return cleaned_data
