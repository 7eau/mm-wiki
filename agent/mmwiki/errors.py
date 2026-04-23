class MMWikiError(Exception):
    """Base exception."""


class AuthenticationError(MMWikiError):
    """Raised when auth/session is invalid."""


class ApiError(MMWikiError):
    """Raised for remote API/HTML errors."""


class DriftError(MMWikiError):
    """Raised when local snapshot drifts from remote."""

