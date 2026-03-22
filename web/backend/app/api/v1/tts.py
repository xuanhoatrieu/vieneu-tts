"""
TTS API endpoints — synthesize with preset, ref, or custom audio.
"""
import os
import uuid
import time
import shutil
import tempfile
import threading
import asyncio

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DBSession
from app.core.config import settings
from app.models.reference import UserReference
from app.models.audio_history import AudioHistory

from app.schemas.tts import (
    SynthesizeRequest,
    SynthesizeWithRefRequest,
    SynthesizeWithTrainedVoiceRequest,
    SynthesizeResponse,
    TrainedSynthesisJobResponse,
    VoicePresetResponse,
)
from app.services.tts_service import tts_service, AVAILABLE_MODELS
from app.models.training import TrainedVoice
from sqlalchemy import select

router = APIRouter()

# ─── In-memory job store for trained voice synthesis ───
# Avoids Cloudflare 524 timeout by returning immediately and polling for results
_synthesis_jobs: dict[str, dict] = {}


@router.get("/models")
async def get_available_models(user: CurrentUser):
    """Get available TTS models + GPU status for the model selector."""
    return tts_service.get_model_status()


@router.post("/models/switch")
async def switch_tts_model(body: dict, user: CurrentUser):
    """User requests model switch. GPU models validated for VRAM."""
    repo = body.get("repo", "")
    if not repo:
        raise HTTPException(400, "Missing 'repo'")
    try:
        tts_service.switch_model(repo)
        return {"ok": True, "message": f"Đang chuyển sang model mới..."}
    except (RuntimeError, ValueError) as e:
        raise HTTPException(400, str(e))


