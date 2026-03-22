# Phase 05: Recording Studio
Status: ⬜ Pending
Dependencies: Phase 04

## Objective
Thu âm theo sentence sets. Browser recording (MediaRecorder API), progress tracking, re-record. Theo mockup `recording_studio.png`.

## Implementation Steps
1. [ ] Recording Studio page layout (sidebar set list, main recording area)
2. [ ] Sentence set selector (GET /sentences/sets, dropdown)
3. [ ] Sentence list with recording status (recorded ✅ / not recorded ⬜)
4. [ ] Browser audio recorder (MediaRecorder API, start/stop/preview)
5. [ ] Upload recording per sentence (POST /training/recordings/{set_id}/{sentence_id})
6. [ ] Progress tracker (GET /training/recordings/{set_id} → progress bar)
7. [ ] Re-record existing (overwrite, confirm dialog)
8. [ ] Convert recording to reference (POST /training/recordings/{id}/to-ref)

## API Endpoints Used
- `GET /api/v1/sentences/sets`
- `GET /api/v1/sentences/sets/{id}`
- `POST /api/v1/training/recordings/{set_id}/{sentence_id}`
- `GET /api/v1/training/recordings/{set_id}`
- `GET /api/v1/training/recordings/audio/{id}`
- `POST /api/v1/training/recordings/{id}/to-ref`

## Test Criteria
- [ ] Chọn set → hiện danh sách câu
- [ ] Record → upload → câu đánh dấu ✅
- [ ] Progress bar cập nhật (10/20)
- [ ] Play lại recording đã thu
- [ ] Re-record → overwrite cũ

---
Next Phase: → phase-06-training.md
