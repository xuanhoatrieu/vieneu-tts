# Phase 04: TTS API + References
Status: ⬜ Pending
Dependencies: Phase 03

## Objective
TTS synthesis endpoints + reference audio management. Gọi `Vieneu()` SDK trực tiếp.

## Implementation Steps
1. [ ] Tạo `tts_service.py` — singleton Vieneu instance
2. [ ] POST `/tts/synthesize` — với preset voice
3. [ ] POST `/tts/synthesize-with-ref` — với saved reference (ref_id)
4. [ ] POST `/tts/synthesize-custom` — upload audio zero-shot clone
5. [ ] GET `/tts/voices` — list preset voices từ SDK
6. [ ] CRUD `/refs` — upload, list, get audio, delete reference
7. [ ] Lưu audio history + auto pre-encode ref_codes khi upload

## Files to Create
- `web/backend/services/tts_service.py`
- `web/backend/api/v1/tts.py`
- `web/backend/api/v1/refs.py`
- `web/backend/schemas/tts.py`, `refs.py`

## Test Criteria
- [ ] Synthesize với preset voice → WAV
- [ ] Synthesize với saved ref → cloned voice
- [ ] Upload ref → pre-encode ref_codes OK
- [ ] Audio history recorded

---
Next Phase: → phase-05-sentences.md
