"""
Sentence Sets & Sentences API — CRUD with permission system.

Permissions:
- Admin: CRUD all sets (system + custom)
- User: CRUD only their own custom sets
- System sets: readable by everyone, editable only by admin
"""
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func

from app.core.deps import CurrentUser, DBSession
from app.models.sentence import SentenceSet, Sentence
from app.schemas.sentence import (
    SentenceSetResponse,
    SentenceSetDetailResponse,
    SentenceSetCreateRequest,
    SentenceSetUpdateRequest,
    SentenceCreateRequest,
    SentenceUpdateRequest,
    SentenceResponse,
)

router = APIRouter()


# ─── Sentence Sets ────────────────────────────────

@router.get("/sets", response_model=List[SentenceSetResponse])
async def list_sentence_sets(
    category: str | None = Query(None, description="Filter: basic, tech, emotional, business, ref"),
    language: str | None = Query(None, description="Filter: vi, en"),
    user: CurrentUser = None,
    db: DBSession = None,
):
    """List sentence sets. Shows system sets + user's own custom sets."""
    query = select(SentenceSet)

    # Filter by category
    if category:
        query = query.where(SentenceSet.category == category)

    # Filter by language
    if language:
        query = query.where(SentenceSet.language == language)

    # Show: system sets + user's own sets
    if user.role != "admin":
        query = query.where(
            (SentenceSet.is_system == True) | (SentenceSet.created_by == user.id)
        )

    query = query.order_by(SentenceSet.is_system.desc(), SentenceSet.created_at.desc())
    result = await db.execute(query)
    sets = result.scalars().all()

    # Add sentence_count
    responses = []
    for s in sets:
        count_result = await db.execute(
            select(func.count()).where(Sentence.set_id == s.id)
        )
        count = count_result.scalar()
        resp = SentenceSetResponse.model_validate(s)
        resp.sentence_count = count
        responses.append(resp)

    return responses


@router.get("/sets/{set_id}", response_model=SentenceSetDetailResponse)
async def get_sentence_set(set_id: int, user: CurrentUser, db: DBSession):
    """Get a sentence set with all its sentences."""
    result = await db.execute(select(SentenceSet).where(SentenceSet.id == set_id))
    ss = result.scalar_one_or_none()

    if not ss:
        raise HTTPException(status_code=404, detail="Sentence set not found")

    # Permission: system sets visible to all, custom sets only to owner/admin
    if not ss.is_system and ss.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # Get sentences
    sent_result = await db.execute(
        select(Sentence).where(Sentence.set_id == set_id).order_by(Sentence.order_index)
    )
    sentences = sent_result.scalars().all()

    resp = SentenceSetDetailResponse.model_validate(ss)
    resp.sentences = [SentenceResponse.model_validate(s) for s in sentences]
    resp.sentence_count = len(sentences)

    return resp


@router.post("/sets", response_model=SentenceSetDetailResponse, status_code=201)
async def create_sentence_set(body: SentenceSetCreateRequest, user: CurrentUser, db: DBSession):
    """Create a sentence set. Only admin can create system sets."""
    # Only admin can create system sets
    if body.is_system and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create system sets")

    ss = SentenceSet(
        name=body.name,
        description=body.description,
        category=body.category,
        language=body.language,
        is_system=body.is_system if user.role == "admin" else False,
        created_by=user.id,
    )
    db.add(ss)
    await db.flush()

    # Add sentences if provided
    for i, sent in enumerate(body.sentences):
        db.add(Sentence(
            set_id=ss.id,
            text=sent.text,
            order_index=sent.order_index or (i + 1),
            category=sent.category,
        ))

    await db.commit()
    await db.refresh(ss)

    # Get sentences for response
    sent_result = await db.execute(
        select(Sentence).where(Sentence.set_id == ss.id).order_by(Sentence.order_index)
    )
    sentences = sent_result.scalars().all()

    resp = SentenceSetDetailResponse.model_validate(ss)
    resp.sentences = [SentenceResponse.model_validate(s) for s in sentences]
    resp.sentence_count = len(sentences)

    return resp


