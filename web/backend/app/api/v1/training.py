"""
Training/Recording API — upload recordings, manage training data.

IMPORTANT: Routes are ordered so specific paths come BEFORE wildcards.
"""
import asyncio
import os
import uuid
import shutil
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select, func

from app.core.deps import CurrentUser, DBSession
from app.core.config import settings
from app.models.recording import Recording
from app.models.sentence import SentenceSet, Sentence
from app.models.reference import UserReference
from app.models.training import TrainingRequest, TrainedVoice
from app.schemas.recording import RecordingResponse, RecordingSetProgress
from app.schemas.training import (
    TrainingRequestCreate, TrainingRequestResponse,
    TrainedVoiceResponse, BaseModelInfo,
)
from app.services.recording_service import recording_service
from app.services.training_runner import run_training_pipeline, get_base_models

router = APIRouter()


def _rec_to_response(rec: Recording, sentence_text: str | None = None) -> RecordingResponse:
    """Convert Recording model to RecordingResponse, mapping 'duration' -> 'duration_sec'."""
    return RecordingResponse(
        id=rec.id,
        sentence_id=rec.sentence_id,
        sentence_text=sentence_text,
        file_path=rec.file_path,
        duration_sec=rec.duration,
        created_at=rec.created_at,
    )


# ═══ SPECIFIC ROUTES FIRST (before wildcards) ═════

