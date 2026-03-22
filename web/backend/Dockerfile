FROM python:3.13-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY . .

# Storage dir
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV STORAGE_PATH=/app/data

EXPOSE 8888

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]
