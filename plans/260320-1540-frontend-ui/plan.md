# Plan: VieNeu Frontend — Web UI
Created: 2026-03-20T15:40:00Z
Status: 🟡 Planning

## Overview
Xây dựng Web UI cho VieNeu TTS Platform sử dụng React (Vite). Backend API đã hoàn thành (42 endpoints). UI mockups đã có từ `/visualize`.

## Tech Stack
- Frontend: React 19 + Vite
- Styling: Vanilla CSS (dark theme, glassmorphism)
- State: React hooks + Context
- HTTP: fetch API
- Audio: Web Audio API + MediaRecorder
- Charts: lightweight (cho admin dashboard)
- Router: React Router v7

## UI Mockups (đã có)
1. Login page → `login_page.png`
2. TTS Studio → `tts_studio.png`
3. Voice Library → `voice_library.png`
4. Recording Studio → `recording_studio.png`
5. Training Page → `training_page.png`
6. Admin Dashboard → `admin_dashboard.png`

## API Base URL
- Dev: `http://127.0.0.1:8888/api/v1`
- Prod: `https://tts.hoclieu.id.vn/api/v1`

## Phases

| Phase | Name | Status | Tasks |
|-------|------|--------|-------|
| 01 | Project Setup + Design System | ⬜ Pending | 6 |
| 02 | Auth (Login/Register) | ⬜ Pending | 5 |
| 03 | TTS Studio | ⬜ Pending | 7 |
| 04 | Voice Library + Refs | ⬜ Pending | 5 |
| 05 | Recording Studio | ⬜ Pending | 8 |
| 06 | Training + Trained Voices | ⬜ Pending | 6 |
| 07 | Admin Dashboard | ⬜ Pending | 5 |
| 08 | Polish + Deploy | ⬜ Pending | 4 |

**Tổng:** 46 tasks | 8 phases

## Quick Commands
- Start Phase 1: `/code phase-01`
- Check progress: `/next`
- Save context: `/save-brain`
