# Phase 06: Recording Studio
Status: ⬜ Pending
Dependencies: Phase 05

## Objective
Upload audio recordings per sentence. Auto-resample 24kHz mono, format conversion (WebM/OGG→WAV), validation 1-30s. Dùng cho cả training lẫn ref audio.

## Implementation Steps
1. [ ] Tạo `recording_service.py` — save, validate, resample, convert
2. [ ] POST `/training/recordings/{set_id}/{sentence_id}` — upload recording
3. [ ] GET `/training/recordings/{set_id}` — list recordings for a set
4. [ ] GET `/training/recordings/audio/{id}` — stream audio file
5. [ ] DELETE `/training/recordings/{id}` — delete recording
6. [ ] Tạo ref từ recording — chuyển recording thành user_reference

## Recording Service Logic
```python
class RecordingService:
    async def save_recording(file_content, user_id, set_id, sentence_id):
        # 1. Detect format (WebM/OGG/WAV)
        # 2. Convert to WAV via ffmpeg nếu cần
        # 3. Resample 24kHz mono via torchaudio
        # 4. Validate duration 1-30s
        # 5. Save to data/recordings/{user_id}/{set_id}/sentence_{id}.wav
        # 6. Return (file_path, duration)

    def generate_metadata_csv(user_id, set_id, recordings):
        # Tạo metadata.csv cho training pipeline
        # Format: filename|text
```

## Audio Config (from audio_config table)
- Recording: 24kHz, mono, WAV, 1-30s
- Ref audio: 24kHz, mono, WAV, 3-15s (tối ưu cho VieNeu encode)
- Training: 16kHz, mono, WAV, 3-15s (tối ưu cho NeuCodec encode)

## Files to Create
- `web/backend/services/recording_service.py`
- `web/backend/api/v1/training.py` (phần recordings)
- `web/backend/schemas/recording.py`

## Test Criteria
- [ ] Upload WAV → save OK, duration returned
- [ ] Upload WebM → convert to WAV via ffmpeg
- [ ] Audio < 1s → reject 400
- [ ] Audio > 30s → reject 400
- [ ] Re-upload same sentence → overwrite existing

---
Next Phase: → phase-07-training.md
