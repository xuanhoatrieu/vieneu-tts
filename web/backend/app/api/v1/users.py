"""
User API endpoints — profile.
"""
from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(user: CurrentUser):
    """Get current user's profile."""
    return UserResponse.model_validate(user)
