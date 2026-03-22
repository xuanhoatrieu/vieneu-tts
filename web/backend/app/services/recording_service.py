"""
Recording Service — save, validate, resample, convert audio files.
Uses wave/ffmpeg instead of torchaudio for maximum compatibility.
"""
import os
import subprocess
import tempfile
import uuid
import wave as wave_mod

from app.core.config import settings


class RecordingService:
    """Handles audio recording processing: format conversion, resampling, validation."""

    def save_recording(
        self,
        file_content: bytes,
        original_filename: str,
        user_id: uuid.UUID,
        set_id: int,
        sentence_id: int,
    ) -> tuple[str, float]:
        """
        Process and save a recording.
        1. Detect format (WebM/OGG/WAV/MP3)
        2. Convert to 24kHz mono WAV via ffmpeg
        3. Validate duration 1-30s
        4. Save to data/recordings/{user_id}/{set_id}/sentence_{id}.wav

        Returns: (file_path, duration_sec)
        Raises: ValueError on invalid audio
        """
        rec_dir = os.path.join(
            settings.STORAGE_PATH, "recordings", str(user_id), str(set_id)
        )
        os.makedirs(rec_dir, exist_ok=True)
        output_path = os.path.join(rec_dir, f"sentence_{sentence_id}.wav")

        # Save raw upload to temp
        ext = os.path.splitext(original_filename)[1].lower() or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            # Always convert to 24kHz mono WAV via ffmpeg (handles any format)
            self._convert_to_wav(tmp_path, output_path, target_sr=24000)

            # Get duration and validate
            duration = self._get_duration(output_path)
            if duration < 1.0:
                os.unlink(output_path)
                raise ValueError(f"Audio too short: {duration:.1f}s (min 1s)")
            if duration > 30.0:
                os.unlink(output_path)
                raise ValueError(f"Audio too long: {duration:.1f}s (max 30s)")

            return output_path, round(duration, 2)

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _convert_to_wav(self, input_path: str, output_path: str, target_sr: int = 24000):
        """Convert any audio to 24kHz mono 16-bit WAV using ffmpeg."""
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-acodec", "pcm_s16le",
                "-ar", str(target_sr),
                "-ac", "1",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ValueError(f"Audio conversion failed: {result.stderr[:200]}")

    def _get_duration(self, path: str) -> float:
        """Get WAV audio duration in seconds using standard library."""
        with wave_mod.open(path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / rate

    def generate_metadata_csv(
        self, recordings: list[dict], output_dir: str
    ) -> str:
        """
        Generate metadata.csv for VieNeu training pipeline.
        Format: filename|text
        """
        csv_path = os.path.join(output_dir, "metadata.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            for rec in recordings:
                filename = os.path.basename(rec["file_path"])
                text = rec["text"]
                f.write(f"{filename}|{text}\n")
        return csv_path


# Singleton
recording_service = RecordingService()
