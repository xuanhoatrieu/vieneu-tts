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

        # Determine device: GPU models → cuda:0, GGUF models → cpu
        model_info = next((m for m in AVAILABLE_MODELS if m["repo"] == backbone_repo), None)
        is_gpu_model = model_info and model_info.get("device") == "gpu"
        device = "cuda:0" if is_gpu_model else "cpu"
        print(f"🔄 Loading model: {backbone_repo} (mode={mode}, device={device})...")

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
                backbone_device=device,
                codec_repo=settings.VIENEU_CODEC_REPO,
                codec_device=device,
            )

        elapsed = _t.time() - t0
        self._current_model = backbone_repo
        self._initialized = True
        print(f"🧠 VieNeu TTS loaded: {backbone_repo} on {device} in {elapsed:.1f}s (mode={mode})")

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
        """Get available preset voices.
        These are the same 6 voices for all VieNeu models,
        so we return them statically rather than querying the model.
        """
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

    def synthesize_with_trained_voice(
        self, text: str, checkpoint_path: str,
        ref_audio_path: str | None = None, ref_text: str | None = None,
        voice_id: str = "",
    ) -> tuple[str, float | None, float]:
        """Synthesize using a LoRA-finetuned trained voice.
        Uses SDK's built-in max_chars=256 text splitting — no manual chunking needed.
        Note: ensure_model_for_trained_voice must be called BEFORE this method.
        """
        # Wait for any model loading to finish
        for _ in range(120):
            if not self._is_loading:
                break
            time.sleep(0.5)
        if self._is_loading:
            raise RuntimeError("Model đang được nạp quá lâu, vui lòng thử lại sau.")

        self._ensure_initialized()

        # Need GPU model for LoRA — GGUF models don't support adapters
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
            if hasattr(self.tts, 'backbone') and hasattr(self.tts.backbone, 'peft_config'):
                try:
                    self.tts.backbone = self.tts.backbone.merge_and_unload() if hasattr(self.tts.backbone, 'merge_and_unload') else self.tts.backbone
                    self.tts._lora_loaded = False
                    print("   🧹 Cleaned up leftover peft_config")
                except Exception:
                    pass

            # Load LoRA adapter
            print(f"🔄 Loading LoRA adapter: {checkpoint_path}")
            self.tts.load_lora_adapter(checkpoint_path)

            # Build inference kwargs
            kwargs = {"text": text}
            if ref_audio_path and os.path.exists(ref_audio_path):
                kwargs["ref_audio"] = ref_audio_path
                kwargs["ref_text"] = ref_text or ""
                print(f"   📎 Using ref audio: {os.path.basename(ref_audio_path)}")
            elif voice_id:
                try:
                    kwargs["voice"] = self.tts.get_preset_voice(voice_id)
                except Exception:
                    pass

            # SDK handles text splitting internally (max_chars=256)
            # No need for manual chunking!
            print(f"   📝 Text length: {len(text)} chars")
            audio = self.tts.infer(**kwargs)
            self.tts.save(audio, output_path)

        finally:
            # Always unload adapter after inference
            try:
                self.tts.unload_lora_adapter()
                print(f"✅ LoRA adapter unloaded")
            except Exception as e:
                print(f"⚠️ Failed to unload LoRA adapter: {e}")

        elapsed = time.time() - start
        duration = self._get_audio_duration(output_path)
        print(f"🎵 Total: {duration:.1f}s audio, {elapsed:.1f}s processing")
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
