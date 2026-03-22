# Phase 06: Training + Trained Voices
Status: ⬜ Pending
Dependencies: Phase 05

## Objective
Submit training request, track progress, view trained voices. Theo mockup `training_page.png`.

## Implementation Steps
1. [ ] Training page layout (request form, request list, trained voices)
2. [ ] Submit training request (voice name, set selector, base model)
3. [ ] Training request list (status badges, progress bar)
4. [ ] Auto-refresh progress (polling or interval)
5. [ ] Trained voices list (name, status, rename, soft-delete)
6. [ ] Use trained voice in TTS Studio (selector integration)

## API Endpoints Used
- `GET /api/v1/training/base-models`
- `POST /api/v1/training/requests`
- `GET /api/v1/training/requests`
- `GET /api/v1/training/requests/{id}`
- `DELETE /api/v1/training/requests/{id}`
- `GET /api/v1/training/voices`
- `PUT /api/v1/training/voices/{id}`
- `DELETE /api/v1/training/voices/{id}`

## Test Criteria
- [ ] Submit request → appears in list as "pending"
- [ ] Progress updates khi training chạy
- [ ] Trained voice hiện khi hoàn thành
- [ ] Rename / soft-delete trained voice
- [ ] Cancel pending request

---
Next Phase: → phase-07-admin.md