@router.put("/sets/{set_id}", response_model=SentenceSetResponse)
async def update_sentence_set(
    set_id: int, body: SentenceSetUpdateRequest, user: CurrentUser, db: DBSession
):
    """Update a sentence set. Admin: any set. User: own custom sets only."""
    result = await db.execute(select(SentenceSet).where(SentenceSet.id == set_id))
    ss = result.scalar_one_or_none()

    if not ss:
        raise HTTPException(status_code=404, detail="Sentence set not found")

    # Permission check
    if ss.is_system and user.role != "admin":
        raise HTTPException(status_code=403, detail="Cannot modify system sets")
    if not ss.is_system and ss.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your set")

    # Update fields
    if body.name is not None:
        ss.name = body.name
    if body.description is not None:
        ss.description = body.description
    if body.category is not None:
        ss.category = body.category
    if body.language is not None:
        ss.language = body.language

    await db.commit()
    await db.refresh(ss)

    count_result = await db.execute(select(func.count()).where(Sentence.set_id == ss.id))
    resp = SentenceSetResponse.model_validate(ss)
    resp.sentence_count = count_result.scalar()
    return resp


@router.delete("/sets/{set_id}", status_code=204)
async def delete_sentence_set(set_id: int, user: CurrentUser, db: DBSession):
    """Delete a sentence set (cascade deletes sentences). Admin: any. User: own only."""
    result = await db.execute(select(SentenceSet).where(SentenceSet.id == set_id))
    ss = result.scalar_one_or_none()

    if not ss:
        raise HTTPException(status_code=404, detail="Sentence set not found")

    if ss.is_system and user.role != "admin":
        raise HTTPException(status_code=403, detail="Cannot delete system sets")
    if not ss.is_system and ss.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your set")

    await db.delete(ss)
    await db.commit()


# ─── Individual Sentences ─────────────────────────

@router.post("/sets/{set_id}/sentences", response_model=SentenceResponse, status_code=201)
async def add_sentence(set_id: int, body: SentenceCreateRequest, user: CurrentUser, db: DBSession):
    """Add a sentence to a set."""
    result = await db.execute(select(SentenceSet).where(SentenceSet.id == set_id))
    ss = result.scalar_one_or_none()
    if not ss:
        raise HTTPException(status_code=404, detail="Set not found")

    # Permission
    if ss.is_system and user.role != "admin":
        raise HTTPException(status_code=403, detail="Cannot modify system sets")
    if not ss.is_system and ss.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your set")

    # Auto order_index if not set
    if body.order_index == 0:
        max_result = await db.execute(
            select(func.max(Sentence.order_index)).where(Sentence.set_id == set_id)
        )
        max_idx = max_result.scalar() or 0
        body.order_index = max_idx + 1

    sentence = Sentence(
        set_id=set_id,
        text=body.text,
        order_index=body.order_index,
        category=body.category,
    )
    db.add(sentence)
    await db.commit()
    await db.refresh(sentence)

    return SentenceResponse.model_validate(sentence)


@router.put("/sentences/{sentence_id}", response_model=SentenceResponse)
async def update_sentence(
    sentence_id: int, body: SentenceUpdateRequest, user: CurrentUser, db: DBSession
):
    """Update a sentence."""
    result = await db.execute(
        select(Sentence).where(Sentence.id == sentence_id)
    )
    sentence = result.scalar_one_or_none()
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")

    # Check set permission
    set_result = await db.execute(
        select(SentenceSet).where(SentenceSet.id == sentence.set_id)
    )
    ss = set_result.scalar_one_or_none()
    if ss.is_system and user.role != "admin":
        raise HTTPException(status_code=403, detail="Cannot modify system sets")
    if not ss.is_system and ss.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your set")

    if body.text is not None:
        sentence.text = body.text
    if body.order_index is not None:
        sentence.order_index = body.order_index
    if body.category is not None:
        sentence.category = body.category

    await db.commit()
    await db.refresh(sentence)
    return SentenceResponse.model_validate(sentence)


@router.delete("/sentences/{sentence_id}", status_code=204)
async def delete_sentence(sentence_id: int, user: CurrentUser, db: DBSession):
    """Delete a sentence."""
    result = await db.execute(select(Sentence).where(Sentence.id == sentence_id))
    sentence = result.scalar_one_or_none()
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")

    set_result = await db.execute(
        select(SentenceSet).where(SentenceSet.id == sentence.set_id)
    )
    ss = set_result.scalar_one_or_none()
    if ss.is_system and user.role != "admin":
        raise HTTPException(status_code=403, detail="Cannot modify system sets")
    if not ss.is_system and ss.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your set")

    await db.delete(sentence)
    await db.commit()
