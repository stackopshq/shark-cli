"""Custom exceptions for orca."""

import click


class OrcaCLIError(click.ClickException):
    """Base exception for all orca errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class AuthenticationError(OrcaCLIError):
    """Raised when API authentication fails (HTTP 401/403)."""

    def __init__(self, message: str = "Authentication failed. Run 'orca setup' to configure your API key.") -> None:
        super().__init__(message)


_HTTP_FRIENDLY = {
    400: "Bad request",
    404: "Not found",
    409: "Conflict",
    413: "Request too large",
    415: "Unsupported media type",
    422: "Unprocessable entity",
    429: "Too many requests",
    500: "Internal server error",
    502: "Bad gateway",
    503: "Service unavailable",
}


class APIError(OrcaCLIError):
    """Raised when the OpenStack API returns an unexpected error."""

    def __init__(self, status_code: int, detail: str = "") -> None:
        self.status_code = status_code
        label = _HTTP_FRIENDLY.get(status_code, f"HTTP {status_code}")
        msg = f"{label} ({status_code})"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class ConfigurationError(OrcaCLIError):
    """Raised when the CLI configuration is missing or invalid."""

    def __init__(self, message: str = "Configuration not found. Run 'orca setup' first.") -> None:
        super().__init__(message)
