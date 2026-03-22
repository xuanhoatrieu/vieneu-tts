# Phase 02: Database Schema (10 Tables)
Status: ⬜ Pending
Dependencies: Phase 01

## Objective
10 bảng PostgreSQL cho full platform: users, sentence_sets, sentences, recordings, user_references, training_requests, trained_voices, api_keys, audio_history, audio_config.

## Implementation Steps
1. [ ] Tạo SQLAlchemy models cho 10 tables
2. [ ] Setup Alembic migrations
3. [ ] Tạo initial migration + run
4. [ ] Seed data: admin user + system sentence sets + audio config defaults
5. [ ] Test CRUD operations cho tất cả models
6. [ ] Tạo indexes cho performance

## Tables Summary

```
users               → id, email, password_hash, name, role (user/admin), is_active
sentence_sets       → id, name, description, category, language, is_system, created_by
sentences           → id, set_id (FK), text, order_index, category
recordings          → id, user_id (FK), sentence_id (FK), file_path, duration
user_references     → id, user_id (FK), name, language, ref_text, audio_path, ref_codes (JSON)
training_requests   → id, user_id (FK), sentence_set_id (FK), voice_name, status, base_model_path, progress, queue_position
trained_voices      → id, user_id (FK), training_request_id (FK), name, checkpoint_path, ref_audio_path, ref_text, is_active, language
api_keys            → id, user_id (FK), key_hash, key_prefix, name, is_active, last_used_at
audio_history       → id, user_id (FK), ref_id (FK), voice_preset, trained_voice_id (FK), input_text, audio_path, duration_sec, model_mode, processing_time_sec
audio_config        → id, name, sample_rate, channels, format, min_duration, max_duration, description
```

## Test Criteria
- [ ] All 10 tables created via migration
- [ ] FK constraints working
- [ ] Seed data populated (admin, sentence sets, audio configs)

---
Next Phase: → phase-03-auth.md
