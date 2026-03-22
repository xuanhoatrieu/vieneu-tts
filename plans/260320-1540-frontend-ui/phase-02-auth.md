# Phase 02: Auth (Login / Register)
Status: ⬜ Pending
Dependencies: Phase 01

## Objective
Login + Register pages theo mockup. JWT token management, protected routes, auto-redirect.

## Implementation Steps
1. [ ] Login page UI (glassmorphism card, gradient background) — theo `login_page.png`
2. [ ] Register page UI (tương tự login)
3. [ ] Auth API integration (POST /auth/login, POST /auth/register)
4. [ ] Protected route wrapper (redirect to login if no token)
5. [ ] Persistent session (localStorage token, auto-restore on reload)

## API Endpoints Used
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `GET /api/v1/users/profile`

## Test Criteria
- [ ] Login thành công → redirect to TTS Studio
- [ ] Register → auto-login → redirect
- [ ] Invalid credentials → error message
- [ ] Refresh page → vẫn logged in
- [ ] Logout → redirect to login

---
Next Phase: → phase-03-tts-studio.md
