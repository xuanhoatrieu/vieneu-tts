"""
API Key endpoints — create, list, revoke.
"""
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DBSession
from app.core.security import generate_api_key
from app.models.api_key import APIKey
from app.schemas.auth import APIKeyCreateRequest, APIKeyCreateResponse, APIKeyResponse

router = APIRouter()


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(body: APIKeyCreateRequest, user: CurrentUser, db: DBSession):
    """
    Create a new API key. The full key is shown ONLY in this response.
    Store it securely — it cannot be retrieved again.
    """
    full_key, prefix, key_hash = generate_api_key()

    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=prefix,
        name=body.name,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyCreateResponse(
        id=api_key.id,
        key=full_key,
        name=api_key.name,
        key_prefix=prefix,
        created_at=api_key.created_at,
    )


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(user: CurrentUser, db: DBSession):
    """List all active API keys for the current user (key NOT shown)."""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == user.id, APIKey.is_active == True)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [APIKeyResponse.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(key_id: uuid.UUID, user: CurrentUser, db: DBSession):
    """Revoke (delete) an API key."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(api_key)
    await db.commit()
