import pytest

from warehouse_backend.domain.auth.exceptions import (
    AuthError,
    DepartmentAccessDeniedError,
    ForbiddenAccessError,
    InvalidTokenError,
    MissingRoleError,
    TokenExpiredError,
)
from warehouse_backend.domain.auth.models import AuthenticatedUser, DepartmentRole


def test_authenticated_user_roles_and_departments() -> None:
    user = AuthenticatedUser(
        user_id="user-123",
        username="dr_garcia",
        email="garcia@club.internal",
        roles=frozenset({"dept_ingestor"}),
        groups=("/Departamentos/Medico",),
        departments=frozenset({"medico"}),
    )

    assert user.has_role(DepartmentRole.INGESTOR) is True
    assert user.has_role("dept_ingestor") is True
    assert user.has_role(DepartmentRole.ADMIN) is False
    assert user.has_any_role("dept_admin", "dept_ingestor") is True
    assert user.has_any_role("dept_analyst") is False
    assert user.is_admin() is False

    assert user.has_department("medico") is True
    assert user.has_department("MEDICO") is True  # case insensitive
    assert user.has_department("scouting") is False
    assert user.can_access_department("medico") is True
    assert user.can_access_department("scouting") is False


def test_admin_user_has_universal_department_access() -> None:
    admin = AuthenticatedUser(
        user_id="admin-1",
        username="admin_user",
        email="admin@club.internal",
        roles=frozenset({"dept_admin"}),
        groups=("/Departamentos/Direccion-Deportiva",),
        departments=frozenset({"direccion-deportiva"}),
    )

    assert admin.is_admin() is True
    assert admin.can_access_department("direccion-deportiva") is True
    assert admin.can_access_department("medico") is True
    assert admin.can_access_department("preparacion-fisica") is True
    assert admin.can_access_department("scouting") is True


def test_auth_exception_hierarchy() -> None:
    assert issubclass(InvalidTokenError, AuthError)
    assert issubclass(TokenExpiredError, InvalidTokenError)
    assert issubclass(ForbiddenAccessError, AuthError)
    assert issubclass(MissingRoleError, ForbiddenAccessError)
    assert issubclass(DepartmentAccessDeniedError, ForbiddenAccessError)

    with pytest.raises(AuthError):
        raise TokenExpiredError("Expired")
