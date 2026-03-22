"""
Training Runner — orchestrates the VieNeu LoRA finetune pipeline.

Pipeline: recordings → metadata.csv → filter → encode NeuCodec → LoRA train → trained_voice

Calls the scripts from VieNeu-TTS/finetune/ via subprocess for isolation.
"""
import os
import sys
import csv
import json
import asyncio
import subprocess
import shutil
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.models.training import TrainingRequest, TrainedVoice
from app.models.recording import Recording
from app.models.sentence import Sentence

VIENEU_TTS_ROOT = settings.VIENEU_TTS_PATH  # e.g. /home/quanghoa/vietneu/VieNeu-TTS

# Available base models for finetuning
BASE_MODELS = [
    {
        "name": "VieNeu-TTS-0.3B",
        "repo_id": "pnnbao-ump/VieNeu-TTS-0.3B",
        "description": "Lightweight model, faster training (~30 min)",
    },
    {
        "name": "VieNeu-TTS-0.5B",
        "repo_id": "pnnbao-ump/VieNeu-TTS",
        "description": "Full model, better quality (~60 min)",
    },
]

# Default training params
DEFAULT_MAX_STEPS = 5000
DEFAULT_SAVE_STEPS = 500
DEFAULT_BATCH_SIZE = 2
DEFAULT_LR = 2e-4


async def _update_request(db: AsyncSession, request_id: int, **kwargs):
    """Helper to update training request fields."""
    result = await db.execute(
        select(TrainingRequest).where(TrainingRequest.id == request_id)
    )
    req = result.scalar_one()
    for k, v in kwargs.items():
        setattr(req, k, v)
    await db.commit()


