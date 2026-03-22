"""
Training Pydantic schemas.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Training Request ─────────────────────────────

class TrainingRequestCreate(BaseModel):
    voice_name: str = Field(min_length=1, max_length=100)
    set_id: int
    base_model: str = "VieNeu-TTS-0.3B"


class TrainingRequestResponse(BaseModel):
    id: int
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    voice_name: str
    sentence_set_id: int
    base_model_path: str | None
    status: str
    progress: int
    submitted_at: datetime
    approved_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ─── Trained Voice ────────────────────────────────

class TrainedVoiceResponse(BaseModel):
    id: int
    name: str
    checkpoint_path: str
    base_model_repo: str | None = None
    ref_audio_path: str | None
    is_active: bool
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Base Models ──────────────────────────────────

class BaseModelInfo(BaseModel):
    name: str
    repo_id: str
    description: str
