# 🎨 DESIGN: VieNeu TTS Frontend

Ngày tạo: 2026-03-20
Dựa trên: 6 UI mockups + 42 backend API endpoints

---

## 1. Design System (CSS Tokens)

### Colors (Dark Theme — từ mockups)
```css
--bg-primary:    #0d1117    /* Nền chính (gần đen) */
--bg-secondary:  #161b22    /* Nền sidebar, cards */
--bg-card:       #1c2333    /* Card background */
--bg-hover:      #252d3a    /* Hover state */
--bg-input:      #0d1117    /* Input fields */

--accent:        #6366f1    /* Tím chủ đạo (indigo-500) */
--accent-hover:  #818cf8    /* Hover tím sáng */
--accent-glow:   rgba(99, 102, 241, 0.15)  /* Glassmorphism glow */

--text-primary:  #e6edf3    /* Text chính (trắng nhạt) */
--text-secondary:#8b949e    /* Text phụ (xám) */
--text-muted:    #484f58    /* Placeholder */

--border:        #30363d    /* Viền card, input */
--border-active: #6366f1    /* Viền focus */

--success:       #3fb950    /* Xanh lá — recorded, completed */
--warning:       #d29922    /* Vàng — pending, training */
--danger:        #f85149    /* Đỏ — error, reject, record btn */
--info:          #58a6ff    /* Xanh dương — approved */
```

### Typography
```css
--font-family: 'Inter', -apple-system, sans-serif;
--font-mono:   'JetBrains Mono', monospace;

--text-xs:   0.75rem    /* 12px — badges */
--text-sm:   0.875rem   /* 14px — secondary text */
--text-base: 1rem       /* 16px — body */
--text-lg:   1.125rem   /* 18px — subheadings */
--text-xl:   1.25rem    /* 20px — page titles */
--text-2xl:  1.5rem     /* 24px — hero text */
```

### Spacing & Radius
```css
--space-1: 4px   --space-2: 8px   --space-3: 12px
--space-4: 16px  --space-5: 20px  --space-6: 24px
--space-8: 32px  --space-10: 40px

--radius-sm: 6px   --radius-md: 8px
--radius-lg: 12px  --radius-xl: 16px

--shadow-card: 0 1px 3px rgba(0,0,0,0.3);
--shadow-glass: 0 8px 32px rgba(0,0,0,0.4);
```

### Glassmorphism (Login card)
```css
.glass-card {
  background: rgba(22, 27, 34, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  border-radius: var(--radius-xl);
}
```

---

## 2. Component Tree

```
App
├── AuthProvider (JWT context)
├── Routes
│   ├── /login          → LoginPage
│   ├── /register       → RegisterPage
│   └── ProtectedLayout (sidebar + topbar)
│       ├── /studio     → TTSStudioPage
│       ├── /voices     → VoiceLibraryPage
│       ├── /recording  → RecordingStudioPage
│       ├── /training   → TrainingPage
│       ├── /api-keys   → APIKeysPage
│       └── /admin/*    → AdminLayout (admin only)
│           ├── /admin/dashboard → AdminDashboard
│           ├── /admin/queue     → TrainingQueue
│           └── /admin/sets      → SentenceSetManager
```

---

## 3. Shared Components

| Component | Mô tả | Dùng ở |
|-----------|--------|--------|
| `Sidebar` | Menu trái: logo, nav links, user avatar | Mọi trang (trừ login) |
| `TopBar` | Tiêu đề trang + actions (share, notifications) | Mọi trang |
| `AudioPlayer` | Play/pause, progress bar, download, volume | Studio, Library, Recording |
| `AudioRecorder` | Record button (đỏ), waveform live, timer | Recording Studio |
| `FileDropZone` | Drag & drop area + browse button | Library upload, TTS custom |
| `StatusBadge` | Badge màu: pending/approved/training/completed | Training, Admin |
| `Modal` | Dialog overlay (confirm, upload form) | Library, Training |
| `Toast` | Notification popup (success, error) | Global |
| `ProgressBar` | Bar ngang có % | Recording, Training |
| `EmptyState` | Icon + text "chưa có data" + CTA button | Library, Training |
| `LoadingSpinner` | Spinner khi đang fetch/generate | Global |

---

## 4. Page Designs (Chi tiết từ mockups)

### 4.1. Login Page
```
┌─────────────────────────────────────────┐
│           (gradient background)          │
│                                          │
│    ┌────────────────────────────┐        │
│    │  🔊 VieNeu TTS             │  Glass │
│    │  Vietnamese TTS Platform   │  Card  │
│    │                            │        │
│    │  📧 Email                  │        │
│    │  🔒 Password               │        │
│    │  [    Đăng nhập     ]      │  Btn   │
│    │  Chưa có? Đăng ký          │        │
│    └────────────────────────────┘        │
└─────────────────────────────────────────┘
```

### 4.2. TTS Studio (Trang chính)
```
┌──────┬──────────────────────┬────────┐
│      │  VieNeu TTS Studio   │ Share  │
│ Side │                      │        │
│ bar  │  ┌─────────────────────────┐  │
│      │  │ Nhập văn bản...         │  │ Cài đặt
│ TTS  │  │ (textarea lớn)          │  │ Temp: 0.7
│ Voice│  │                         │  │ Mode: Fast
│ Rec  │  └─────────────────────────┘  │
│ Train│                               │
│ API  │  Voice: [Dropdown ▼] [Tổng hợp]│
│      │                               │
│      │  Kết quả âm thanh:            │
│      │  ┌─────────────────────────┐  │
│ User │  │ ▶ ████████░░ 00:38  🔊 │  │
│ avatar│ │ Huyen_Output.mp3    ⬇  │  │
│      │  └─────────────────────────┘  │
└──────┴───────────────────────┴───────┘
```

