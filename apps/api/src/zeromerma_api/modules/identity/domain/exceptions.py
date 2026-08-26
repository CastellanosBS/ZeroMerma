class IdentityError(Exception):
    """Base error for the identity module."""


class InvalidCredentialsError(IdentityError):
    """Raised when login credentials are invalid."""


class AuthenticationError(IdentityError):
    """Raised when a bearer token is invalid or expired."""


class UserAdminError(IdentityError):
    """Base error for administrative user management."""


class UserNotFoundError(UserAdminError):
    """Raised when an administrative user lookup cannot find the user."""


class UserConflictError(UserAdminError):
    """Raised when an administrative user command conflicts with account rules."""


class UserValidationError(UserAdminError):
    """Raised when an administrative user command violates account rules."""


class RoleAdminError(IdentityError):
    """Base error for administrative role and permission management."""


class RoleNotFoundError(RoleAdminError):
    """Raised when an administrative role lookup cannot find the role."""


class RoleConflictError(RoleAdminError):
    """Raised when an administrative role command conflicts with access rules."""


class RoleValidationError(RoleAdminError):
    """Raised when an administrative role command violates access-control rules."""