def _run_script(cmd, cwd=None, env=None):
    """Run a subprocess, return (success, stdout, stderr)."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, env=merged_env, timeout=7200
    )
    if result.returncode != 0:
        print(f"❌ Script failed: {' '.join(cmd)}")
        print(f"   stderr: {result.stderr[-500:]}")
    return result.returncode == 0, result.stdout, result.stderr


async def run_training_pipeline(request_id: int, max_steps: int = None, gpu_id: int = None):
    """
    Full training pipeline — runs as a background task.

    Steps:
    1. Generate metadata.csv from recordings (10%)
    2. Filter data quality (20%)
    3. Encode NeuCodec (50%)
    4. Run LoRA training (90%)
    5. Save trained voice (100%)
    """
    if max_steps is None:
        max_steps = DEFAULT_MAX_STEPS
    if gpu_id is None:
        gpu_id = settings.TRAINING_GPU_ID

    async with async_session() as db:
        result = await db.execute(
            select(TrainingRequest).where(TrainingRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if not req:
            return

        user_id = req.user_id
        set_id = req.sentence_set_id
        voice_name = req.voice_name
        base_model = req.base_model_path or settings.TRAINING_BASE_MODEL

        # Mark as training
        req.status = "training"
        req.started_at = datetime.now(timezone.utc)
        req.progress = 0
        await db.commit()

    # Working directory for this training run
    output_dir = os.path.join(
        settings.STORAGE_PATH, "training", str(user_id), str(request_id)
    )
    dataset_dir = os.path.join(output_dir, "dataset")
    raw_audio_dir = os.path.join(dataset_dir, "raw_audio")
    os.makedirs(raw_audio_dir, exist_ok=True)

    env = {"CUDA_VISIBLE_DEVICES": str(gpu_id)}

    try:
        # ── Step 1: Generate metadata.csv (0→10%) ──
        print(f"🔄 [{request_id}] Step 1: Generating metadata.csv...")
        async with async_session() as db:
            sent_result = await db.execute(
                select(Sentence.id).where(Sentence.set_id == set_id)
            )
            sentence_ids = [row[0] for row in sent_result.all()]

            rec_result = await db.execute(
                select(Recording).where(
                    Recording.user_id == user_id,
                    Recording.sentence_id.in_(sentence_ids),
                )
            )
            recordings = rec_result.scalars().all()

            metadata_lines = []
            for rec in recordings:
                s_result = await db.execute(
                    select(Sentence).where(Sentence.id == rec.sentence_id)
                )
                sent = s_result.scalar_one_or_none()
                if not sent or not rec.file_path or not os.path.exists(rec.file_path):
                    continue
                # Copy audio to dataset/raw_audio/
                dest_name = os.path.basename(rec.file_path)
                shutil.copy2(rec.file_path, os.path.join(raw_audio_dir, dest_name))
                metadata_lines.append(f"{dest_name}|{sent.text}\n")

        # Write metadata.csv
        metadata_path = os.path.join(dataset_dir, "metadata.csv")
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.writelines(metadata_lines)
        print(f"   ✅ {len(metadata_lines)} samples → {metadata_path}")

        async with async_session() as db:
            await _update_request(db, request_id, progress=10)

        # ── Step 2: Filter data (10→20%) ──
        print(f"🔄 [{request_id}] Step 2: Filtering data...")
        filter_script = os.path.join(VIENEU_TTS_ROOT, "finetune", "data_scripts", "filter_data.py")
        ok, stdout, stderr = await asyncio.to_thread(
            _run_script,
            [sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{VIENEU_TTS_ROOT}')
from finetune.data_scripts.filter_data import filter_and_process_dataset
filter_and_process_dataset(dataset_dir='{dataset_dir}')
"""],
            cwd=VIENEU_TTS_ROOT, env=env,
        )
        print(f"   {'✅' if ok else '⚠️'} Filter done. {stdout[-200:] if stdout else ''}")

        # If filter removed all samples, use original metadata
        cleaned_path = os.path.join(dataset_dir, "metadata_cleaned.csv")
        if not os.path.exists(cleaned_path) or os.path.getsize(cleaned_path) == 0:
            print("   ⚠️ Filter removed all samples, using original metadata")
            shutil.copy2(metadata_path, cleaned_path)

        async with async_session() as db:
            await _update_request(db, request_id, progress=20)

        # ── Step 3: Encode NeuCodec (20→50%) ──
        print(f"🔄 [{request_id}] Step 3: Encoding with NeuCodec...")
        ok, stdout, stderr = await asyncio.to_thread(
            _run_script,
            [sys.executable, "-c", f"""
import sys, os
os.environ['HF_HOME'] = '{os.path.join(os.path.dirname(VIENEU_TTS_ROOT), "models")}'
sys.path.insert(0, '{VIENEU_TTS_ROOT}')
from finetune.data_scripts.encode_data import encode_dataset
encode_dataset(dataset_dir='{dataset_dir}', max_samples=9999)
"""],
            cwd=VIENEU_TTS_ROOT, env=env,
        )
        if not ok:
            raise RuntimeError(f"NeuCodec encoding failed: {stderr[-300:]}")
        print(f"   ✅ Encode done. {stdout[-200:] if stdout else ''}")

        async with async_session() as db:
            await _update_request(db, request_id, progress=50)

        # ── Step 4: Run LoRA training (50→90%) ──
        print(f"🔄 [{request_id}] Step 4: LoRA training ({max_steps} steps)...")
        checkpoint_dir = os.path.join(output_dir, "checkpoint")
        os.makedirs(checkpoint_dir, exist_ok=True)

        train_script = f"""
import sys, os, gc
os.environ['HF_HOME'] = '{os.path.join(os.path.dirname(VIENEU_TTS_ROOT), "models")}'
sys.path.insert(0, '{VIENEU_TTS_ROOT}')
sys.path.insert(0, os.path.join('{VIENEU_TTS_ROOT}', 'src'))

import torch

# Force clear GPU memory from any previous step
torch.cuda.empty_cache()
gc.collect()
print(f"GPU memory free: {{torch.cuda.mem_get_info()[0]/1024**3:.1f}} GiB")

from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, default_data_collator, TrainingArguments
from peft import get_peft_model, LoraConfig, TaskType

# LoRA config
lora_config = LoraConfig(
    r=16, lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05, bias="none", task_type=TaskType.CAUSAL_LM,
)

# Load model — use device 0 because CUDA_VISIBLE_DEVICES already limits to one GPU
model_name = "{base_model}"
print(f"Loading model: {{model_name}}")
tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map={{"": 0}})
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
model.enable_input_require_grads()

# Dataset
from finetune.train import VieNeuDataset
dataset_path = '{os.path.join(dataset_dir, "metadata_encoded.csv")}'
dataset = VieNeuDataset(dataset_path, tokenizer)
print(f"Dataset: {{len(dataset)}} samples")

# Training — batch_size=1 for memory safety, gradient_checkpointing to save VRAM
args = TrainingArguments(
    output_dir='{checkpoint_dir}',
    do_train=True, do_eval=False,
    max_steps={max_steps},
    per_device_train_batch_size=1,
    gradient_accumulation_steps=2,
    learning_rate={DEFAULT_LR},
    warmup_ratio=0.05, bf16=True,
    logging_steps=50,
    save_steps={max_steps // 5 if max_steps >= 100 else max_steps},
    eval_strategy="no", save_strategy="steps",
    save_total_limit=3, report_to="none",
    dataloader_num_workers=0,
    gradient_checkpointing=True,
)

trainer = Trainer(model=model, args=args, train_dataset=dataset, data_collator=default_data_collator)
print("Starting training...")
trainer.train()

# Save final
save_path = os.path.join('{checkpoint_dir}', 'final')
model.save_pretrained(save_path)
tokenizer.save_pretrained(save_path)
print(f"Training complete. Saved to: {{save_path}}")
"""

        ok, stdout, stderr = await asyncio.to_thread(
            _run_script,
            [sys.executable, "-c", train_script],
            cwd=VIENEU_TTS_ROOT, env=env,
        )
        if not ok:
            raise RuntimeError(f"LoRA training failed: {stderr[-500:]}")
        print(f"   ✅ Training done!")

        async with async_session() as db:
            await _update_request(db, request_id, progress=90)

        # ── Step 4.5: Create voices.json for the checkpoint ──
        # This is CRITICAL for quality: load_lora_adapter() loads voices.json
        # to provide pre-encoded NeuCodec reference → consistent with training
        print(f"🔄 [{request_id}] Step 4.5: Creating voices.json from ref audio...")
        final_checkpoint = os.path.join(checkpoint_dir, "final")
        if not os.path.isdir(final_checkpoint):
            final_checkpoint = checkpoint_dir

        # Pick best ref audio from training recordings (3-15s, longest)
        best_ref_path = None
        best_ref_text = None
        best_ref_duration = 0
        async with async_session() as db:
            sent_result = await db.execute(
                select(Sentence.id).where(Sentence.set_id == set_id)
            )
            sentence_ids = [row[0] for row in sent_result.all()]
            if sentence_ids:
                rec_result = await db.execute(
                    select(Recording).where(
                        Recording.user_id == user_id,
                        Recording.sentence_id.in_(sentence_ids),
                    ).order_by(Recording.duration.desc())
                )
                for rec in rec_result.scalars().all():
                    dur = rec.duration or 0
                    if 3.0 <= dur <= 15.0 and os.path.exists(rec.file_path):
                        s_result = await db.execute(
                            select(Sentence).where(Sentence.id == rec.sentence_id)
                        )
                        sent = s_result.scalar_one_or_none()
                        best_ref_path = rec.file_path
                        best_ref_text = sent.text if sent else ""
                        best_ref_duration = dur
                        break
                if not best_ref_path:
                    rec_result2 = await db.execute(
                        select(Recording).where(
                            Recording.user_id == user_id,
                            Recording.sentence_id.in_(sentence_ids),
                        ).order_by(Recording.duration.desc())
                    )
                    rec = rec_result2.scalars().first()
                    if rec and rec.file_path and os.path.exists(rec.file_path):
                        s_result = await db.execute(
                            select(Sentence).where(Sentence.id == rec.sentence_id)
                        )
                        sent = s_result.scalar_one_or_none()
                        best_ref_path = rec.file_path
                        best_ref_text = sent.text if sent else ""

        # Encode ref audio → voices.json
        if best_ref_path:
            voices_json_script = f"""
import os, json, sys
os.environ['HF_HOME'] = '{os.path.join(os.path.dirname(VIENEU_TTS_ROOT), "models")}'
sys.path.insert(0, '{VIENEU_TTS_ROOT}')
sys.path.insert(0, os.path.join('{VIENEU_TTS_ROOT}', 'src'))

from vieneu.standard import VieNeuTTS
tts = VieNeuTTS(
    backbone_repo='{base_model}',
    backbone_device='cuda:0',
    codec_repo='neuphonic/distill-neucodec',
    codec_device='cuda:0'
)
ref_codes = tts.encode_reference('{best_ref_path}')
codes_list = ref_codes.cpu().numpy().flatten().tolist()

voices_data = {{
    "meta": {{"spec": "vieneu.voice.presets", "spec_version": "1.0", "engine": "VieNeu-TTS"}},
    "default_voice": "trained_voice",
    "presets": {{
        "trained_voice": {{
            "codes": codes_list,
            "text": '''{best_ref_text}''',
            "description": "LoRA trained voice"
        }}
    }}
}}

voices_path = os.path.join('{final_checkpoint}', 'voices.json')
with open(voices_path, 'w', encoding='utf-8') as f:
    json.dump(voices_data, f, ensure_ascii=False)
print(f"Created voices.json: {{len(codes_list)}} codes")
"""
            ok, stdout, stderr = await asyncio.to_thread(
                _run_script,
                [sys.executable, "-c", voices_json_script],
                cwd=VIENEU_TTS_ROOT, env=env,
            )
            if ok:
                print(f"   ✅ voices.json created! {stdout.strip()}")
            else:
                print(f"   ⚠️ voices.json creation failed (non-critical): {stderr[-200:]}")
        else:
            print(f"   ⚠️ No ref audio found, skipping voices.json creation")

        # ── Step 5: Create trained_voice record (95→100%) ──
        # best_ref_path and best_ref_text already set in Step 4.5

        async with async_session() as db:
            trained_voice = TrainedVoice(
                user_id=user_id,
                training_request_id=request_id,
                name=voice_name,
                checkpoint_path=final_checkpoint,
                base_model_repo=base_model,
                ref_audio_path=best_ref_path,
                ref_text=best_ref_text,
                language="vi",
                is_active=True,
            )
            db.add(trained_voice)

            result = await db.execute(
                select(TrainingRequest).where(TrainingRequest.id == request_id)
            )
            req = result.scalar_one()
            req.status = "completed"
            req.progress = 100
            req.completed_at = datetime.now(timezone.utc)
            await db.commit()

        print(f"✅ Training complete: {voice_name} (request #{request_id}, {max_steps} steps)")

    except Exception as e:
        async with async_session() as db:
            result = await db.execute(
                select(TrainingRequest).where(TrainingRequest.id == request_id)
            )
            req = result.scalar_one_or_none()
            if req:
                req.status = "failed"
                await db.commit()

        print(f"❌ Training failed (request #{request_id}): {e}")
        import traceback
        traceback.print_exc()


def get_base_models():
    """Return available base models for finetuning."""
    return BASE_MODELS
