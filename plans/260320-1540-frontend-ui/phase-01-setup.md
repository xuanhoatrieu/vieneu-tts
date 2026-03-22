# Phase 01: Project Setup + Design System
Status: ⬜ Pending
Dependencies: None

## Objective
Tạo React project (Vite), cài dependencies, thiết lập design system (dark theme, CSS tokens, layout components).

## Implementation Steps
1. [ ] Tạo Vite React project tại `web/frontend/`
2. [ ] Install deps: react-router-dom
3. [ ] Tạo design system CSS: colors, typography, spacing, glassmorphism tokens
4. [ ] Layout components: Sidebar, TopBar, MainContent, PageContainer
5. [ ] API service layer: `api.js` (fetch wrapper, auth interceptor, base URL config)
6. [ ] Auth context: `AuthProvider` (store JWT, user state, login/logout)

## Files to Create
- `web/frontend/` (Vite project)
- `src/index.css` (design system tokens)
- `src/components/Layout/` (Sidebar, TopBar)
- `src/services/api.js` (API client)
- `src/contexts/AuthContext.jsx`

## Test Criteria
- [ ] `npm run dev` chạy được
- [ ] Dark theme layout render đúng
- [ ] API client có thể gọi `GET /` thành công

---
Next Phase: → phase-02-auth.md
