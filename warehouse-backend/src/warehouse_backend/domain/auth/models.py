from dataclasses import dataclass, field
from enum import StrEnum


class DepartmentRole(StrEnum):
    ADMIN = "dept_admin"
    INGESTOR = "dept_ingestor"
    ANALYST = "dept_analyst"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Domain model representing an authenticated identity with verified RBAC roles and groups."""

    user_id: str
    username: str
    email: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    groups: tuple[str, ...] = field(default_factory=tuple)
    departments: frozenset[str] = field(default_factory=frozenset)

    def has_role(self, role: str | DepartmentRole) -> bool:
        role_value = role.value if isinstance(role, DepartmentRole) else role
        return role_value in self.roles

    def has_any_role(self, *roles: str | DepartmentRole) -> bool:
        for r in roles:
            if self.has_role(r):
                return True
        return False

    def is_admin(self) -> bool:
        return self.has_role(DepartmentRole.ADMIN) or "admin" in self.roles

    def has_department(self, department_id: str) -> bool:
        normalized = department_id.strip().lower().replace("_", "-")
        return normalized in self.departments

    def can_access_department(self, department_id: str) -> bool:
        """Admins can access any department; other roles require explicit membership."""
        if self.is_admin():
            return True
        return self.has_department(department_id)
