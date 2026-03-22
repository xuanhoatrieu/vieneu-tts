# Phase 06: Testing & Deploy
Status: ⬜ Pending
Dependencies: Phase 05

## Objective
End-to-end testing toàn bộ API và deploy với systemd hoặc Docker.

## Implementation Steps
1. [ ] Test full flow: register → login → upload ref → synthesize → history
2. [ ] Test auth: JWT + API Key trên tất cả endpoints
3. [ ] Test edge cases: invalid audio, empty text, long text chunking
4. [ ] Tạo deployment scripts (systemd hoặc docker-compose)
5. [ ] Tạo Swagger/ReDoc documentation
6. [ ] Performance test: synthesize latency trên RTX A4000

## Test Scenarios
```
1. User registers → logs in → gets JWT
2. User uploads reference audio → gets ref_id
3. User synthesizes with preset voice → gets WAV
4. User synthesizes with saved ref → gets cloned voice WAV
5. User synthesizes with custom audio upload → zero-shot clone
6. User lists audio history
7. External app uses API key → synthesize
8. Invalid token → 401
9. Very long text → chunked, joined correctly
10. Large audio file upload → handled gracefully
```

## Files to Create
- `web/backend/Dockerfile`
- `web/backend/docker-compose.yml`
- `web/scripts/install-services.sh` (systemd)
- `tests/test_api.py`

## Deploy Options
- **Option A**: systemd services (same as viF5TTS pattern)
- **Option B**: Docker Compose (VieNeu-TTS đã có Dockerfile)

## Test Criteria
- [ ] Tất cả 10 scenarios pass
- [ ] API docs accessible tại `/docs`
- [ ] Response time < 5s cho text ngắn (< 100 chars)
- [ ] Audio quality tương đương Gradio UI
