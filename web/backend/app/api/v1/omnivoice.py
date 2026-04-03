"""
OmniVoice API endpoints — voice cloning, voice design, and auto voice.
Uses job-based async pattern to avoid Cloudflare 524 timeout.
"""
import os
import uuid
import time
import shutil
import tempfile
import threading

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DBSession
from app.core.config import settings
from app.schemas.omnivoice import (
    OmniVoiceDesignRequest,
    OmniVoiceAutoRequest,
    OmniVoiceJobResponse,
)
from app.services.omnivoice_service import omnivoice_service

router = APIRouter()

# ─── In-memory job store ───
_omni_jobs: dict[str, dict] = {}


@router.get("/status")
async def get_omnivoice_status(user: CurrentUser):
    """Get OmniVoice model status."""
    return omnivoice_service.get_status()


# ─── Voice Cloning (file upload) ───

@router.post("/generate-clone", response_model=OmniVoiceJobResponse)
async def generate_clone(
    text: str = Form(..., min_length=1, max_length=5000),
    ref_text: str = Form(default=""),
    speed: float = Form(default=1.0),
    num_step: int = Form(default=32),
    normalize: bool = Form(default=True),
    audio: UploadFile = File(...),
    user: CurrentUser = None,
):
    """Voice cloning with uploaded reference audio. Returns job_id for polling."""
    # Save uploaded audio to temp
    suffix = os.path.splitext(audio.filename or ".wav")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    # Create job
    job_id = str(uuid.uuid4())[:8]
    _omni_jobs[job_id] = {
        "status": "processing",
        "user_id": str(user.id),
        "mode": "clone",
        "text": text[:100],
        "started_at": time.time(),
    }

    def _background():
        try:
            output_path, duration, elapsed = omnivoice_service.generate_clone(
                text=text,
                ref_audio_path=tmp_path,
                ref_text=ref_text or None,
                speed=speed,
                num_step=num_step,
                normalize=normalize,
            )
            filename = os.path.basename(output_path)
            _omni_jobs[job_id].update({
                "status": "completed",
                "audio_url": f"/api/v1/omnivoice/audio/{filename}",
                "audio_file": filename,
                "duration_sec": duration,
                "processing_time_sec": round(elapsed, 2),
            })
        except Exception as e:
            import traceback; traceback.print_exc()
            _omni_jobs[job_id]["status"] = "failed"
            _omni_jobs[job_id]["error"] = str(e)
        finally:
            # Clean temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    threading.Thread(target=_background, daemon=True).start()
    return OmniVoiceJobResponse(job_id=job_id, status="processing")


# ─── Voice Cloning from Voice Library ───

