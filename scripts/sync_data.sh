#!/bin/bash
# ============================================================
# VieNeu TTS — Sync data from source machine to target machine
# ============================================================
#
# Usage (run from TARGET machine — 192.168.0.19):
#   bash scripts/sync_data.sh
#
# What it syncs:
#   - data/recordings/    → User voice recordings
#   - data/refs/          → Reference audio files
#   - data/training/      → Training checkpoints + datasets
#   - data/outputs/       → Generated audio files
#   - Database            → pg_dump + pg_restore
# ============================================================

set -e

# --- Configuration ---
SOURCE_HOST="192.168.0.11"
SOURCE_USER="quanghoa"
SOURCE_PATH="/home/quanghoa/vietneu/data/"

TARGET_PATH="./data/"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 VieNeu TTS — Data Sync"
echo "   Source: ${SOURCE_USER}@${SOURCE_HOST}:${SOURCE_PATH}"
echo "   Target: ${TARGET_PATH}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --- Step 1: Sync data files ---
echo "📂 Step 1/3: Syncing data files..."
mkdir -p "${TARGET_PATH}"

rsync -avz --progress \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    "${SOURCE_USER}@${SOURCE_HOST}:${SOURCE_PATH}" \
    "${TARGET_PATH}"

echo "✅ Data files synced"
echo ""

# --- Step 2: Sync database ---
echo "🗄️ Step 2/3: Exporting database from source..."

# Dump from source
ssh "${SOURCE_USER}@${SOURCE_HOST}" \
    "pg_dump -U vietneu -d vietneu_tts --clean --if-exists" \
    > /tmp/vietneu_tts_dump.sql

echo "   Dump size: $(du -h /tmp/vietneu_tts_dump.sql | cut -f1)"

echo "📥 Step 3/3: Importing database to local PostgreSQL..."

# Get DB container name
DB_CONTAINER=$(docker compose ps -q db 2>/dev/null || echo "")

if [ -n "$DB_CONTAINER" ]; then
    # Import via Docker
    docker exec -i "$DB_CONTAINER" \
        psql -U vietneu -d vietneu_tts < /tmp/vietneu_tts_dump.sql 2>&1 | tail -3
    echo "✅ Database imported via Docker"
else
    # Import directly (if PostgreSQL is local)
    psql -U vietneu -d vietneu_tts < /tmp/vietneu_tts_dump.sql 2>&1 | tail -3
    echo "✅ Database imported locally"
fi

rm -f /tmp/vietneu_tts_dump.sql

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Sync complete!"
echo ""
echo "📊 Data synced:"
du -sh "${TARGET_PATH}recordings/" "${TARGET_PATH}refs/" "${TARGET_PATH}training/" "${TARGET_PATH}outputs/" 2>/dev/null || true
echo ""
echo "🚀 Start the app: docker compose up -d"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
