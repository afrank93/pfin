from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class ServiceError(Exception):
    """Base service error class."""

    def __init__(
        self,
        message: str,
        error_code: str = "SERVICE_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ServiceError):
    """Validation error for business logic validation."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details or {},
        )
        if field:
            self.details["field"] = field


class NotFoundError(ServiceError):
    """Resource not found error."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        details: dict[str, Any] | None = None,
    ):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            message=message, error_code="NOT_FOUND", details=details or {}
        )
        self.details["resource_type"] = resource_type
        self.details["resource_id"] = resource_id


class ConflictError(ServiceError):
    """Resource conflict error (e.g., duplicate)."""

    def __init__(
        self,
        message: str,
        conflicting_field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code="CONFLICT", details=details or {}
        )
        if conflicting_field:
            self.details["conflicting_field"] = conflicting_field


def service_error_to_http_exception(error: ServiceError) -> HTTPException:
    """Convert ServiceError to appropriate HTTPException."""

    if isinstance(error, ValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": error.error_code,
                "message": error.message,
                "details": error.details,
            },
        )

    elif isinstance(error, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": error.error_code,
                "message": error.message,
                "details": error.details,
            },
        )

    elif isinstance(error, ConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": error.error_code,
                "message": error.message,
                "details": error.details,
            },
        )

    else:
        # Generic service error
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": error.error_code,
                "message": error.message,
                "details": error.details,
            },
        )


def handle_service_errors(func):
    """Decorator to handle ServiceError exceptions and convert to HTTPException."""  # noqa: E501
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ServiceError as e:
            raise service_error_to_http_exception(e) from e

    return wrapper


def create_validation_error(
    message: str, field: str | None = None
) -> ValidationError:
    """Helper to create validation errors."""
    return ValidationError(message=message, field=field)


def create_not_found_error(
    resource_type: str, resource_id: Any
) -> NotFoundError:
    """Helper to create not found errors."""
    return NotFoundError(
        resource_type=resource_type, resource_id=resource_id
    )


def create_conflict_error(
    message: str, conflicting_field: str | None = None
) -> ConflictError:
    """Helper to create conflict errors."""
    return ConflictError(
        message=message, conflicting_field=conflicting_field
    )
