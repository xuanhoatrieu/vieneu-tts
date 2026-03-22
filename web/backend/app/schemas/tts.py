"""
TTS and Reference Pydantic schemas.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# ─── TTS Synthesize ───────────────────────────────

class SynthesizeRequest(BaseModel):
    """Synthesize with preset voice."""
    text: str = Field(min_length=1, max_length=5000)
    voice_id: str = Field(default="")
    mode: str = Field(default="standard")
    temperature: float = Field(default=0.7)


class SynthesizeWithRefRequest(BaseModel):
    """Synthesize with saved reference audio (voice cloning)."""
    text: str = Field(min_length=1, max_length=5000)
    ref_id: uuid.UUID
    mode: str = Field(default="fast")


class SynthesizeWithTrainedVoiceRequest(BaseModel):
    """Synthesize using a LoRA-finetuned trained voice."""
    text: str = Field(min_length=1, max_length=5000)
    trained_voice_id: int


class SynthesizeResponse(BaseModel):
    """Response for any synthesis endpoint."""
    audio_url: str
    audio_file: str | None = None
    duration_sec: float | None = None
    processing_time_sec: float | None = None
    history_id: uuid.UUID | None = None


class TrainedSynthesisJobResponse(BaseModel):
    """Response for async trained voice synthesis job."""
    job_id: str
    status: str  # queued, processing, completed, failed
    audio_url: str | None = None
    audio_file: str | None = None
    duration_sec: float | None = None
    processing_time_sec: float | None = None
    error: str | None = None


class VoicePresetResponse(BaseModel):
    """Available preset voice."""
    id: str
    name: str
    language: str
    description: str | None = None


# ─── Reference Audio ─────────────────────────────

class ReferenceResponse(BaseModel):
    id: uuid.UUID
    name: str
    language: str
    ref_text: str | None
    duration_sec: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferenceCreateResponse(BaseModel):
    id: uuid.UUID
    name: str
    language: str
    ref_text: str | None
    duration_sec: float | None
    has_ref_codes: bool
    created_at: datetime


# ─── Audio History ────────────────────────────────

class AudioHistoryResponse(BaseModel):
    id: uuid.UUID
    voice_preset: str | None
    input_text: str
    duration_sec: float | None
    model_mode: str | None
    processing_time_sec: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
