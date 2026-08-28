"""Structured error handling for Clawforge."""

from typing import Any


class ClawforgeError(Exception):
    """Base exception for Clawforge errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
        status_code: int = 500,
    ):
        """Initialize ClawforgeError.

        Args:
            message: Human-readable error message.
            code: Machine-readable error code.
            details: Additional error context.
            status_code: HTTP status code.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(ClawforgeError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
            status_code=400,
        )


class NotFoundError(ClawforgeError):
    """Raised when a resource is not found."""

    def __init__(
        self,
        resource: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=f"{resource} '{resource_id}' not found",
            code="NOT_FOUND",
            details={"resource": resource, "id": resource_id, **(details or {})},
            status_code=404,
        )


class AuthenticationError(ClawforgeError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details,
            status_code=401,
        )


class AuthorizationError(ClawforgeError):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            details=details,
            status_code=403,
        )


class RateLimitError(ClawforgeError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details={"retry_after": retry_after, **(details or {})},
            status_code=429,
        )


class ConflictError(ClawforgeError):
    """Raised when a resource conflict occurs."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            details=details,
            status_code=409,
        )


class ExternalServiceError(ClawforgeError):
    """Raised when an external service call fails."""

    def __init__(
        self,
        service: str,
        message: str = "External service error",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=f"{service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})},
            status_code=502,
        )


class CryptoError(ClawforgeError):
    """Raised when cryptographic operations fail."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="CRYPTO_ERROR",
            details=details,
            status_code=500,
        )
