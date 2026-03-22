"""
Reference audio endpoints — upload, list, get audio, delete.
"""
import os
import uuid
import shutil
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.deps import CurrentUser, DBSession
from app.core.config import settings
from app.models.reference import UserReference
from app.schemas.tts import ReferenceResponse, ReferenceCreateResponse
from app.services.tts_service import tts_service

router = APIRouter()


@router.post("", response_model=ReferenceCreateResponse, status_code=201)
async def upload_reference(
    name: str = Form(...),
    language: str = Form(default="vi"),
    ref_text: str = Form(default=""),
    audio: UploadFile = File(...),
    user: CurrentUser = None,
    db: DBSession = None,
):
    """
    Upload reference audio for voice cloning.
    Audio is resampled to 24kHz mono WAV and ref_codes pre-encoded.
    """
    # Create user directory
    ref_dir = os.path.join(settings.STORAGE_PATH, "refs", str(user.id))
    os.makedirs(ref_dir, exist_ok=True)

    ref_id = uuid.uuid4()
    audio_path = os.path.join(ref_dir, f"{ref_id}.wav")

    # Save uploaded file
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    # Resample to 24kHz mono if needed
    try:
        _resample_audio(audio_path, target_sr=24000)
    except Exception as e:
        os.unlink(audio_path)
        raise HTTPException(status_code=400, detail=f"Audio processing failed: {str(e)}")

    # Get duration
    duration = _get_audio_duration(audio_path)

    # Validate duration (3-15 seconds for ref)
    if duration is not None and (duration < 1.0 or duration > 30.0):
        os.unlink(audio_path)
        raise HTTPException(
            status_code=400,
            detail=f"Audio duration must be 1-30 seconds. Got {duration:.1f}s",
        )

    # Pre-encode ref codes (async-safe, may be None)
    ref_codes = tts_service.encode_reference(audio_path)

    # Save to DB
    reference = UserReference(
        id=ref_id,
        user_id=user.id,
        name=name,
        language=language,
        ref_text=ref_text or None,
        audio_path=audio_path,
        ref_codes=ref_codes,
        duration_sec=duration,
    )
    db.add(reference)
    await db.commit()
    await db.refresh(reference)

    return ReferenceCreateResponse(
        id=reference.id,
        name=reference.name,
        language=reference.language,
        ref_text=reference.ref_text,
        duration_sec=reference.duration_sec,
        has_ref_codes=ref_codes is not None,
        created_at=reference.created_at,
    )


@router.get("", response_model=List[ReferenceResponse])
async def list_references(user: CurrentUser, db: DBSession):
    """List all reference audio for the current user."""
    result = await db.execute(
        select(UserReference)
        .where(UserReference.user_id == user.id)
        .order_by(UserReference.created_at.desc())
    )
    refs = result.scalars().all()
    return [ReferenceResponse.model_validate(r) for r in refs]


@router.get("/{ref_id}/audio")
async def get_reference_audio(ref_id: uuid.UUID, user: CurrentUser, db: DBSession):
    """Download reference audio file."""
    result = await db.execute(
        select(UserReference).where(
            UserReference.id == ref_id,
            UserReference.user_id == user.id,
        )
    )
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(status_code=404, detail="Reference not found")

    if not os.path.exists(ref.audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(ref.audio_path, media_type="audio/wav", filename=f"{ref.name}.wav")


@router.delete("/{ref_id}", status_code=204)
async def delete_reference(ref_id: uuid.UUID, user: CurrentUser, db: DBSession):
    """Delete a reference audio."""
    result = await db.execute(
        select(UserReference).where(
            UserReference.id == ref_id,
            UserReference.user_id == user.id,
        )
    )
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(status_code=404, detail="Reference not found")

    # Delete file
    if os.path.exists(ref.audio_path):
        os.unlink(ref.audio_path)

    # Delete from DB
    await db.delete(ref)
    await db.commit()


# ─── Audio Utilities ──────────────────────────────

def _resample_audio(path: str, target_sr: int = 24000):
    """Resample audio to target sample rate, mono channel."""
    import torchaudio

    waveform, sr = torchaudio.load(path)

    # Convert to mono if stereo
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample if needed
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
        waveform = resampler(waveform)

    torchaudio.save(path, waveform, target_sr)


def _get_audio_duration(path: str) -> float | None:
    """Get audio duration in seconds."""
    try:
        import torchaudio
        info = torchaudio.info(path)
        return info.num_frames / info.sample_rate
    except Exception:
        return None
