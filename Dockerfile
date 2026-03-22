# ============================================================
# VieNeu TTS — Multi-stage Dockerfile
# Stage 1: Build React frontend
# Stage 2: CUDA runtime + Python backend
# ============================================================

# --- Stage 1: Frontend Build ---
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci --silent
COPY web/frontend/ .
RUN npm run build

# --- Stage 2: Runtime ---
FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.13 python3.13-venv python3-pip python3.13-dev \
    ffmpeg libpq-dev gcc g++ git curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.13 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.13 /usr/bin/python

WORKDIR /app

# Python deps — install torch with CUDA first (cached layer)
COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages \
    torch==2.10.0 torchaudio==2.10.0 --index-url https://download.pytorch.org/whl/cu126
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy backend code
COPY web/backend/app ./app
COPY web/backend/alembic ./alembic
COPY web/backend/alembic.ini .

# Copy built frontend
COPY --from=frontend-build /build/dist ./static

# Copy scripts
COPY scripts/ ./scripts/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh scripts/*.sh 2>/dev/null; true

# Dirs for volumes
RUN mkdir -p /app/data /app/models

# Default env vars (overridden by docker-compose)
ENV STORAGE_PATH=/app/data
ENV HF_HOME=/app/models
ENV PORT=8889

EXPOSE 8889

ENTRYPOINT ["./entrypoint.sh"]
