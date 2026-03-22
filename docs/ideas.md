# Ý tưởng dự án VieNeu

## Mục tiêu
- Xây dựng app Vietnamese Text-to-Speech sử dụng model VieNeu-TTS
- Dựa trên kiến trúc app viF5TTS đã có, adapt cho VieNeu-TTS

## Tính năng chính (dự kiến)
- Text-to-Speech tiếng Việt chất lượng cao (24kHz)
- Voice Cloning từ audio tham chiếu (3-5 giây)
- Hỗ trợ nhiều mode: standard, fast (GPU), remote, streaming
- Web UI (Gradio) để demo và sử dụng
- API endpoint để tích hợp

## Nguồn tham khảo
- VieNeu-TTS: https://github.com/pnnbao97/VieNeu-TTS
- SDK Docs: https://docs.vieneu.io/docs/sdk/overview/
- App viF5TTS gốc: https://github.com/xuanhoatrieu/viF5TTS
