"""
Admin API — training queue management, approve, start training, stats.
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import select, func

from app.core.deps import AdminUser, DBSession
from app.models.training import TrainingRequest
from app.models.user import User
from app.models.audio_history import AudioHistory
from app.models.reference import UserReference
from app.schemas.training import TrainingRequestResponse
from app.services.training_runner import run_training_pipeline

router = APIRouter()


# ─── Helpers ─────────────────────────────────────────

async def _enrich_with_user(db, requests):
    """Add user_email to training request responses."""
    enriched = []
    user_cache = {}
    for r in requests:
        resp = TrainingRequestResponse.model_validate(r)
        if r.user_id and r.user_id not in user_cache:
            result = await db.execute(select(User.email).where(User.id == r.user_id))
            user_cache[r.user_id] = result.scalar_one_or_none()
        resp.user_email = user_cache.get(r.user_id, "—")
        enriched.append(resp)
    return enriched


# ─── Stats ──────────────────────────────────────────

@router.get("/stats")
async def get_stats(admin: AdminUser = None, db: DBSession = None):
    """System-wide stats for admin dashboard."""
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    synth_count = (await db.execute(select(func.count(AudioHistory.id)))).scalar()
    ref_count = (await db.execute(select(func.count(UserReference.id)))).scalar()

    training_total = (await db.execute(select(func.count(TrainingRequest.id)))).scalar()
    training_pending = (await db.execute(
        select(func.count(TrainingRequest.id)).where(TrainingRequest.status == "pending")
    )).scalar()
    training_active = (await db.execute(
        select(func.count(TrainingRequest.id)).where(TrainingRequest.status == "training")
    )).scalar()
    training_done = (await db.execute(
        select(func.count(TrainingRequest.id)).where(TrainingRequest.status == "completed")
    )).scalar()

    return {
        "users": user_count,
        "synths": synth_count,
        "refs": ref_count,
        "training_total": training_total,
        "training_pending": training_pending,
        "training_active": training_active,
        "training_done": training_done,
    }


# ─── Users ──────────────────────────────────────────

def _user_to_dict(u):
    return {
        "id": str(u.id),
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }

@router.get("/users")
async def list_users(admin: AdminUser = None, db: DBSession = None):
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [_user_to_dict(u) for u in result.scalars().all()]


@router.post("/users")
async def create_user(body: dict, admin: AdminUser = None, db: DBSession = None):
    """Create a new user (admin only)."""
    from app.core.security import hash_password

    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    name = body.get("name", "").strip()
    role = body.get("role", "user")

    if not email or not password:
        raise HTTPException(400, "Email and password are required")
    if role not in ("user", "admin"):
        raise HTTPException(400, "Role must be 'user' or 'admin'")

    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Email '{email}' already exists")

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name or email.split("@")[0],
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_to_dict(user)


@router.patch("/users/{user_id}")
async def update_user(user_id: str, body: dict, admin: AdminUser = None, db: DBSession = None):
    """Update a user (admin only). Can change name, role, is_active, password."""
    from app.core.security import hash_password

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if "name" in body and body["name"]:
        user.name = body["name"].strip()
    if "role" in body and body["role"] in ("user", "admin"):
        user.role = body["role"]
    if "is_active" in body:
        user.is_active = bool(body["is_active"])
    if "password" in body and body["password"]:
        user.password_hash = hash_password(body["password"])

    await db.commit()
    await db.refresh(user)
    return _user_to_dict(user)


@router.get("/users/{user_id}/delete-preview")
async def delete_user_preview(user_id: str, admin: AdminUser = None, db: DBSession = None):
    """Preview what will be deleted when removing a user."""
    from app.models.audio_history import AudioHistory
    from app.models.recording import Recording
    from app.models.reference import UserReference
    from app.models.api_key import APIKey
    from app.models.training import TrainedVoice

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    counts = {}
    for label, model in [
        ("training_requests", TrainingRequest),
        ("trained_voices", TrainedVoice),
        ("recordings", Recording),
        ("references", UserReference),
        ("api_keys", APIKey),
        ("synthesis_history", AudioHistory),
    ]:
        r = await db.execute(select(func.count(model.id)).where(model.user_id == user.id))
        counts[label] = r.scalar()

    total = sum(counts.values())
    return {"user": _user_to_dict(user), "related_data": counts, "total_records": total}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: AdminUser = None, db: DBSession = None):
    """Delete a user and all related data + files on disk (admin only)."""
    import os, shutil
    if str(admin.id) == user_id:
        raise HTTPException(400, "Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Cascade-delete related records in FK-safe order
    from sqlalchemy import delete as sql_delete
    from app.models.audio_history import AudioHistory
    from app.models.recording import Recording
    from app.models.reference import UserReference
    from app.models.api_key import APIKey
    from app.models.training import TrainedVoice
    from app.core.config import settings

    # 1. Collect file paths before deleting DB records
    audio_history_rows = (await db.execute(
        select(AudioHistory.audio_path).where(AudioHistory.user_id == user.id)
    )).scalars().all()

    # 2. Delete DB records
    await db.execute(sql_delete(TrainedVoice).where(TrainedVoice.user_id == user.id))
    await db.execute(sql_delete(TrainingRequest).where(TrainingRequest.user_id == user.id))
    await db.execute(sql_delete(AudioHistory).where(AudioHistory.user_id == user.id))
    await db.execute(sql_delete(Recording).where(Recording.user_id == user.id))
    await db.execute(sql_delete(UserReference).where(UserReference.user_id == user.id))
    await db.execute(sql_delete(APIKey).where(APIKey.user_id == user.id))
    await db.delete(user)
    await db.commit()

    # 3. Clean up disk files (after successful commit)
    uid = str(user.id)
    # Recordings directory
    rec_dir = os.path.join(settings.STORAGE_PATH, "recordings", uid)
    if os.path.isdir(rec_dir):
        shutil.rmtree(rec_dir, ignore_errors=True)
    # References directory
    ref_dir = os.path.join(settings.STORAGE_PATH, "refs", uid)
    if os.path.isdir(ref_dir):
        shutil.rmtree(ref_dir, ignore_errors=True)
    # Individual audio history files
    for path in audio_history_rows:
        if path and os.path.isfile(path):
            try:
                os.unlink(path)
            except OSError:
                pass

    return {"ok": True}


# ─── Training Queue ─────────────────────────────────

@router.get("/training-queue", response_model=List[TrainingRequestResponse])
async def list_training_queue(
    status: str | None = Query(None, description="Filter: pending, approved, training, completed, failed"),
    admin: AdminUser = None,
    db: DBSession = None,
):
    """List all training requests (admin only). Optionally filter by status."""
    query = select(TrainingRequest).order_by(TrainingRequest.submitted_at.desc())
    if status:
        query = query.where(TrainingRequest.status == status)
    result = await db.execute(query)
    requests = result.scalars().all()
    return await _enrich_with_user(db, requests)


@router.post("/training-queue/{request_id}/approve", response_model=TrainingRequestResponse)
async def approve_training_request(
    request_id: int,
    admin: AdminUser = None,
    db: DBSession = None,
):
    """Approve a pending training request."""
    result = await db.execute(
        select(TrainingRequest).where(TrainingRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve: status is '{req.status}'")

    req.status = "approved"
    req.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(req)

    return TrainingRequestResponse.model_validate(req)


@router.post("/training-queue/{request_id}/reject", response_model=TrainingRequestResponse)
async def reject_training_request(
    request_id: int,
    admin: AdminUser = None,
    db: DBSession = None,
):
    """Reject a pending training request."""
    result = await db.execute(
        select(TrainingRequest).where(TrainingRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot reject: status is '{req.status}'")

    req.status = "rejected"
    await db.commit()
    await db.refresh(req)

    return TrainingRequestResponse.model_validate(req)


@router.post("/training-queue/{request_id}/start", response_model=TrainingRequestResponse)
async def start_training(
    request_id: int,
    background_tasks: BackgroundTasks,
    max_steps: int = Query(default=5000, ge=100, le=50000, description="Number of training steps"),
    gpu_id: int = Query(default=None, description="GPU ID to use for training"),
    base_model: str = Query(default=None, description="Base model repo for finetuning"),
    admin: AdminUser = None,
    db: DBSession = None,
):
    """Start training for an approved request (runs as background task)."""
    result = await db.execute(
        select(TrainingRequest).where(TrainingRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != "approved":
        raise HTTPException(status_code=400, detail=f"Cannot start: status is '{req.status}' (must be 'approved')")

    # Save base model selection
    if base_model:
        req.base_model_path = base_model
        await db.commit()
        await db.refresh(req)

    # Launch background training with params
    background_tasks.add_task(run_training_pipeline, request_id, max_steps, gpu_id)

    return TrainingRequestResponse.model_validate(req)


@router.delete("/training-queue/{request_id}")
async def delete_training_request(
    request_id: int, admin: AdminUser = None, db: DBSession = None,
):
    """Delete a training request and associated data."""
    import os, shutil
    from sqlalchemy import delete as sql_delete
    from app.models.training import TrainedVoice
    from app.core.config import settings

    result = await db.execute(
        select(TrainingRequest).where(TrainingRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Request not found")

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

    return {"ok": True}


@router.get("/training-queue/{request_id}/log")
async def get_training_log(
    request_id: int,
    tail: int = Query(default=200, ge=10, le=5000, description="Number of last lines to return"),
    admin: AdminUser = None,
    db: DBSession = None,
):
    """Get training log for a request. Returns last N lines as plain text."""
    from fastapi.responses import PlainTextResponse
    from app.services.training_runner import get_training_log_path

    result = await db.execute(
        select(TrainingRequest).where(TrainingRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Request not found")

    log_path = get_training_log_path(str(req.user_id), request_id)

    import os
    if not os.path.exists(log_path):
        return PlainTextResponse(
            f"[No log file yet — training may not have started]\n"
            f"Status: {req.status} | Progress: {req.progress}%",
            media_type="text/plain; charset=utf-8",
        )

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Return last N lines
        content = "".join(lines[-tail:])
        header = f"--- Training Log (request #{request_id}) | showing last {min(tail, len(lines))}/{len(lines)} lines ---\n\n"
        return PlainTextResponse(
            header + content,
            media_type="text/plain; charset=utf-8",
        )
    except Exception as e:
        return PlainTextResponse(f"[Error reading log: {e}]", media_type="text/plain; charset=utf-8")


# ─── Model Management ───────────────────────────────

@router.get("/models")
async def list_models(admin: AdminUser = None):
    """List available models and current status."""
    from app.services.tts_service import tts_service
    return tts_service.get_model_status()


@router.post("/models/switch")
async def switch_model(body: dict, admin: AdminUser = None):
    """Switch to a different backbone model (async)."""
    from app.services.tts_service import tts_service
    repo = body.get("repo", "")
    if not repo:
        raise HTTPException(400, "Missing 'repo' field")
    try:
        tts_service.switch_model(repo)
        return {"ok": True, "message": f"Switching to {repo}..."}
    except (RuntimeError, ValueError) as e:
        raise HTTPException(400, str(e))


@router.get("/models/status")
async def model_status(admin: AdminUser = None):
    """Poll model loading status."""
    from app.services.tts_service import tts_service
    return tts_service.get_model_status()
