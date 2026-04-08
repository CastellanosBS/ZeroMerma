class IdentityError(Exception):
    """Base error for the identity module."""


class InvalidCredentialsError(IdentityError):
    """Raised when login credentials are invalid."""


class AuthenticationError(IdentityError):
    """Raised when a bearer token is invalid or expired."""