@router.post("/generate-clone-ref", response_model=OmniVoiceJobResponse)
async def generate_clone_from_ref(
    text: str = Form(..., min_length=1, max_length=5000),
    ref_id: str = Form(...),
    speed: float = Form(default=1.0),
    num_step: int = Form(default=32),
    normalize: bool = Form(default=True),
    user: CurrentUser = None,
    db: DBSession = None,
):
    """Voice cloning using a reference from Voice Library."""
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.reference import UserReference

    # Look up reference in DB
    try:
        rid = _uuid.UUID(ref_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ref_id")

    result = await db.execute(
        select(UserReference).where(
            UserReference.id == rid,
            UserReference.user_id == user.id,
        )
    )
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(status_code=404, detail="Reference not found")
    if not os.path.exists(ref.audio_path):
        raise HTTPException(status_code=404, detail="Reference audio file not found")

    ref_audio_path = ref.audio_path
    ref_text = ref.ref_text or ""

    # Create job
    job_id = str(_uuid.uuid4())[:8]
    _omni_jobs[job_id] = {
        "status": "processing",
        "user_id": str(user.id),
        "mode": "clone-ref",
        "text": text[:100],
        "started_at": time.time(),
    }

    def _background():
        try:
            output_path, duration, elapsed = omnivoice_service.generate_clone(
                text=text,
                ref_audio_path=ref_audio_path,
                ref_text=ref_text or None,
                speed=speed,
                num_step=num_step,
                normalize=normalize,
            )
            filename = os.path.basename(output_path)
            _omni_jobs[job_id].update({
                "status": "completed",
                "audio_url": f"/api/v1/omnivoice/audio/{filename}",
                "audio_file": filename,
                "duration_sec": duration,
                "processing_time_sec": round(elapsed, 2),
            })
        except Exception as e:
            import traceback; traceback.print_exc()
            _omni_jobs[job_id]["status"] = "failed"
            _omni_jobs[job_id]["error"] = str(e)

    threading.Thread(target=_background, daemon=True).start()
    return OmniVoiceJobResponse(job_id=job_id, status="processing")

@router.post("/generate-design", response_model=OmniVoiceJobResponse)
async def generate_design(body: OmniVoiceDesignRequest, user: CurrentUser):
    """Voice design — describe desired voice with attributes."""
    job_id = str(uuid.uuid4())[:8]
    _omni_jobs[job_id] = {
        "status": "processing",
        "user_id": str(user.id),
        "mode": "design",
        "text": body.text[:100],
        "started_at": time.time(),
    }

    def _background():
        try:
            output_path, duration, elapsed = omnivoice_service.generate_design(
                text=body.text,
                instruct=body.instruct,
                speed=body.speed,
                num_step=body.num_step,
                normalize=body.normalize,
            )
            filename = os.path.basename(output_path)
            _omni_jobs[job_id].update({
                "status": "completed",
                "audio_url": f"/api/v1/omnivoice/audio/{filename}",
                "audio_file": filename,
                "duration_sec": duration,
                "processing_time_sec": round(elapsed, 2),
            })
        except Exception as e:
            import traceback; traceback.print_exc()
            _omni_jobs[job_id]["status"] = "failed"
            _omni_jobs[job_id]["error"] = str(e)

    threading.Thread(target=_background, daemon=True).start()
    return OmniVoiceJobResponse(job_id=job_id, status="processing")


# ─── Auto Voice ───

@router.post("/generate-auto", response_model=OmniVoiceJobResponse)
async def generate_auto(body: OmniVoiceAutoRequest, user: CurrentUser):
    """Auto voice — model chooses voice automatically."""
    job_id = str(uuid.uuid4())[:8]
    _omni_jobs[job_id] = {
        "status": "processing",
        "user_id": str(user.id),
        "mode": "auto",
        "text": body.text[:100],
        "started_at": time.time(),
    }

    def _background():
        try:
            output_path, duration, elapsed = omnivoice_service.generate_auto(
                text=body.text,
                speed=body.speed,
                num_step=body.num_step,
                normalize=body.normalize,
            )
            filename = os.path.basename(output_path)
            _omni_jobs[job_id].update({
                "status": "completed",
                "audio_url": f"/api/v1/omnivoice/audio/{filename}",
                "audio_file": filename,
                "duration_sec": duration,
                "processing_time_sec": round(elapsed, 2),
            })
        except Exception as e:
            import traceback; traceback.print_exc()
            _omni_jobs[job_id]["status"] = "failed"
            _omni_jobs[job_id]["error"] = str(e)

    threading.Thread(target=_background, daemon=True).start()
    return OmniVoiceJobResponse(job_id=job_id, status="processing")


# ─── Poll job status ───

@router.get("/jobs/{job_id}", response_model=OmniVoiceJobResponse)
async def poll_omnivoice_job(job_id: str, user: CurrentUser):
    """Poll for OmniVoice synthesis job status."""
    job = _omni_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user.id):
        raise HTTPException(status_code=403, detail="Not your job")

    if job["status"] == "completed":
        return OmniVoiceJobResponse(
            job_id=job_id,
            status="completed",
            audio_url=job["audio_url"],
            audio_file=job["audio_file"],
            duration_sec=job["duration_sec"],
            processing_time_sec=job["processing_time_sec"],
        )
    elif job["status"] == "failed":
        return OmniVoiceJobResponse(
            job_id=job_id, status="failed", error=job.get("error", "Unknown error"),
        )
    else:
        elapsed = round(time.time() - job["started_at"])
        return OmniVoiceJobResponse(
            job_id=job_id, status="processing",
            error=f"Đang xử lý... ({elapsed}s)",
        )


# ─── Serve audio ───

@router.get("/audio/{filename}")
async def get_omni_audio(filename: str):
    """Serve OmniVoice audio file."""
    output_dir = os.path.join(settings.STORAGE_PATH, "outputs", "omnivoice")
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio not found")
    if not os.path.realpath(filepath).startswith(os.path.realpath(output_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(filepath, media_type="audio/wav")
