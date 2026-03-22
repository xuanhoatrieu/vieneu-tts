"""
FastAPI dependencies for authentication and database.
Supports both JWT Bearer token and X-API-Key header.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token, hash_api_key


security = HTTPBearer(auto_error=False)

# Type alias for DB session dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user from JWT token OR X-API-Key header.

    Priority:
    1. Authorization: Bearer <jwt_token>
    2. X-API-Key: vneu_xxxxxxxxxxxxx
    """
    from app.models.user import User
    from app.models.api_key import APIKey
    from datetime import datetime, timezone

    # ─── Try JWT first ────────────────────────────
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user

    # ─── Try API Key ──────────────────────────────
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        key_hash = hash_api_key(api_key_header)
        result = await db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            # Update last_used_at
            api_key.last_used_at = datetime.now(timezone.utc)
            await db.commit()

            # Get the user
            result = await db.execute(select(User).where(User.id == api_key.user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user

    # ─── No valid auth found ──────────────────────
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(user=Depends(get_current_user)):
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type aliases for dependency injection
CurrentUser = Annotated[object, Depends(get_current_user)]
AdminUser = Annotated[object, Depends(require_admin)]
