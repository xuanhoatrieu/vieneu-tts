# Phase 05: Sentence Sets
Status: ⬜ Pending
Dependencies: Phase 02

## Objective
CRUD cho sentence sets (bộ câu thu âm). Admin quản lý system sets, users tạo custom sets. Hỗ trợ categories và language filter.

## Implementation Steps
1. [ ] GET `/sentences/sets` — list sets (filter by category, language)
2. [ ] GET `/sentences/sets/{id}` — get set with all sentences
3. [ ] POST `/sentences/sets` — create custom set (user) hoặc system set (admin)
4. [ ] PUT/DELETE `/sentences/sets/{id}` — update/delete (permission check)
5. [ ] POST/PUT/DELETE `/sentences/sentences/{id}` — CRUD individual sentences

## Sentence Set Categories
- `basic` — Câu thông thường (giới thiệu, chào hỏi)
- `tech` — Thuật ngữ kỹ thuật
- `emotional` — Biểu cảm (vui, buồn, giận)
- `business` — Kinh doanh, chuyên nghiệp
- `ref` — Câu tối ưu cho reference audio (Zero-shot clone)

## Permission Rules
- Admin: CRUD bất kỳ set nào (system + custom)
- User: Chỉ CRUD custom sets do mình tạo
- System sets: Ai cũng xem được, chỉ admin sửa/xóa

## Seed Data (system sets)
- "Bộ câu tiếng Việt cơ bản" — 50 câu, language: vi
- "Bộ câu reference tối ưu" — 10 câu ngắn 3-5s cho ref audio

## Files to Create
- `web/backend/api/v1/sentences.py`
- `web/backend/schemas/sentence.py`

## Test Criteria
- [ ] List/filter sets by category + language
- [ ] User tạo custom set + thêm/bớt câu
- [ ] Admin quản lý system sets
- [ ] Non-admin không sửa được system sets → 403

---
Next Phase: → phase-06-recording.md
