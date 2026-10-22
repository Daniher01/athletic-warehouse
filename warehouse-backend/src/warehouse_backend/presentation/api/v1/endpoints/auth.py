from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from warehouse_backend.domain.auth.models import AuthenticatedUser
from warehouse_backend.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & IAM"])


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str | None
    roles: list[str]
    groups: list[str]
    departments: list[str]
    is_admin: bool


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserProfileResponse:
    """Return authenticated user profile, roles, and authorized departments."""
    return UserProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        roles=sorted(list(current_user.roles)),
        groups=list(current_user.groups),
        departments=sorted(list(current_user.departments)),
        is_admin=current_user.is_admin(),
    )
