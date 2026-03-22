"""
TTS Service — singleton wrapper around VieNeu-TTS SDK.
Supports model switching with async loading, GPU availability check, and status tracking.

SDK Reference: https://docs.vieneu.io/docs/sdk/overview
"""
import os
import uuid
import time
import wave
import threading
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import settings

# Project-local model storage (Docker sets HF_HOME=/app/models)
MODELS_DIR = os.environ.get("HF_HOME", str(Path(__file__).resolve().parent.parent.parent.parent.parent / "models"))
os.environ["HF_HOME"] = MODELS_DIR

# Available backbone models
AVAILABLE_MODELS = [
    {
        "repo": "pnnbao-ump/VieNeu-TTS-0.3B-q4-gguf",
        "name": "VieNeu 0.3B (Q4)",
        "size": "0.3B",
        "format": "GGUF Q4",
        "device": "cpu",
        "size_mb": 193,
        "description": "Nhẹ nhất, chạy CPU, tốc độ nhanh",
    },
    {
        "repo": "pnnbao-ump/VieNeu-TTS-0.3B-q8-gguf",
        "name": "VieNeu 0.3B (Q8)",
        "size": "0.3B",
        "format": "GGUF Q8",
        "device": "cpu",
        "size_mb": 350,
        "description": "Chất lượng tốt hơn Q4, chạy CPU",
    },
    {
        "repo": "pnnbao-ump/VieNeu-TTS-q4-gguf",
        "name": "VieNeu 0.5B (Q4)",
        "size": "0.5B",
        "format": "GGUF Q4",
        "device": "cpu",
        "size_mb": 398,
        "description": "Model lớn, quantize Q4, CPU",
    },
    {
        "repo": "pnnbao-ump/VieNeu-TTS-q8-gguf",
        "name": "VieNeu 0.5B (Q8)",
        "size": "0.5B",
        "format": "GGUF Q8",
        "device": "cpu",
        "size_mb": 568,
        "description": "Model lớn, chất lượng cao, CPU",
    },
    {
        "repo": "pnnbao-ump/VieNeu-TTS-0.3B",
        "name": "VieNeu 0.3B (GPU)",
        "size": "0.3B",
        "format": "PyTorch",
        "device": "gpu",
        "size_mb": 600,
        "vram_required_mb": 2000,
        "description": "Full precision, cần GPU, chất lượng tốt",
    },
    {
        "repo": "pnnbao-ump/VieNeu-TTS",
        "name": "VieNeu 0.5B (GPU)",
        "size": "0.5B",
        "format": "PyTorch",
        "device": "gpu",
        "size_mb": 1100,
        "vram_required_mb": 3000,
        "description": "Chất lượng tốt nhất, cần GPU",
    },
]


