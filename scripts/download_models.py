"""
VieNeu TTS — Download all models from HuggingFace.
Run inside Docker: docker compose run --rm app python3 scripts/download_models.py
Or standalone:     python3 scripts/download_models.py
"""
import os
import sys

MODELS = [
    # GGUF models (CPU) — small, fast to download
    "pnnbao-ump/VieNeu-TTS-0.3B-q4-gguf",
    "pnnbao-ump/VieNeu-TTS-0.3B-q8-gguf",
    "pnnbao-ump/VieNeu-TTS-q4-gguf",
    "pnnbao-ump/VieNeu-TTS-q8-gguf",
    # PyTorch models (GPU) — larger
    "pnnbao-ump/VieNeu-TTS-0.3B",
    "pnnbao-ump/VieNeu-TTS",
    # Codec (required)
    "neuphonic/distill-neucodec",
]


def main():
    # Set HF cache directory
    hf_home = os.environ.get("HF_HOME", os.path.join(os.path.dirname(__file__), "..", "models"))
    os.environ["HF_HOME"] = hf_home
    print(f"📁 Models directory: {hf_home}")
    print(f"📦 Downloading {len(MODELS)} models from HuggingFace...\n")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("❌ huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    for i, repo_id in enumerate(MODELS, 1):
        print(f"[{i}/{len(MODELS)}] 🔄 {repo_id}...")
        try:
            path = snapshot_download(repo_id, cache_dir=hf_home)
            print(f"         ✅ Downloaded to {path}")
        except Exception as e:
            print(f"         ❌ Failed: {e}")
            continue

    print(f"\n🎉 Done! Models saved to {hf_home}")
    print("   Start the app: docker compose up -d")


if __name__ == "__main__":
    main()