### 4.3. Voice Library (Grid 3 cột)
```
┌──────┬──────────────────────────────┐
│      │  Voice Library / References   │
│ Side │                 [+ Upload Ref]│
│      │  ┌─────┐ ┌─────┐ ┌─────┐    │
│      │  │Name │ │Name │ │Name │    │
│      │  │4.2s │ │3.5s │ │5.1s │    │
│      │  │▶  🗑│ │▶  🗑│ │▶  🗑│    │
│      │  └─────┘ └─────┘ └─────┘    │
│      │                              │
│      │  Upload Modal:               │
│      │  ┌──────────────────────┐    │
│      │  │ Drag & drop files    │    │
│      │  │ Transcript: [____]   │    │
│      │  │ Name: [____]         │    │
│      │  │ Language: [vi ▼]     │    │
│      │  └──────────────────────┘    │
└──────┴──────────────────────────────┘
```

### 4.4. Recording Studio
```
┌──────┬──────────────────────────────┐
│      │  Recording Studio    12/50   │
│ Side │  Set: [Bộ câu cơ bản ▼]     │
│      │                              │
│      │  1  Xin chào, tôi là... 🎙✅ 3.2s│
│      │  2  Xin chào, tôi là... 🎙✅ 3.2s│
│      │  3  Xin chào, tôi là... 🎙✅ 3.2s│
│      │  ┌──────────────────────┐    │
│      │  │ 5  Xin chào...      │    │
│      │  │ 🔴 ▕██████░░▏ 00:04 ■│ ← Active│
│      │  └──────────────────────┘    │
│      │  6  Tôi chú tâm...     ▶ ⬜ │
│      │                              │
│      │  ██████░░░░ 12/50 câu       │
│      │        [Gửi yêu cầu Training]│
└──────┴──────────────────────────────┘
```

### 4.5. Admin Dashboard
```
┌──────┬──────────────────────────────┐
│Admin │  Admin Dashboard              │
│      │  ┌────┐┌────┐┌────┐┌────┐   │
│Dash  │  │ 24 ││  3 ││  1 ││ 15 │   │
│Queue │  │User││Wait││Run ││Done│   │
│Sets  │  └────┘└────┘└────┘└────┘   │
│Users │                              │
│      │  Training Queue              │
│      │  ─────────────────────────   │
│      │  user@.. VieNeu1 [pending] [Approve][Reject]│
│      │  user@.. VieNeu2 [approved] [Start Training]│
│      │  user@.. VieNeu3 [training] ████░ 49%       │
│      │  user@.. VieNeu4 [completed] ✅              │
└──────┴──────────────────────────────┘
```

---

## 5. API ↔ Page Mapping

| Page | API Calls | Trigger |
|------|-----------|---------|
| **Login** | `POST /auth/login` | Form submit |
| **Register** | `POST /auth/register` | Form submit |
| **TTS Studio** | `GET /tts/voices`, `GET /refs`, `POST /tts/synthesize`, `POST /tts/synthesize-with-ref`, `POST /tts/synthesize-custom` | Page load, button |
| **Voice Library** | `GET /refs`, `POST /refs`, `DELETE /refs/{id}`, `GET /refs/{id}/audio` | Page load, upload, delete |
| **Recording** | `GET /sentences/sets`, `GET /sentences/sets/{id}`, `POST /training/recordings/{set}/{sent}`, `GET /training/recordings/{set}`, `GET /training/recordings/audio/{id}` | Page load, record |
| **Training** | `GET /training/base-models`, `POST /training/requests`, `GET /training/requests`, `DELETE /training/requests/{id}`, `GET /training/voices`, `PUT /training/voices/{id}`, `DELETE /training/voices/{id}` | Page load, submit |
| **Admin** | `GET /admin/training-queue`, `POST /admin/.../approve`, `POST /admin/.../reject`, `POST /admin/.../start` | Page load, actions |

---

## 6. State Management

```
AuthContext
├── user: { id, email, name, role }
├── token: string (JWT)
├── login(email, password)
├── register(email, password, name)
├── logout()
└── isAdmin: boolean

// Không cần global state phức tạp
// Mỗi page tự fetch data (local state)
// Audio playback = component-local
```

---

## 7. User Journeys

### Journey 1: Người dùng mới → Tổng hợp giọng nói
```
Login → TTS Studio → Nhập text → Chọn preset voice
→ Bấm "Tổng hợp" → Nghe audio → Download
```

### Journey 2: Voice Cloning (Zero-shot)
```
Voice Library → Upload ref audio (3-5s) → Đặt tên
→ TTS Studio → Chọn ref voice → Nhập text → Generate → Cloned!
```

### Journey 3: Training Custom Voice
```
Recording Studio → Chọn sentence set → Thu âm 15+ câu
→ Training → Submit request → (Đợi admin approve)
→ Admin approve + start → Training complete
→ TTS Studio → Chọn trained voice → Generate
```

### Journey 4: Admin quản lý
```
Admin Dashboard → Xem stats → Training Queue
→ Review request → Approve → Start Training
→ Monitor progress → Complete
```

---

## 8. Responsive Strategy

| Breakpoint | Layout |
|------------|--------|
| Desktop (≥1280px) | Sidebar 240px + Content |
| Tablet (768-1279px) | Sidebar collapsed (icon only 60px) + Content |
| Mobile (<768px) | Sidebar hidden, hamburger menu |

---

*Tạo bởi AWF — Design Phase | Backend: 42 endpoints ready*