def get_gpu_status() -> list[dict]:
    """Get GPU VRAM usage via nvidia-smi. Returns list of {id, name, used_mb, total_mb, free_mb, utilization}."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        gpus = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append({
                    "id": int(parts[0]),
                    "name": parts[1],
                    "used_mb": int(parts[2]),
                    "total_mb": int(parts[3]),
                    "free_mb": int(parts[4]),
                    "utilization": int(parts[5]),
                })
        return gpus
    except Exception:
        return []


def is_gpu_available(min_free_mb: int = 2000) -> tuple[bool, list[dict]]:
    """Check if any GPU has enough free VRAM. Returns (available, gpus)."""
    gpus = get_gpu_status()
    if not gpus:
        return False, []
    available = any(g["free_mb"] >= min_free_mb for g in gpus)
    return available, gpus


class TTSService:
    """Singleton TTS service with model switching and GPU awareness."""

    _instance: Optional["TTSService"] = None
    _tts = None
    _initialized = False
    _current_model: str = ""
    _is_loading: bool = False
    _loading_error: str = ""
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self):
        """Lazy-load default model on first call."""
        if self._initialized:
            return
        if self._is_loading:
            raise RuntimeError("Model đang được nạp, vui lòng chờ...")

        default_repo = "pnnbao-ump/VieNeu-TTS-0.3B-q4-gguf"
        self._load_model_sync(default_repo)

    def _load_model_sync(self, backbone_repo: str):
        """Load a model synchronously with timing logs."""
        import time as _t
        mode = settings.VIENEU_MODE
        t0 = _t.time()
        print(f"🔄 Loading model: {backbone_repo} (mode={mode})...")

        if mode == "remote":
            from vieneu.remote import RemoteVieNeuTTS
            init_kwargs = {}
            if hasattr(settings, "VIENEU_REMOTE_API_BASE"):
                init_kwargs["api_base"] = settings.VIENEU_REMOTE_API_BASE
                init_kwargs["model_name"] = getattr(
                    settings, "VIENEU_REMOTE_MODEL", backbone_repo
                )
            self._tts = RemoteVieNeuTTS(**init_kwargs)
        elif mode == "fast":
            from vieneu.fast import FastVieNeuTTS
            self._tts = FastVieNeuTTS()
        else:
            from vieneu.standard import VieNeuTTS
            self._tts = VieNeuTTS(
                backbone_repo=backbone_repo,
                codec_repo=settings.VIENEU_CODEC_REPO,
            )

        elapsed = _t.time() - t0
        self._current_model = backbone_repo
        self._initialized = True
        print(f"🧠 VieNeu TTS loaded: {backbone_repo} in {elapsed:.1f}s (mode={mode})")

    def switch_model(self, backbone_repo: str):
        """Switch to a different backbone model asynchronously."""
        if self._is_loading:
            raise RuntimeError("Đang nạp model, vui lòng chờ...")
        if backbone_repo == self._current_model and self._initialized:
            return

        # Validate repo
        valid_repos = [m["repo"] for m in AVAILABLE_MODELS]
        if backbone_repo not in valid_repos:
            raise ValueError(f"Model không hợp lệ: {backbone_repo}")

        # Check GPU for GPU models
        model_info = next((m for m in AVAILABLE_MODELS if m["repo"] == backbone_repo), None)
        if model_info and model_info["device"] == "gpu":
            min_vram = model_info.get("vram_required_mb", 2000)
            gpu_ok, gpus = is_gpu_available(min_vram)
            if not gpu_ok:
                gpu_msg = ""
                if gpus:
                    gpu_msg = " | ".join(
                        f"GPU {g['id']}: {g['free_mb']}MB free / {g['total_mb']}MB"
                        for g in gpus
                    )
                raise RuntimeError(
                    f"GPU không đủ VRAM ({min_vram}MB cần). "
                    f"Vui lòng chờ hoặc sử dụng model CPU. [{gpu_msg}]"
                )

        self._is_loading = True
        self._loading_error = ""

        def _do_switch():
            try:
                # Unload old model
                if self._tts is not None:
                    del self._tts
                    self._tts = None
                    self._initialized = False
                    import gc
                    gc.collect()
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except ImportError:
                        pass

                self._load_model_sync(backbone_repo)
            except Exception as e:
                self._loading_error = str(e)
                print(f"❌ Model switch failed: {e}")
            finally:
                self._is_loading = False

        thread = threading.Thread(target=_do_switch, daemon=True)
        thread.start()

    def get_model_status(self) -> dict:
        """Get current model status + GPU info for API."""
        _, gpus = is_gpu_available(0)
        return {
            "current_model": self._current_model,
            "is_loading": self._is_loading,
            "is_initialized": self._initialized,
            "error": self._loading_error,
            "available_models": AVAILABLE_MODELS,
            "gpus": gpus,
        }

    @property
    def tts(self):
        self._ensure_initialized()
        return self._tts

    def synthesize_preset(
        self, text: str, voice_id: str = "", mode: str = "fast"
    ) -> tuple[str, float | None, float]:
        """Synthesize with a preset voice."""
        if self._is_loading:
            raise RuntimeError("Model đang được nạp, vui lòng chờ...")

        start = time.time()
        output_dir = os.path.join(settings.STORAGE_PATH, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{uuid.uuid4()}.wav")

        voice_data = None
        if voice_id:
            try:
                voice_data = self.tts.get_preset_voice(voice_id)
            except Exception:
                pass

        audio = self.tts.infer(text=text, voice=voice_data)
        self.tts.save(audio, output_path)

        elapsed = time.time() - start
        duration = self._get_audio_duration(output_path)
        return output_path, duration, elapsed

    def synthesize_with_ref(
        self, text: str, ref_audio_path: str, ref_text: str | None = None, mode: str = "fast",
    ) -> tuple[str, float | None, float]:
        """Synthesize with reference audio (zero-shot cloning)."""
        if self._is_loading:
            raise RuntimeError("Model đang được nạp, vui lòng chờ...")

        start = time.time()
        output_dir = os.path.join(settings.STORAGE_PATH, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{uuid.uuid4()}.wav")

        audio = self.tts.infer(text=text, ref_audio=ref_audio_path, ref_text=ref_text or "")
        self.tts.save(audio, output_path)

        elapsed = time.time() - start
        duration = self._get_audio_duration(output_path)
        return output_path, duration, elapsed

    def get_preset_voices(self) -> list[dict]:
        """Get available preset voices, sorted by region & gender."""
        # Mapping: voice_id -> (display_name, sort_order)
        VOICE_MAP = {
            "Binh":  ("North-Male-Bình",   1),
            "Tuyen": ("North-Male-Tuyên",  2),
            "Ly":    ("North-Female-Ly",    3),
            "Ngoc":  ("North-Female-Ngọc",  4),
            "Vinh":  ("South-Male-Vĩnh",   5),
            "Doan":  ("South-Female-Đoan",  6),
        }
        try:
            self._ensure_initialized()
            voices = self.tts.list_preset_voices()
            result = []
            for desc, vid in voices:
                name, order = VOICE_MAP.get(vid, (desc, 99))
                result.append({"id": vid, "name": name, "language": "vi", "_order": order})
            result.sort(key=lambda v: v["_order"])
            for v in result:
                v.pop("_order", None)
            return result
        except Exception as e:
            print(f"⚠️ Could not load preset voices: {e}")
            return [
                {"id": "Binh",  "name": "North-Male-Bình",   "language": "vi"},
                {"id": "Tuyen", "name": "North-Male-Tuyên",  "language": "vi"},
                {"id": "Ly",    "name": "North-Female-Ly",    "language": "vi"},
                {"id": "Ngoc",  "name": "North-Female-Ngọc",  "language": "vi"},
                {"id": "Vinh",  "name": "South-Male-Vĩnh",   "language": "vi"},
                {"id": "Doan",  "name": "South-Female-Đoan",  "language": "vi"},
            ]

    def encode_reference(self, audio_path: str) -> dict | None:
        try:
            self._ensure_initialized()
            return None
        except Exception as e:
            print(f"⚠️ Failed to encode reference: {e}")
            return None

    @staticmethod
    def _split_text_to_chunks(text: str, max_chars: int = 150) -> list[str]:
        """Split long text into sentence-level chunks for faster synthesis.
        TTS models have super-linear time complexity — processing 4 short chunks
        is much faster than 1 long chunk of the same total length.
        """
        import re
        # Split by sentence boundaries
        sentences = re.split(r'(?<=[.!?;:。！？])\s+', text.strip())
        chunks = []
        current = ""
        for s in sentences:
            if not s.strip():
                continue
            # If adding this sentence would exceed max_chars, flush current
            if current and len(current) + len(s) + 1 > max_chars:
                chunks.append(current.strip())
                current = s
            else:
                current = f"{current} {s}".strip() if current else s
        if current.strip():
            chunks.append(current.strip())

        # If no sentence boundaries found, split by commas or force split
        if len(chunks) == 1 and len(chunks[0]) > max_chars:
            text = chunks[0]
            chunks = []
            parts = re.split(r'(?<=[,，])\s*', text)
            current = ""
            for p in parts:
                if current and len(current) + len(p) + 1 > max_chars:
                    chunks.append(current.strip())
                    current = p
                else:
                    current = f"{current} {p}".strip() if current else p
            if current.strip():
                chunks.append(current.strip())

        return chunks if chunks else [text]

    def synthesize_with_trained_voice(
        self, text: str, checkpoint_path: str,
        ref_audio_path: str | None = None, ref_text: str | None = None,
        voice_id: str = "",
    ) -> tuple[str, float | None, float]:
        """Synthesize using a LoRA-finetuned trained voice.
        Splits long text into chunks for faster processing.
        Note: ensure_model_for_trained_voice must be called BEFORE this method
        to guarantee the correct GPU model is loaded.
        """
        # Wait for any model loading to finish (e.g. startup auto-load)
        for _ in range(120):  # wait up to 60s
            if not self._is_loading:
                break
            time.sleep(0.5)
        if self._is_loading:
            raise RuntimeError("Model đang được nạp quá lâu, vui lòng thử lại sau.")

        self._ensure_initialized()

        # Double-check: need GPU model for LoRA — GGUF models don't support adapters
        if "gguf" in self._current_model.lower():
            raise RuntimeError(
                "Trained voice cần model GPU (PyTorch). "
                "Hệ thống không thể tự chuyển. Vui lòng chọn model GPU trước."
            )

        start = time.time()
        output_dir = os.path.join(settings.STORAGE_PATH, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{uuid.uuid4()}.wav")

        try:
            # Clean up any leftover peft state from previous calls
            if hasattr(self.tts, '_lora_loaded') and self.tts._lora_loaded:
                try:
                    self.tts.unload_lora_adapter()
                    print("   🧹 Cleaned up leftover LoRA adapter")
                except Exception:
                    pass
            if hasattr(self.tts.backbone, 'peft_config'):
                try:
                    self.tts.backbone = self.tts.backbone.merge_and_unload() if hasattr(self.tts.backbone, 'merge_and_unload') else self.tts.backbone
                    self.tts._lora_loaded = False
                    print("   🧹 Cleaned up leftover peft_config")
                except Exception:
                    pass

            # Load LoRA adapter
            print(f"🔄 Loading LoRA adapter: {checkpoint_path}")
            self.tts.load_lora_adapter(checkpoint_path)

            # Build base inference kwargs (ref audio / voice)
            base_kwargs = {}
            if ref_audio_path and os.path.exists(ref_audio_path):
                base_kwargs["ref_audio"] = ref_audio_path
                base_kwargs["ref_text"] = ref_text or ""
                print(f"   📎 Using ref audio: {os.path.basename(ref_audio_path)}")
            elif voice_id:
                try:
                    base_kwargs["voice"] = self.tts.get_preset_voice(voice_id)
                except Exception:
                    pass

            # Split text into chunks for faster processing
            chunks = self._split_text_to_chunks(text, max_chars=150)
            print(f"   📝 Text split into {len(chunks)} chunk(s)")

            if len(chunks) == 1:
                # Single chunk — direct synthesis
                audio = self.tts.infer(text=chunks[0], **base_kwargs)
                self.tts.save(audio, output_path)
            else:
                # Multiple chunks — synthesize each and concatenate
                import numpy as np
                import soundfile as sf

                all_audio = []
                for i, chunk in enumerate(chunks):
                    t0 = time.time()
                    print(f"   🔊 Chunk {i+1}/{len(chunks)}: {chunk[:60]}...")
                    audio = self.tts.infer(text=chunk, **base_kwargs)
                    # Extract numpy array from audio object
                    if hasattr(audio, 'audios') and audio.audios:
                        arr = audio.audios[0]
                    elif isinstance(audio, np.ndarray):
                        arr = audio
                    else:
                        # Try saving to temp file and reading back
                        tmp = os.path.join(output_dir, f"_chunk_{i}.wav")
                        self.tts.save(audio, tmp)
                        arr, sr = sf.read(tmp)
                        os.remove(tmp)
                    all_audio.append(arr)
                    print(f"      ✅ Chunk {i+1} done ({time.time()-t0:.1f}s)")

                # Concatenate all audio arrays
                combined = np.concatenate(all_audio)
                sf.write(output_path, combined, 24000)

        finally:
            # Always unload adapter after inference
            try:
                self.tts.unload_lora_adapter()
                print(f"✅ LoRA adapter unloaded")
            except Exception as e:
                print(f"⚠️ Failed to unload LoRA adapter: {e}")

        elapsed = time.time() - start
        duration = self._get_audio_duration(output_path)
        print(f"🎵 Total: {len(chunks)} chunks, {duration:.1f}s audio, {elapsed:.1f}s processing")
        return output_path, duration, elapsed

    def ensure_model_for_trained_voice(self, base_model_repo: str | None) -> str | None:
        """Ensure the correct GPU model is loaded for a trained voice.
        Returns error message if cannot switch, None if OK.
        
        Simple logic:
        1. Wait for any model loading to complete
        2. If already on a compatible GPU model → done
        3. Otherwise → unload current model → load correct GPU model
        """
        target = base_model_repo or "pnnbao-ump/VieNeu-TTS"
        print(f"🔍 ensure_model: target={target}, current={self._current_model!r}, initialized={self._initialized}")

        # Step 1: Wait for any loading (startup, manual switch, etc.)
        waited = 0
        while self._is_loading and waited < 90:
            time.sleep(0.5)
            waited += 0.5
        if self._is_loading:
            return "Model đang được nạp quá lâu, vui lòng thử lại sau."

        # Step 2: Check if we're already on a compatible GPU model
        if self._initialized and self._current_model:
            if "gguf" not in self._current_model.lower():
                print(f"✅ Already on GPU model: {self._current_model}")
                return None  # Already on a GPU (PyTorch) model — LoRA compatible

        # Step 3: Need to load the GPU model
        print(f"🔄 Auto-switching to {target} for trained voice...")

        # Unload current model to free resources
        if self._tts is not None:
            print("   🗑️ Unloading current model...")
            try:
                del self._tts
            except Exception:
                pass
            self._tts = None
            self._initialized = False
            self._current_model = ""
            import gc; gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            time.sleep(1)  # Allow GPU memory to be freed

        # Check VRAM (after unloading)
        model_info = next((m for m in AVAILABLE_MODELS if m["repo"] == target), None)
        if model_info and model_info.get("device") == "gpu":
            min_vram = model_info.get("vram_required_mb", 2000)
            gpu_ok, gpus = is_gpu_available(min_vram)
            if not gpu_ok:
                gpu_msg = ", ".join(f"GPU{g['id']}: {g['free_mb']}MB free" for g in gpus)
                return f"GPU không đủ VRAM ({min_vram}MB). [{gpu_msg}]. Vui lòng đợi GPU rảnh."

        # Load the GPU model
        try:
            self._load_model_sync(target)
            print(f"✅ Model switched to {target}")
            return None
        except Exception as e:
            return f"Không thể load model: {e}"

    def _get_audio_duration(self, path: str) -> float | None:
        try:
            with wave.open(path, "rb") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            return None


# Singleton
tts_service = TTSService()
