# Phase 03: Auth System
Status: ⬜ Pending
Dependencies: Phase 02

## Objective
Xây dựng hệ thống authentication với JWT Bearer token + API Key, hỗ trợ register/login/profile.

## Implementation Steps
1. [ ] Implement password hashing (bcrypt)
2. [ ] Implement JWT token generation/validation
3. [ ] Implement API Key generation/validation
4. [ ] Tạo auth endpoints (register, login, profile)
5. [ ] Tạo auth dependencies (get_current_user, get_current_user_or_apikey)

## API Endpoints

```
POST   /api/v1/auth/register      — Đăng ký tài khoản
POST   /api/v1/auth/login         — Đăng nhập → JWT token
GET    /api/v1/users/profile      — Xem profile (JWT required)
POST   /api/v1/api-keys           — Tạo API key (JWT required)
GET    /api/v1/api-keys           — List API keys (JWT required)
DELETE /api/v1/api-keys/{id}      — Xóa API key (JWT required)
```

## Auth Methods
```
# Method 1: JWT Bearer Token
Authorization: Bearer <jwt_token>

# Method 2: API Key (cho SDK/external apps)
X-API-Key: vneu_xxxxxxxxxxxxx
```

## Files to Create
- `web/backend/core/security.py` — JWT + password + API key utils
- `web/backend/core/deps.py` — FastAPI dependencies
- `web/backend/api/v1/auth.py` — Auth endpoints
- `web/backend/api/v1/users.py` — User endpoints
- `web/backend/api/v1/api_keys.py` — API key endpoints
- `web/backend/schemas/auth.py` — Request/response schemas

## Test Criteria
- [ ] Register → Login → Get JWT → Access protected endpoint
- [ ] API Key auth hoạt động
- [ ] Invalid credentials → 401
- [ ] Expired token → 401

---
Next Phase: → phase-04-tts-api.md
