# Phase 07: Admin Dashboard
Status: ⬜ Pending
Dependencies: Phase 06

## Objective
Admin-only dashboard: training queue management (approve/reject/start), sentence set management. Theo mockup `admin_dashboard.png`.

## Implementation Steps
1. [ ] Admin route guard (redirect non-admin users)
2. [ ] Admin dashboard layout (sidebar with admin menu)
3. [ ] Training queue (list requests, filter by status, approve/reject/start buttons)
4. [ ] Sentence set management (create system sets, add/edit/delete sentences)
5. [ ] Stats overview (total users, requests, trained voices)

## API Endpoints Used
- `GET /api/v1/admin/training-queue`
- `POST /api/v1/admin/training-queue/{id}/approve`
- `POST /api/v1/admin/training-queue/{id}/reject`
- `POST /api/v1/admin/training-queue/{id}/start`
- `GET /api/v1/sentences/sets` (admin CRUD)

## Test Criteria
- [ ] Non-admin → redirect away
- [ ] Admin sees all training requests
- [ ] Approve → status changes to "approved"
- [ ] Start → training begins, progress updates
- [ ] Manage sentence sets

---
Next Phase: → phase-08-polish.md
