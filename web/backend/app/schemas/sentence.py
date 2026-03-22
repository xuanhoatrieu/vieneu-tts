"""
Sentence Set and Sentence Pydantic schemas.
"""
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Sentence ─────────────────────────────────────

class SentenceResponse(BaseModel):
    id: int
    text: str
    order_index: int
    category: str | None = None

    model_config = {"from_attributes": True}


class SentenceCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    order_index: int = 0
    category: str | None = None


class SentenceUpdateRequest(BaseModel):
    text: str | None = None
    order_index: int | None = None
    category: str | None = None


# ─── Sentence Set ─────────────────────────────────

class SentenceSetResponse(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    language: str
    is_system: bool
    sentence_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class SentenceSetDetailResponse(SentenceSetResponse):
    """Set with all sentences included."""
    sentences: list[SentenceResponse] = []


class SentenceSetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    category: str = Field(default="basic")
    language: str = Field(default="vi")
    is_system: bool = False  # Only admin can set True
    sentences: list[SentenceCreateRequest] = []


class SentenceSetUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    language: str | None = None
