#!/bin/bash
# ============================================================
# VieNeu TTS — Container Entrypoint
# 1. Wait for PostgreSQL
# 2. Run database migrations
# 3. Start uvicorn
# ============================================================

set -e

echo "🚀 VieNeu TTS Starting..."

# --- Wait for PostgreSQL ---
echo "⏳ Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY=0
until python3 -c "
import asyncio, asyncpg, os
async def check():
    url = os.environ.get('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "❌ PostgreSQL not available after ${MAX_RETRIES} retries"
        exit 1
    fi
    echo "   Retry $RETRY/$MAX_RETRIES..."
    sleep 2
done
echo "✅ PostgreSQL ready"

# --- Run Alembic migrations ---
echo "📦 Running database migrations..."
cd /app

# Update alembic.ini with the correct DB URL
SYNC_URL=$(echo "$DATABASE_URL" | sed 's/asyncpg/psycopg2/g')
sed -i "s|sqlalchemy.url = .*|sqlalchemy.url = ${DATABASE_URL}|g" alembic.ini

python3 -m alembic upgrade head 2>&1 || {
    echo "⚠️ Alembic migration failed (may already be up to date)"
}
echo "✅ Database ready"

# --- Check models ---
MODEL_COUNT=$(find /app/models -name "*.gguf" -o -name "*.safetensors" 2>/dev/null | wc -l)
if [ "$MODEL_COUNT" -eq 0 ]; then
    echo ""
    echo "⚠️ ═══════════════════════════════════════════════════"
    echo "⚠️  No models found in /app/models"
    echo "⚠️  Run: docker compose run --rm app python3 scripts/download_models.py"
    echo "⚠️ ═══════════════════════════════════════════════════"
    echo ""
fi

# --- Start uvicorn ---
PORT=${PORT:-8889}
echo "🌐 Starting VieNeu TTS on port ${PORT}..."
exec python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --timeout-keep-alive 300 \
    --workers 1
