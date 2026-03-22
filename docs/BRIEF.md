# 💡 BRIEF: VieNeu — Vietnamese TTS Platform (v2 — Full Features)

**Ngày tạo:** 2026-03-20 | **Cập nhật:** 2026-03-20

---

## 1. MỤC TIÊU

Xây dựng nền tảng TTS tiếng Việt dựa trên **kiến trúc gốc VieNeu-TTS**, bổ sung đầy đủ các tính năng từ viF5TTS: recording studio, voice training workflow, sentence management, trained voice management, REST API, multi-user.

> ⚠️ **Nguyên tắc**: VieNeu-TTS là nền tảng. Gọi `Vieneu()` SDK trực tiếp, KHÔNG tạo wrapper. Mọi tính năng thêm phải phù hợp với kiến trúc VieNeu.

---

## 2. KIẾN TRÚC GỐC VIENEU-TTS (GIỮ NGUYÊN)

```
src/vieneu/
├── base.py          # BaseVieneuTTS → voice mgmt, encode/decode, watermark
├── factory.py       # Vieneu() → standard/fast/remote/xpu
├── standard.py      # VieNeuTTS: GGUF + PyTorch, batch, stream, LoRA loading
├── fast.py          # FastVieNeuTTS: LMDeploy GPU optimized
├── remote.py        # RemoteVieNeuTTS: API client
└── serve.py         # LMDeploy API server

finetune/
├── train.py         # LoRA training (peft + transformers)
├── merge_lora.py    # Merge adapter → base model
├── create_voices_json.py  # Tạo voices.json cho model
├── configs/lora_config.py # r=16, alpha=32, target all proj
└── data_scripts/
    ├── filter_data.py    # Lọc audio 3-15s, text valid
    └── encode_data.py    # Encode audio → NeuCodec codes
```

---

## 3. TÍNH NĂNG ĐẦY ĐỦ (Tham khảo từ viF5TTS)

### 🚀 MVP — Nhóm 1: Core TTS API
| # | Tính năng | VieNeu có? | Ghi chú |
|---|-----------|-----------|---------|
| 1 | REST API server (FastAPI) | ⚠️ có streaming đơn giản | Cần build full API |
| 2 | Auth (JWT + API Key) | ❌ | |
| 3 | Multi-user (user isolation) | ❌ | |
| 4 | Database (PostgreSQL) | ❌ | |

### 🚀 MVP — Nhóm 2: Recording & Training
| # | Tính năng | VieNeu có? | Ghi chú |
|---|-----------|-----------|---------|
| 5 | **Sentence Sets** — bộ câu thu âm | ❌ | System sets (admin quản lý) + Custom sets (user tạo) |
| 6 | **Browser Recording** — thu âm trong web UI | ❌ | Upload audio per sentence, auto-resample 24kHz mono |
| 7 | **Ref audio từ recordings** — dùng bản ghi làm ref | ❌ | Config sẵn câu tối ưu cho ref audio (Zero-shot) |
| 8 | **Reference Audio Management** — lưu & reuse nhiều giọng | ❌ | Upload, pre-encode, thêm/bớt nhiều refs |
| 9 | **Training Request** — user gửi yêu cầu finetune | ❌ | Min 10 recordings, status: pending→approved→training→completed |
| 10 | **Admin Approval** — admin duyệt & bắt đầu train | ❌ | Admin chọn base model, start training |
| 11 | **Training Runner** — chạy finetune LoRA tự động | ⚠️ có scripts CLI | Cần tích hợp vào backend (background task) |
| 12 | **Trained Voices** — sử dụng checkpoint đã train | ⚠️ có `load_lora_adapter` | Cần UI: list, rename, soft-delete, activate |

### 💭 Backlog
| # | Tính năng | Ghi chú |
|---|-----------|---------|
| 13 | Modern Web UI (Next.js) | Thay Gradio |
| 14 | Admin Dashboard | Training queue, user mgmt |
| 15 | Python SDK client | Remote SDK client |

---

## 4. LUỒNG CHÍNH (Workflow)

### 4.1. Zero-shot Voice Cloning (qua API)
```
User → Upload ref audio (3-5s) → tts.encode_reference() → Save ref_codes
User → POST /synthesize-with-ref → tts.infer(ref_codes=...) → Audio output
```

