# Phase 08: Trained Voices + Admin API
Status: ⬜ Pending
Dependencies: Phase 07

## Objective
Trained voice management (user side) + Admin API (training queue, approve, start training, manage sentence sets).

## Implementation Steps — Trained Voices
1. [ ] GET `/trained-voices` — list user's trained voices (active only)
2. [ ] PUT `/trained-voices/{id}` — rename voice
3. [ ] DELETE `/trained-voices/{id}` — soft delete (is_active=false)

## Implementation Steps — Admin API
4. [ ] GET `/admin/training-queue` — list all requests (filter by status)
5. [ ] POST `/admin/training-queue/{id}/approve` — approve + chọn base model
6. [ ] POST `/admin/training-queue/{id}/start` — start training (background task)

## Using Trained Voice in TTS
```python
# Trong tts_service.py:
def synthesize_with_trained_voice(text, trained_voice_id):
    voice = db.get(trained_voice_id)
    # Load LoRA adapter
    tts.load_lora_adapter(voice.checkpoint_path)
    # Infer with ref
    audio = tts.infer(text=text, ref_codes=voice.ref_codes, ref_text=voice.ref_text)
    return audio
```

## POST `/tts/synthesize` — Extended
```
Body: {
    "text": "Xin chào",
    "voice_type": "preset" | "ref" | "trained",
    "voice_id": "preset_name" | "ref_uuid" | "trained_voice_id"
}
```

## Admin Dependency
- `AdminUser = Depends(require_admin)` — check user.role == "admin"

## Files to Create
- `web/backend/api/v1/trained_voice.py`
- `web/backend/api/v1/admin.py`
- `web/backend/schemas/trained_voice.py`

## Test Criteria
- [ ] User list → chỉ thấy trained voices của mình
- [ ] Admin approve → status change to "approved"
- [ ] Admin start → training chạy background
- [ ] Synthesize với trained voice → audio cloned OK
- [ ] Non-admin gọi admin API → 403
- [ ] Soft delete → voice không hiện trong list

---
Next Phase: → phase-09-testing.md
