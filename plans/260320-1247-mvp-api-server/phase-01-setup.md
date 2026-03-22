# Phase 01: Setup Environment
Status: ⬜ Pending
Dependencies: None

## Objective
Chuẩn bị môi trường phát triển: cài VieNeu-TTS SDK, tạo project FastAPI backend, cấu hình PostgreSQL.

## Implementation Steps
1. [ ] Cài dependencies VieNeu-TTS (`uv sync` trong `VieNeu-TTS/`)
2. [ ] Cài eSpeak NG (`sudo apt install espeak-ng`)
3. [ ] Test VieNeu-TTS SDK chạy OK (`python examples/main.py`)
4. [ ] Tạo FastAPI project (`web/backend/`) với cấu trúc chuẩn
5. [ ] Setup PostgreSQL database (`vietneu_tts`)
6. [ ] Tạo `.env` config cho backend

## Files to Create
- `web/backend/main.py` — FastAPI app entrypoint
- `web/backend/core/config.py` — Settings (Pydantic BaseSettings)
- `web/backend/core/database.py` — SQLAlchemy async engine
- `web/backend/requirements.txt` — Dependencies
- `web/backend/.env` — Environment variables

## Test Criteria
- [ ] `uv run vieneu-web` chạy Gradio UI thành công
- [ ] `python -c "from vieneu import Vieneu; print('OK')"` pass
- [ ] FastAPI chạy tại `http://localhost:8000/docs`
- [ ] PostgreSQL connection OK

---
Next Phase: → phase-02-database.md
