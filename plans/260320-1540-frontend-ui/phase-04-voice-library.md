# Phase 04: Voice Library + References
Status: ⬜ Pending
Dependencies: Phase 03

## Objective
Quản lý voice references: upload, list, play, delete. Theo mockup `voice_library.png`.

## Implementation Steps
1. [ ] Voice Library page layout (grid cards, search/filter)
2. [ ] Upload reference audio (drag & drop, name input, language selector)
3. [ ] Reference list (cards with name, duration, play button, delete)
4. [ ] Audio preview player (inline play for each ref card)
5. [ ] Delete confirmation dialog

## API Endpoints Used
- `GET /api/v1/refs`
- `POST /api/v1/refs`
- `GET /api/v1/refs/{id}/audio`
- `DELETE /api/v1/refs/{id}`

## Test Criteria
- [ ] Upload WAV/MP3 → appears in library
- [ ] Play ref audio inline
- [ ] Delete → confirm → removed from list
- [ ] Empty state when no refs

---
Next Phase: → phase-05-recording.md
