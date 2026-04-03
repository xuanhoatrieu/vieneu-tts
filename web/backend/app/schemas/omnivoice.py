"""
OmniVoice Pydantic schemas.
"""
from pydantic import BaseModel, Field


class OmniVoiceDesignRequest(BaseModel):
    """Voice design — describe voice attributes via instruct text."""
    text: str = Field(min_length=1, max_length=5000)
    instruct: str = Field(
        min_length=1, max_length=500,
        description="Voice attributes: gender, age, pitch, accent, etc.",
    )
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    num_step: int = Field(default=32, ge=4, le=64)
    normalize: bool = Field(default=True, description="Normalize Vietnamese text with SEA-G2P")


class OmniVoiceAutoRequest(BaseModel):
    """Auto voice — let model choose voice automatically."""
    text: str = Field(min_length=1, max_length=5000)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    num_step: int = Field(default=32, ge=4, le=64)
    normalize: bool = Field(default=True, description="Normalize Vietnamese text with SEA-G2P")


class OmniVoiceResponse(BaseModel):
    """Response for OmniVoice synthesis."""
    audio_url: str
    audio_file: str | None = None
    duration_sec: float | None = None
    processing_time_sec: float | None = None


class OmniVoiceJobResponse(BaseModel):
    """Response for async OmniVoice synthesis job."""
    job_id: str
    status: str  # processing, completed, failed
    audio_url: str | None = None
    audio_file: str | None = None
    duration_sec: float | None = None
    processing_time_sec: float | None = None
    error: str | None = None
