# Phase 07: Training Workflow
Status: ⬜ Pending
Dependencies: Phase 06

## Objective
Full training workflow: user submit request → admin approve → backend runs VieNeu LoRA finetune pipeline → trained voice available.

## Implementation Steps
1. [ ] POST `/training/requests` — user submit (min 10 recordings, check pending)
2. [ ] GET `/training/requests` — list user's requests + status
3. [ ] DELETE `/training/requests/{id}` — cancel pending request
4. [ ] Tạo `training_runner.py` — tích hợp VieNeu finetune pipeline
5. [ ] Background task: recordings → metadata.csv → filter → encode NeuCodec → LoRA train
6. [ ] Progress tracking (% steps via training_requests.progress)
7. [ ] On complete: tạo trained_voice record + ref audio/text

## Training Runner (tích hợp VieNeu pipeline)

```python
class TrainingRunner:
    def run_training(request_id, user_id, voice_name, base_model_path, recordings):
        # Step 1: Generate metadata.csv from recordings
        recording_service.generate_metadata_csv(user_id, set_id, recordings)

        # Step 2: Filter data (import from VieNeu finetune)
        from finetune.data_scripts.filter_data import filter_and_process_dataset

        # Step 3: Encode audio → NeuCodec codes
        from finetune.data_scripts.encode_data import encode_dataset

        # Step 4: Run LoRA training
        from finetune.train import run_training
        # Override config: model, output_dir, max_steps

        # Step 5: Create trained_voice record
        # checkpoint_path = finetune/output/{run_name}/

    def get_available_base_models():
        return [
            {"name": "VieNeu-TTS-0.3B", "path": "pnnbao-ump/VieNeu-TTS-0.3B"},
            {"name": "VieNeu-TTS-0.5B", "path": "pnnbao-ump/VieNeu-TTS"},
        ]
```

## Training Status Flow
```
pending → approved → training → completed
    ↓         ↓         ↓
 (cancel)  (reject)  (failed)
```

## Files to Create
- `web/backend/services/training_runner.py`
- `web/backend/api/v1/training.py` (phần requests)
- `web/backend/schemas/training.py`

## Test Criteria
- [ ] Submit request với < 10 recordings → 400
- [ ] Submit khi đã có pending request → 400
- [ ] Training chạy → checkpoint xuất hiện
- [ ] Training complete → trained_voice record tạo
- [ ] Progress tracking cập nhật đúng %

---
Next Phase: → phase-08-trained-voices.md
