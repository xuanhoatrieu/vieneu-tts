"""
OmniVoice Service — singleton wrapper around OmniVoice TTS.
Supports voice cloning, voice design, and auto voice with SEA-G2P text normalization.

Reference: https://huggingface.co/k2-fsa/OmniVoice
"""
import os
import uuid
import time
import wave
import threading
from pathlib import Path
from typing import Optional

from app.core.config import settings


def get_gpu_free_mb(gpu_id: int = 0) -> int:
    """Get free VRAM on a specific GPU."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits", f"--id={gpu_id}"],
            capture_output=True, text=True, timeout=5,
        )
        return int(result.stdout.strip())
    except Exception:
        return 0


class OmniVoiceService:
    """Singleton OmniVoice service with lazy model loading."""

    _instance: Optional["OmniVoiceService"] = None
    _model = None
    _normalizer = None
    _initialized = False
    _is_loading: bool = False
    _loading_error: str = ""
    _lock = threading.Lock()

    # Config
    MODEL_REPO = "k2-fsa/OmniVoice"
    DEVICE = "cuda:0"
    SAMPLE_RATE = 24000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self):
        """Lazy-load model on first call."""
        if self._initialized:
            return
        if self._is_loading:
            raise RuntimeError("OmniVoice model đang được nạp, vui lòng chờ...")

        self._is_loading = True
        try:
            self._load_model()
        finally:
            self._is_loading = False

    def _load_model(self):
        """Load OmniVoice model + SEA-G2P normalizer."""
        import torch

        t0 = time.time()
        print(f"🔄 Loading OmniVoice model: {self.MODEL_REPO} on {self.DEVICE}...")

        from omnivoice import OmniVoice
        self._model = OmniVoice.from_pretrained(
            self.MODEL_REPO,
            device_map=self.DEVICE,
            dtype=torch.float16,
        )

        # Load SEA-G2P normalizer for Vietnamese text
        try:
            from sea_g2p import Normalizer
            self._normalizer = Normalizer(lang="vi")
            print("🦭 SEA-G2P normalizer loaded for Vietnamese")
        except Exception as e:
            print(f"⚠️ SEA-G2P normalizer not available: {e}")
            self._normalizer = None

        elapsed = time.time() - t0
        self._initialized = True
        print(f"🌍 OmniVoice loaded in {elapsed:.1f}s on {self.DEVICE}")

    def _normalize_text(self, text: str) -> str:
        """Normalize Vietnamese text using SEA-G2P (numbers, dates, currencies, etc.)."""
        if self._normalizer is None:
            return text
        try:
            result = self._normalizer.normalize(text)
            if result != text:
                print(f"   📝 Normalized: '{text}' → '{result}'")
            return result
        except Exception as e:
            print(f"⚠️ Normalization failed, using raw text: {e}")
            return text

    def get_status(self) -> dict:
        """Get model status for API."""
        gpu_free = get_gpu_free_mb(0)
        return {
            "initialized": self._initialized,
            "is_loading": self._is_loading,
            "error": self._loading_error,
            "model_repo": self.MODEL_REPO,
            "device": self.DEVICE,
            "gpu_free_mb": gpu_free,
            "has_normalizer": self._normalizer is not None,
        }

    def generate_clone(
        self, text: str, ref_audio_path: str,
        ref_text: str | None = None,
        speed: float = 1.0, num_step: int = 32,
        normalize: bool = True,
    ) -> tuple[str, float | None, float]:
        """Voice cloning — generate speech using reference audio."""
        self._ensure_initialized()
        start = time.time()

        if normalize:
            text = self._normalize_text(text)

        output_dir = os.path.join(settings.STORAGE_PATH, "outputs", "omnivoice")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{uuid.uuid4()}.wav")

        kwargs = {
            "text": text,
            "ref_audio": ref_audio_path,
            "speed": speed,
            "num_step": num_step,
        }
        if ref_text:
            kwargs["ref_text"] = ref_text

        import torchaudio
        audio = self._model.generate(**kwargs)
        torchaudio.save(output_path, audio[0], self.SAMPLE_RATE)

        elapsed = time.time() - start
        duration = self._get_audio_duration(output_path)
        print(f"🎵 OmniVoice clone: {duration:.1f}s audio in {elapsed:.1f}s")
        return output_path, duration, elapsed

    def generate_design(
        self, text: str, instruct: str,
        speed: float = 1.0, num_step: int = 32,
        normalize: bool = True,
    ) -> tuple[str, float | None, float]:
        """Voice design — generate speech with attribute instructions."""
        self._ensure_initialized()
        start = time.time()

        if normalize:
            text = self._normalize_text(text)

        output_dir = os.path.join(settings.STORAGE_PATH, "outputs", "omnivoice")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{uuid.uuid4()}.wav")

        import torchaudio
        audio = self._model.generate(
            text=text, instruct=instruct,
            speed=speed, num_step=num_step,
        )
        torchaudio.save(output_path, audio[0], self.SAMPLE_RATE)

        elapsed = time.time() - start
        duration = self._get_audio_duration(output_path)
        print(f"🎵 OmniVoice design: {duration:.1f}s audio in {elapsed:.1f}s")
        return output_path, duration, elapsed

    def generate_auto(
        self, text: str,
        speed: float = 1.0, num_step: int = 32,
        normalize: bool = True,
    ) -> tuple[str, float | None, float]:
        """Auto voice — generate speech with auto-selected voice."""
        self._ensure_initialized()
        start = time.time()

        if normalize:
            text = self._normalize_text(text)

        output_dir = os.path.join(settings.STORAGE_PATH, "outputs", "omnivoice")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{uuid.uuid4()}.wav")

        import torchaudio
        audio = self._model.generate(
            text=text, speed=speed, num_step=num_step,
        )
        torchaudio.save(output_path, audio[0], self.SAMPLE_RATE)

        elapsed = time.time() - start
        duration = self._get_audio_duration(output_path)
        print(f"🎵 OmniVoice auto: {duration:.1f}s audio in {elapsed:.1f}s")
        return output_path, duration, elapsed

    def _get_audio_duration(self, path: str) -> float | None:
        try:
            with wave.open(path, "rb") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            return None


# Singleton
omnivoice_service = OmniVoiceService()
