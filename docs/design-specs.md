# Design Specifications — VieNeu TTS Platform

## 🎨 Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Primary | `#6366f1` | Buttons, links, accent |
| Primary Hover | `#4f46e5` | Hover states |
| Success | `#10b981` | Success messages, online status |
| Warning | `#f59e0b` | Warnings |
| Error | `#ef4444` | Errors, delete |
| Background | `#0f172a` | Main background |
| Surface | `#1e293b` | Cards, modals, sidebar |
| Surface Light | `#334155` | Input fields, hover |
| Text Primary | `#f1f5f9` | Main text |
| Text Secondary | `#94a3b8` | Descriptions, labels |
| Border | `#334155` | Borders, dividers |

## 📝 Typography

**Font Family**: Inter (Google Fonts)

| Element | Size | Weight | Letter Spacing |
|---------|------|--------|---------------|
| H1 (Page title) | 28px | 700 | -0.02em |
| H2 (Section) | 22px | 600 | -0.01em |
| H3 (Card title) | 16px | 600 | 0 |
| Body | 14px | 400 | 0 |
| Small | 12px | 400 | 0 |
| Button | 14px | 500 | 0.02em |

## 📐 Spacing

| Name | Value |
|------|-------|
| xs | 4px |
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |
| 2xl | 48px |

## 🔲 Border Radius

| Name | Value | Usage |
|------|-------|-------|
| sm | 6px | Inputs, small buttons |
| md | 8px | Cards, panels |
| lg | 12px | Modals, large cards |
| full | 9999px | Badges, avatars |

## 🌫️ Shadows

| Name | Value |
|------|-------|
| sm | `0 1px 2px rgba(0,0,0,0.3)` |
| md | `0 4px 12px rgba(0,0,0,0.25)` |
| lg | `0 8px 24px rgba(0,0,0,0.3)` |

## 📱 Breakpoints

| Name | Width |
|------|-------|
| mobile | 640px |
| tablet | 768px |
| desktop | 1280px |

## ✨ Animations

| Name | Duration | Easing |
|------|----------|--------|
| fast | 150ms | ease-out |
| normal | 250ms | ease-in-out |
| slow | 400ms | ease-in-out |

## 🖼️ Screen Inventory

| # | Screen | Priority | Mockup |
|---|--------|----------|--------|
| 1 | Login / Register | MVP | ✅ |
| 2 | TTS Studio | MVP | ✅ |
| 3 | Voice Library (Refs) | MVP | ✅ |
| 4 | Recording Studio | MVP | ✅ |
| 5 | Training & Trained Voices | MVP | ✅ |
| 6 | Admin Dashboard | MVP | ✅ |
| 7 | API Keys | MVP | — |
| 8 | History | Phase 2 | — |

## 🧩 Component Library

### Sidebar Navigation
- Width: 220px (desktop), collapsed on mobile
- Active item: indigo bg with white text
- Hover: surface light bg

### Text Input Area
- Min height: 160px
- Placeholder text in muted color
- Character count at bottom right

### Voice Selector
- Dropdown with voice name + description
- Play button for preview
- Grouped by language (VI/EN)

### Audio Player
- Waveform visualization
- Play/Pause, Download buttons
- Duration display
- Indigo waveform bars

### Reference Card
- Surface bg, md border-radius
- Language badge (VI=indigo, EN=green)
- Duration badge
- Play + Delete action buttons

### Button Variants
- **Primary**: Indigo gradient, white text
- **Secondary**: Surface bg, border
- **Danger**: Red bg for destructive actions
- **Ghost**: Transparent, text only
