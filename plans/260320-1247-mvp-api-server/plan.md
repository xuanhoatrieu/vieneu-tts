# Plan: VieNeu TTS Platform — Full Feature Set
Created: 2026-03-20
Status: 🟡 In Progress

## Overview
Nền tảng TTS tiếng Việt trên kiến trúc VieNeu-TTS: REST API, multi-user, recording studio, voice training (LoRA finetune), trained voice management. Gọi `Vieneu()` SDK trực tiếp.

## Tech Stack
- **TTS Engine**: VieNeu-TTS SDK (`Vieneu()` factory)
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **Database**: PostgreSQL (10 tables)
- **Auth**: JWT + API Key
- **Training**: VieNeu LoRA pipeline (peft + transformers + NeuCodec)
- **Server**: 2x RTX A4000

## Architecture

```
┌────────────────────────────────────────────────────┐
│              Client (SDK / Web UI)                  │
└───────────────────┬────────────────────────────────┘
                    │ REST API
┌───────────────────▼────────────────────────────────┐
│            FastAPI Backend (web/backend/)           │
│                                                    │
│  Auth ─── TTS API ─── Refs ─── Sentences           │
│   │         │           │          │               │
│   │    tts_service     │     Recording            │
│   │    (Vieneu SDK)    │     Studio               │
│   │         │           │          │               │
│   │         │           │    Training              │
│   │         │           │    Requests              │
│   │         │           │      │                   │
│   │         │           │    Admin                 │
│   │         │           │    Approve               │
│   │         │           │      │                   │
│   │         │           │    Training              │
│   │         │           │    Runner                │
│   │         │           │    (LoRA finetune)       │
│   │         │           │      │                   │
│   │         │           │    Trained               │
│   │         │           │    Voices                │
│   │         │           │                          │
│   └─── PostgreSQL (10 tables) ─────────────────────│
└────────────────────────────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────────┐
│      VieNeu-TTS SDK (giữ nguyên, KHÔNG sửa)       │
│  Vieneu() → infer / encode_reference /             │
│             load_lora_adapter / list_preset_voices  │
│  finetune/ → filter → encode → train → merge      │
└────────────────────────────────────────────────────┘
```

## Phases

| Phase | Name | Status | Tasks |
|-------|------|--------|-------|
| 01 | Setup Environment | ⬜ Pending | 6 |
| 02 | Database Schema (10 tables) | ⬜ Pending | 6 |
| 03 | Auth System | ⬜ Pending | 5 |
| 04 | TTS API + Refs | ⬜ Pending | 7 |
| 05 | Sentence Sets | ⬜ Pending | 5 |
| 06 | Recording Studio | ⬜ Pending | 6 |
| 07 | Training Workflow | ⬜ Pending | 7 |
| 08 | Trained Voices + Admin | ⬜ Pending | 6 |
| 09 | Testing & Deploy | ⬜ Pending | 7 |

**Tổng:** 55 tasks | Ước tính: 3-4 tuần

## Quick Commands
- Start: `/code phase-01`
- Design chi tiết: `/design`
- Check progress: `/next`
