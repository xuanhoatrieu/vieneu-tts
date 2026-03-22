# Phase 03: TTS Studio
Status: ⬜ Pending
Dependencies: Phase 02

## Objective
Trang chính để nhập text và synthesize giọng nói. Theo mockup `tts_studio.png`.

## Implementation Steps
1. [ ] TTS Studio page layout (text input, voice selector, generate button)
2. [ ] Voice preset selector (GET /tts/voices, dropdown/cards)
3. [ ] Text input area (textarea, character count, clear button)
4. [ ] Synthesize preset (POST /tts/synthesize → audio player)
5. [ ] Audio player component (play/pause, download, waveform visualization)
6. [ ] Synthesize with reference (POST /tts/synthesize-with-ref, ref selector)
7. [ ] Custom audio upload for zero-shot (POST /tts/synthesize-custom, drag & drop)

## API Endpoints Used
- `GET /api/v1/tts/voices`
- `POST /api/v1/tts/synthesize`
- `POST /api/v1/tts/synthesize-with-ref`
- `POST /api/v1/tts/synthesize-custom`
- `GET /api/v1/tts/audio/{filename}`
- `GET /api/v1/refs` (for ref voice selector)

## Test Criteria
- [ ] Chọn preset voice → generate → nghe audio
- [ ] Chọn ref voice → generate → cloned voice audio
- [ ] Upload custom audio → generate → zero-shot clone
- [ ] Audio player: play, pause, download
- [ ] Loading state khi đang generate

---
Next Phase: → phase-04-voice-library.md
