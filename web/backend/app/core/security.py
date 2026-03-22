"""
Security utilities — JWT tokens, password hashing, API key generation.
"""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password ─────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Token ────────────────────────────────────

def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode a JWT access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ─── API Key ──────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.
    Returns: (full_key, key_prefix, key_hash)
    """
    raw = secrets.token_urlsafe(32)
    full_key = f"vneu_{raw}"
    prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()
