class AuthError(Exception):
    """Base domain authentication and authorization error."""


class InvalidTokenError(AuthError):
    """Raised when an authentication token cannot be validated."""


class TokenExpiredError(InvalidTokenError):
    """Raised when an authentication token has expired."""


class ForbiddenAccessError(AuthError):
    """Raised when an authenticated entity lacks required permissions."""


class MissingRoleError(ForbiddenAccessError):
    """Raised when a required RBAC role is missing."""


class DepartmentAccessDeniedError(ForbiddenAccessError):
    """Raised when accessing a department resource without appropriate membership."""