### 4.2. Recording + Training (Full workflow)
```
┌──────────────────────────────────────────────────────────────────┐
│  1️⃣ Admin tạo Sentence Set (bộ câu)                             │
│     - System sets: câu chuẩn để thu âm (basic, tech, emotional) │
│     - User cũng có thể tự tạo custom set                       │
├──────────────────────────────────────────────────────────────────┤
│  2️⃣ User thu âm từng câu (Recording Studio)                     │
│     - Browser recording hoặc upload file                         │
│     - Auto-resample 24kHz mono, validate 1-30s                   │
│     - Xem lại, re-record nếu cần                                │
├──────────────────────────────────────────────────────────────────┤
│  3️⃣ User gửi Training Request                                   │
│     - Chọn sentence set đã thu âm (min 10 recordings)            │
│     - Đặt tên voice                                              │
│     - Status: pending                                            │
├──────────────────────────────────────────────────────────────────┤
│  4️⃣ Admin duyệt (Approve)                                       │
│     - Xem training queue                                         │
│     - Chọn base model (VieNeu-TTS-0.3B / 0.5B)                  │
│     - Approve → status: approved                                 │
├──────────────────────────────────────────────────────────────────┤
│  5️⃣ Admin bắt đầu Training (Start)                              │
│     - Backend chạy VieNeu finetune pipeline:                     │
│       recordings → metadata.csv → filter → encode (NeuCodec)    │
│       → LoRA training (r=16, ~5000 steps) → save adapter        │
│     - Status: training → completed                               │
│     - Progress tracking (% steps)                                │
├──────────────────────────────────────────────────────────────────┤
│  6️⃣ Trained Voice xuất hiện trong danh sách user                 │
│     - tts.load_lora_adapter(checkpoint_path)                     │
│     - User dùng trained voice để synthesize                      │
│     - Có thể rename, soft-delete                                 │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3. Ref Audio từ Recording (tối ưu)
```
Admin cấu hình "câu ref" tối ưu cho Zero-shot → Sentence Set loại "ref"
User thu âm → Audio tự động dùng làm ref (đã resample, clean)
User thêm/bớt nhiều ref voices từ recordings
```

---

## 5. VieNeu FINETUNE PIPELINE (đã có sẵn)

VieNeu đã có pipeline finetune hoàn chỉnh, cần tích hợp vào backend:

| Step | Script VieNeu | Tích hợp backend |
|------|--------------|-------------------|
| Chuẩn bị data | `metadata.csv` (filename\|text) | `recording_service.generate_metadata_csv()` |
| Lọc data | `filter_data.py` (3-15s, text valid) | Import trực tiếp |
| Encode audio | `encode_data.py` (NeuCodec → codes) | Import trực tiếp |
| Training | `train.py` (LoRA, peft+transformers) | Background task |
| Merge (optional) | `merge_lora.py` | Admin trigger |
| Voices.json | `create_voices_json.py` | Auto sau training |
| Load runtime | `tts.load_lora_adapter(path)` | SDK method có sẵn |

---

## 6. DATABASE MỞ RỘNG (so với design trước)

Cần **10 bảng** (giống viF5TTS):

| Bảng | Mục đích |
|------|----------|
| `users` | Thông tin user, role (user/admin) |
| `sentence_sets` | Bộ câu (system/custom, category, language) |
| `sentences` | Từng câu trong bộ (text, order_index) |
| `recordings` | Audio thu âm per sentence per user |
| `user_references` | Ref audio đã encode cho voice cloning |
| `training_requests` | Yêu cầu finetune (status workflow) |
| `trained_voices` | Voices đã train (checkpoint, ref, active) |
| `api_keys` | API keys per user |
| `audio_history` | Lịch sử synthesis |
| `audio_config` | Cấu hình audio tối ưu cho recording |

---

## 7. ƯỚC TÍNH SƠ BỘ

| Phase | Nội dung | Thời gian |
|-------|---------|-----------|
| **MVP Nhóm 1** | Core API + Auth + DB + Refs | 1-2 tuần |
| **MVP Nhóm 2** | Sentences + Recording + Training + Trained Voices | 2-3 tuần |
| **Backlog** | Next.js UI + Admin Dashboard | 3-4 tuần |

---

## 8. BƯỚC TIẾP THEO

→ Cập nhật `/plan` và `/design` với đầy đủ tính năng recording + training
