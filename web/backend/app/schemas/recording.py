"""
Recording Pydantic schemas.
"""
from datetime import datetime
from pydantic import BaseModel


class RecordingResponse(BaseModel):
    id: int
    sentence_id: int
    sentence_text: str | None = None
    file_path: str
    duration_sec: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecordingSetProgress(BaseModel):
    """Progress of recordings for a sentence set."""
    set_id: int
    set_name: str
    total_sentences: int
    recorded_count: int
    recordings: list[RecordingResponse]
