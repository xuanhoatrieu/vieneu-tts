"""
Auth & User Pydantic schemas — request/response models.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ─── Auth Request/Response ────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ─── User ─────────────────────────────────────────

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdminUpdate(BaseModel):
    """Admin can update user role and status."""
    role: str | None = None
    is_active: bool | None = None


# ─── API Key ──────────────────────────────────────

class APIKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class APIKeyCreateResponse(BaseModel):
    """Returned only on creation — full key shown once."""
    id: uuid.UUID
    key: str
    name: str
    key_prefix: str
    created_at: datetime


class APIKeyResponse(BaseModel):
    """Returned on list — key NOT shown."""
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Forward reference resolution
TokenResponse.model_rebuild()
