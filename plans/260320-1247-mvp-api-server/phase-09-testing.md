# Phase 09: Testing & Deploy
Status: ⬜ Pending
Dependencies: Phase 08

## Objective
End-to-end testing toàn bộ workflow và deploy.

## Implementation Steps
1. [ ] Test full user flow: register → login → synthesize (preset)
2. [ ] Test ref flow: upload ref → synthesize-with-ref → cloned voice
3. [ ] Test recording flow: list sets → record sentences → list recordings
4. [ ] Test training flow: submit request → admin approve → start → complete → use trained voice
5. [ ] Test auth: JWT + API Key trên tất cả endpoints
6. [ ] Test edge cases: long text, invalid audio, permission violations
7. [ ] Deploy scripts (systemd / docker-compose)

## Full Workflow Test
```
1. Register user → JWT
2. List sentence sets → chọn "Bộ câu tiếng Việt cơ bản"
3. Record 15 sentences (upload audio)
4. Submit training request → status: pending
5. Admin login → approve request → chọn VieNeu-TTS-0.3B → start training
6. Wait → training complete → trained_voice created
7. User synthesize with trained voice → cloned audio
8. User upload ref audio → save as reference
9. User synthesize with saved ref → zero-shot clone
10. External app uses API key → synthesize OK
```

## Files to Create
- `tests/test_api.py`
- `web/backend/Dockerfile`
- `web/scripts/install-services.sh`

## Test Criteria
- [ ] All 10 workflow steps pass
- [ ] Admin API protected → 403 for non-admin
- [ ] User isolation → users can't see each other's data
- [ ] Training runner completes without error on RTX A4000
- [ ] API docs at `/docs` complete and accurate