@router.get("/models/status")
async def tts_model_status(user: CurrentUser):
    """Poll model loading status."""
    return tts_service.get_model_status()


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_preset(body: SynthesizeRequest, user: CurrentUser, db: DBSession):
    """Synthesize speech with a preset voice."""
    try:
        output_path, duration, elapsed = tts_service.synthesize_preset(
            text=body.text,
            voice_id=body.voice_id,
            mode=body.mode,
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

    # Save to history
    history = AudioHistory(
        user_id=user.id,
        voice_preset=body.voice_id,
        input_text=body.text,
        audio_path=output_path,
        duration_sec=duration,
        model_mode=body.mode,
        processing_time_sec=elapsed,
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    filename = os.path.basename(output_path)
    return SynthesizeResponse(
        audio_url=f"/api/v1/tts/audio/{filename}",
        audio_file=filename,
        duration_sec=duration,
        processing_time_sec=round(elapsed, 2),
        history_id=history.id,
    )


@router.post("/synthesize-with-ref", response_model=SynthesizeResponse)
async def synthesize_with_ref(body: SynthesizeWithRefRequest, user: CurrentUser, db: DBSession):
    """Synthesize speech using a saved reference audio (voice cloning)."""
    # Get user's reference
    result = await db.execute(
        select(UserReference).where(
            UserReference.id == body.ref_id,
            UserReference.user_id == user.id,
        )
    )
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(status_code=404, detail="Reference not found")

    try:
        output_path, duration, elapsed = tts_service.synthesize_with_ref(
            text=body.text,
            ref_audio_path=ref.audio_path,
            ref_text=ref.ref_text,
            mode=body.mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

    # Save to history
    history = AudioHistory(
        user_id=user.id,
        ref_id=ref.id,
        input_text=body.text,
        audio_path=output_path,
        duration_sec=duration,
        model_mode=body.mode,
        processing_time_sec=elapsed,
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    filename = os.path.basename(output_path)
    return SynthesizeResponse(
        audio_url=f"/api/v1/tts/audio/{filename}",
        audio_file=filename,
        duration_sec=duration,
        processing_time_sec=round(elapsed, 2),
        history_id=history.id,
    )


@router.post("/synthesize-custom", response_model=SynthesizeResponse)
async def synthesize_custom(
    text: str = Form(...),
    ref_text: str = Form(default=""),
    mode: str = Form(default="fast"),
    audio: UploadFile = File(...),
    user: CurrentUser = None,
    db: DBSession = None,
):
    """
    Zero-shot voice cloning with uploaded audio (not saved as reference).
    Upload audio file + text → synthesize in cloned voice.
    """
    # Save uploaded audio to temp
    suffix = os.path.splitext(audio.filename or ".wav")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    try:
        output_path, duration, elapsed = tts_service.synthesize_with_ref(
            text=text,
            ref_audio_path=tmp_path,
            ref_text=ref_text,
            mode=mode,
        )
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Save to history
    history = AudioHistory(
        user_id=user.id,
        input_text=text,
        audio_path=output_path,
        duration_sec=duration,
        model_mode=mode,
        processing_time_sec=elapsed,
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    filename = os.path.basename(output_path)
    return SynthesizeResponse(
        audio_url=f"/api/v1/tts/audio/{filename}",
        audio_file=filename,
        duration_sec=duration,
        processing_time_sec=round(elapsed, 2),
        history_id=history.id,
    )


@router.post("/synthesize-trained", response_model=TrainedSynthesisJobResponse)
async def synthesize_with_trained_voice(
    body: SynthesizeWithTrainedVoiceRequest, user: CurrentUser, db: DBSession,
):
    """Start async trained voice synthesis. Returns job_id immediately.
    Poll GET /synthesize-trained/{job_id} for results.
    This avoids Cloudflare 524 timeout (100s limit)."""

    # Get user's trained voice
    result = await db.execute(
        select(TrainedVoice).where(
            TrainedVoice.id == body.trained_voice_id,
            TrainedVoice.user_id == user.id,
            TrainedVoice.is_active == True,
        )
    )
    voice = result.scalar_one_or_none()
    if not voice:
        raise HTTPException(status_code=404, detail="Trained voice not found")

    if not voice.checkpoint_path or not os.path.isdir(voice.checkpoint_path):
        raise HTTPException(status_code=400, detail="Checkpoint không tồn tại hoặc đã bị xóa")

    # Create job
    job_id = str(uuid.uuid4())[:8]
    _synthesis_jobs[job_id] = {
        "status": "processing",
        "user_id": str(user.id),
        "voice_name": voice.name,
        "text": body.text,
        "started_at": time.time(),
    }

    # Run synthesis in background thread (fire-and-forget)
    def _background_synthesis():
        try:
            # Step 1: Ensure correct GPU model
            switch_err = tts_service.ensure_model_for_trained_voice(voice.base_model_repo)
            if switch_err:
                _synthesis_jobs[job_id]["status"] = "failed"
                _synthesis_jobs[job_id]["error"] = switch_err
                return

            # Step 2: Synthesize with LoRA
            output_path, duration, elapsed = tts_service.synthesize_with_trained_voice(
                text=body.text,
                checkpoint_path=voice.checkpoint_path,
                ref_audio_path=voice.ref_audio_path,
                ref_text=voice.ref_text,
            )

            filename = os.path.basename(output_path)
            _synthesis_jobs[job_id].update({
                "status": "completed",
                "audio_url": f"/api/v1/tts/audio/{filename}",
                "audio_file": filename,
                "duration_sec": duration,
                "processing_time_sec": round(elapsed, 2),
                "output_path": output_path,
            })
        except Exception as e:
            import traceback; traceback.print_exc()
            _synthesis_jobs[job_id]["status"] = "failed"
            _synthesis_jobs[job_id]["error"] = str(e)

    threading.Thread(target=_background_synthesis, daemon=True).start()

    return TrainedSynthesisJobResponse(job_id=job_id, status="processing")


@router.get("/synthesize-trained/{job_id}", response_model=TrainedSynthesisJobResponse)
async def poll_trained_synthesis(job_id: str, user: CurrentUser, db: DBSession):
    """Poll for trained voice synthesis job status."""
    job = _synthesis_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if job["user_id"] != str(user.id):
        raise HTTPException(status_code=403, detail="Not your job")

    if job["status"] == "completed":
        # Save to audio history on first completion poll
        if not job.get("history_saved"):
            history = AudioHistory(
                user_id=user.id,
                voice_preset=f"trained:{job['voice_name']}",
                input_text=job["text"],
                audio_path=job["output_path"],
                duration_sec=job["duration_sec"],
                model_mode="trained",
                processing_time_sec=job["processing_time_sec"],
            )
            db.add(history)
            await db.commit()
            job["history_saved"] = True

        return TrainedSynthesisJobResponse(
            job_id=job_id,
            status="completed",
            audio_url=job["audio_url"],
            audio_file=job["audio_file"],
            duration_sec=job["duration_sec"],
            processing_time_sec=job["processing_time_sec"],
        )
    elif job["status"] == "failed":
        return TrainedSynthesisJobResponse(
            job_id=job_id, status="failed", error=job.get("error", "Unknown error"),
        )
    else:
        elapsed = round(time.time() - job["started_at"])
        return TrainedSynthesisJobResponse(
            job_id=job_id, status="processing",
            error=f"Đang xử lý... ({elapsed}s)",
        )


@router.get("/trained-voices")
async def list_trained_voices(user: CurrentUser, db: DBSession):
    """List user's active trained voices for TTS Studio voice selector."""
    result = await db.execute(
        select(TrainedVoice).where(
            TrainedVoice.user_id == user.id,
            TrainedVoice.is_active == True,
        )
    )
    voices = result.scalars().all()

    # Get current model info for compatibility check
    current_model = tts_service._current_model if tts_service._initialized else ""
    is_gpu_model = current_model and "gguf" not in current_model.lower()

    return [
        {
            "id": str(v.id),
            "name": v.name,
            "type": "trained",
            "checkpoint_exists": bool(v.checkpoint_path and os.path.isdir(v.checkpoint_path)),
            "has_ref_audio": bool(v.ref_audio_path and os.path.exists(v.ref_audio_path)),
            "base_model_repo": v.base_model_repo,
            "base_model_name": _get_model_display_name(v.base_model_repo),
            "needs_gpu_model": not is_gpu_model,
        }
        for v in voices
    ]


def _get_model_display_name(repo: str | None) -> str:
    """Convert repo ID to human-friendly name."""
    if not repo:
        return "Unknown"
    for m in AVAILABLE_MODELS:
        if m["repo"] == repo:
            return m["name"]
    return repo.split("/")[-1] if "/" in repo else repo


@router.get("/voices", response_model=list[VoicePresetResponse])
async def list_voices():
    """List available preset voices."""
    voices = tts_service.get_preset_voices()
    return [VoicePresetResponse(**v) for v in voices]


@router.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve synthesized audio file."""
    output_dir = os.path.join(settings.STORAGE_PATH, "outputs")
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio not found")

    # Security: prevent path traversal
    if not os.path.realpath(filepath).startswith(os.path.realpath(output_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(filepath, media_type="audio/wav")