@router.get("/recordings/audio/{recording_id}")
async def get_recording_audio(recording_id: int, user: CurrentUser, db: DBSession):
    """Stream a recording audio file."""
    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == user.id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    if not os.path.exists(rec.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(rec.file_path, media_type="audio/wav")


@router.post("/recordings/{recording_id}/to-ref", status_code=201)
async def recording_to_reference(recording_id: int, user: CurrentUser, db: DBSession):
    """Convert a recording into a user reference audio for voice cloning."""
    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == user.id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    if not os.path.exists(rec.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    sent_result = await db.execute(select(Sentence).where(Sentence.id == rec.sentence_id))
    sentence = sent_result.scalar_one_or_none()

    ref_dir = os.path.join(settings.STORAGE_PATH, "refs", str(user.id))
    os.makedirs(ref_dir, exist_ok=True)
    ref_id = uuid.uuid4()
    ref_path = os.path.join(ref_dir, f"{ref_id}.wav")
    shutil.copy2(rec.file_path, ref_path)

    reference = UserReference(
        id=ref_id,
        user_id=user.id,
        name=f"From recording: {sentence.text[:40]}..." if sentence else "From recording",
        language="vi",
        ref_text=sentence.text if sentence else None,
        audio_path=ref_path,
        duration_sec=rec.duration,
    )
    db.add(reference)
    await db.commit()

    return {"ref_id": str(ref_id), "name": reference.name, "message": "Recording converted to reference audio"}


@router.delete("/recordings/item/{recording_id}", status_code=204)
async def delete_recording(recording_id: int, user: CurrentUser, db: DBSession):
    """Delete a recording."""
    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == user.id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    if os.path.exists(rec.file_path):
        os.unlink(rec.file_path)
    await db.delete(rec)
    await db.commit()


# ═══ WILDCARD ROUTES (after specific ones) ════════

@router.get("/recordings/{set_id}", response_model=RecordingSetProgress)
async def list_recordings(set_id: int, user: CurrentUser, db: DBSession):
    """List all recordings for a sentence set, with progress tracking."""
    result = await db.execute(select(SentenceSet).where(SentenceSet.id == set_id))
    ss = result.scalar_one_or_none()
    if not ss:
        raise HTTPException(status_code=404, detail="Set not found")

    total_result = await db.execute(select(func.count()).where(Sentence.set_id == set_id))
    total = total_result.scalar()

    sent_result = await db.execute(select(Sentence.id).where(Sentence.set_id == set_id))
    sentence_ids = [row[0] for row in sent_result.all()]

    if sentence_ids:
        rec_result = await db.execute(
            select(Recording).where(
                Recording.user_id == user.id,
                Recording.sentence_id.in_(sentence_ids),
            ).order_by(Recording.created_at)
        )
        recordings = rec_result.scalars().all()
    else:
        recordings = []

    rec_responses = []
    for rec in recordings:
        s_result = await db.execute(select(Sentence).where(Sentence.id == rec.sentence_id))
        sent = s_result.scalar_one_or_none()
        rec_responses.append(_rec_to_response(rec, sent.text if sent else None))

    return RecordingSetProgress(
        set_id=set_id, set_name=ss.name, total_sentences=total,
        recorded_count=len(recordings), recordings=rec_responses,
    )


@router.post("/recordings/{set_id}/{sentence_id}", response_model=RecordingResponse, status_code=201)
async def upload_recording(
    set_id: int, sentence_id: int,
    audio: UploadFile = File(...),
    user: CurrentUser = None, db: DBSession = None,
):
    """Upload a recording for a specific sentence. Re-upload overwrites existing."""
    result = await db.execute(
        select(Sentence).where(Sentence.id == sentence_id, Sentence.set_id == set_id)
    )
    sentence = result.scalar_one_or_none()
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found in this set")

    content = await audio.read()
    if len(content) < 100:
        raise HTTPException(status_code=400, detail="File too small")

    try:
        file_path, duration = await asyncio.to_thread(
            recording_service.save_recording,
            file_content=content,
            original_filename=audio.filename or "upload.wav",
            user_id=user.id, set_id=set_id, sentence_id=sentence_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = await db.execute(
        select(Recording).where(Recording.user_id == user.id, Recording.sentence_id == sentence_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.file_path = file_path
        existing.duration = duration
        await db.commit()
        await db.refresh(existing)
        return _rec_to_response(existing, sentence.text)
    else:
        recording = Recording(
            user_id=user.id, sentence_id=sentence_id,
            file_path=file_path, duration=duration,
        )
        db.add(recording)
        await db.commit()
        await db.refresh(recording)
        return _rec_to_response(recording, sentence.text)


# ═══════════════════════════════════════════════════
# TRAINING REQUESTS
# ═══════════════════════════════════════════════════

@router.get("/base-models", response_model=List[BaseModelInfo])
async def list_base_models():
    """List available base models for finetuning."""
    return [BaseModelInfo(**m) for m in get_base_models()]


@router.post("/requests", response_model=TrainingRequestResponse, status_code=201)
async def submit_training_request(
    body: TrainingRequestCreate,
    background_tasks: BackgroundTasks,
    user: CurrentUser = None,
    db: DBSession = None,
):
    """
    Submit a training request. Requirements:
    - At least 10 recordings in the sentence set
    - No other pending/training request from this user
    """
    # Check for existing pending/training request
    result = await db.execute(
        select(TrainingRequest).where(
            TrainingRequest.user_id == user.id,
            TrainingRequest.status.in_(["pending", "approved", "training"]),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Already have a {existing.status} request (#{existing.id})",
        )

    # Check set exists
    result = await db.execute(
        select(SentenceSet).where(SentenceSet.id == body.set_id)
    )
    ss = result.scalar_one_or_none()
    if not ss:
        raise HTTPException(status_code=404, detail="Sentence set not found")

    # Count recordings
    sent_result = await db.execute(
        select(Sentence.id).where(Sentence.set_id == body.set_id)
    )
    sentence_ids = [row[0] for row in sent_result.all()]

    if sentence_ids:
        rec_count_result = await db.execute(
            select(func.count()).where(
                Recording.user_id == user.id,
                Recording.sentence_id.in_(sentence_ids),
            )
        )
        rec_count = rec_count_result.scalar()
    else:
        rec_count = 0

    if rec_count < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 10 recordings, have {rec_count}",
        )

    # Validate base model
    valid_models = {m["name"]: m["repo_id"] for m in get_base_models()}
    if body.base_model not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid base model: {body.base_model}")

    # Create request
    req = TrainingRequest(
        user_id=user.id,
        sentence_set_id=body.set_id,
        voice_name=body.voice_name,
        base_model_path=valid_models[body.base_model],
        status="pending",
        progress=0,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return TrainingRequestResponse.model_validate(req)


@router.get("/requests", response_model=List[TrainingRequestResponse])
async def list_training_requests(user: CurrentUser, db: DBSession):
    """List all training requests for the current user."""
    result = await db.execute(
        select(TrainingRequest)
        .where(TrainingRequest.user_id == user.id)
        .order_by(TrainingRequest.submitted_at.desc())
    )
    requests = result.scalars().all()
    return [TrainingRequestResponse.model_validate(r) for r in requests]


@router.get("/requests/{request_id}", response_model=TrainingRequestResponse)
async def get_training_request(request_id: int, user: CurrentUser, db: DBSession):
    """Get training request status + progress."""
    result = await db.execute(
        select(TrainingRequest).where(
            TrainingRequest.id == request_id,
            TrainingRequest.user_id == user.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return TrainingRequestResponse.model_validate(req)


@router.delete("/requests/{request_id}", status_code=204)
async def cancel_training_request(request_id: int, user: CurrentUser, db: DBSession):
    """Delete a training request (any status)."""
    from sqlalchemy import delete as sql_delete

    result = await db.execute(
        select(TrainingRequest).where(
            TrainingRequest.id == request_id,
            TrainingRequest.user_id == user.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Delete trained voice if exists
    await db.execute(sql_delete(TrainedVoice).where(TrainedVoice.training_request_id == request_id))
    await db.delete(req)
    await db.commit()

    # Clean up training files on disk
    train_dir = os.path.join(
        settings.STORAGE_PATH, "training", str(req.user_id), str(request_id)
    )
    if os.path.isdir(train_dir):
        shutil.rmtree(train_dir, ignore_errors=True)


# ─── Trained Voices ───────────────────────────────

@router.get("/voices", response_model=List[TrainedVoiceResponse])
async def list_trained_voices(user: CurrentUser, db: DBSession):
    """List user's active trained voices."""
    result = await db.execute(
        select(TrainedVoice)
        .where(TrainedVoice.user_id == user.id, TrainedVoice.is_active == True)
        .order_by(TrainedVoice.created_at.desc())
    )
    voices = result.scalars().all()
    return [TrainedVoiceResponse.model_validate(v) for v in voices]


@router.put("/voices/{voice_id}", response_model=TrainedVoiceResponse)
async def rename_trained_voice(voice_id: int, name: str, user: CurrentUser, db: DBSession):
    """Rename a trained voice."""
    result = await db.execute(
        select(TrainedVoice).where(
            TrainedVoice.id == voice_id,
            TrainedVoice.user_id == user.id,
        )
    )
    voice = result.scalar_one_or_none()
    if not voice:
        raise HTTPException(status_code=404, detail="Trained voice not found")

    voice.name = name
    await db.commit()
    await db.refresh(voice)
    return TrainedVoiceResponse.model_validate(voice)


@router.delete("/voices/{voice_id}", status_code=204)
async def delete_trained_voice(voice_id: int, user: CurrentUser, db: DBSession):
    """Soft-delete a trained voice (set is_active=False)."""
    result = await db.execute(
        select(TrainedVoice).where(
            TrainedVoice.id == voice_id,
            TrainedVoice.user_id == user.id,
        )
    )
    voice = result.scalar_one_or_none()
    if not voice:
        raise HTTPException(status_code=404, detail="Trained voice not found")

    voice.is_active = False
    await db.commit()
