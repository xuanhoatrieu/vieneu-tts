# VieNeu TTS — Deploy Guide

Hướng dẫn triển khai VieNeu TTS trên máy mới bằng Docker.

## Yêu cầu máy đích

- **OS**: Ubuntu 22.04+
- **GPU**: NVIDIA (≥ 8GB VRAM) + Driver ≥ 550
- **RAM**: ≥ 16GB
- **Disk**: ≥ 30GB free
- **Docker**: Docker Engine + Docker Compose v2
- **NVIDIA Container Toolkit**: Cho GPU passthrough

## Bước 1: Cài đặt Docker + NVIDIA

```bash
# Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out & log in lại

# NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
```

## Bước 2: Clone repo

```bash
cd ~
git clone https://github.com/xuanhoatrieu/vieneu-tts.git vietneu
cd vietneu
```

## Bước 3: Cấu hình

```bash
cp .env.example .env
nano .env
# Đổi: APP_PORT, SECRET_KEY, ADMIN_PASSWORD
```

### Cấu hình mặc định:

| Variable | Default | Mô tả |
|----------|---------|-------|
| APP_PORT | 8889 | Port web app |
| DB_PORT | 5433 | Port PostgreSQL |
| DB_PASSWORD | vietneu | PostgreSQL password |
| SECRET_KEY | ... | JWT secret (PHẢI đổi!) |
| ADMIN_EMAIL | admin@vietneu.io | Admin login |
| ADMIN_PASSWORD | changeme | Admin password (PHẢI đổi!) |
| TRAINING_GPU_ID | 0 | GPU cho training |

## Bước 4: Download models

```bash
# Tạo thư mục models
mkdir -p models

# Build image + download models (~11GB, mất 10-30 phút)
docker compose build
docker compose run --rm app python3 scripts/download_models.py
```

## Bước 5: Sync data từ máy nguồn

```bash
# Sync data (recordings, trained voices, database)
bash scripts/sync_data.sh

# Hoặc rsync thủ công:
rsync -avz quanghoa@192.168.0.11:/home/quanghoa/vietneu/data/ ./data/
```

## Bước 6: Clone VieNeu-TTS finetune scripts (cho training)

```bash
git clone https://github.com/pnnbao97/VieNeu-TTS.git VieNeu-TTS
```

## Bước 7: Start

```bash
docker compose up -d

# Check logs
docker compose logs -f app

# Verify
curl http://localhost:8889/api/v1/tts/voices
```

## Truy cập

- **Web UI**: `http://192.168.0.19:8889`
- **API**: `http://192.168.0.19:8889/api/v1/`

## Commands thường dùng

```bash
# Start / Stop
docker compose up -d
docker compose down

# View logs
docker compose logs -f app
docker compose logs -f db

# Rebuild sau khi pull code mới
git pull
docker compose build
docker compose up -d

# Sync data lại
bash scripts/sync_data.sh

# Download models (nếu chưa có)
docker compose run --rm app python3 scripts/download_models.py

# Vào container debug
docker compose exec app bash
```

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|----------|
| `nvidia-smi` không hoạt động trong Docker | Cài nvidia-container-toolkit + restart Docker |
| Port 8889 bị chiếm | Đổi `APP_PORT` trong `.env` |
| Models không tải được | Kiểm tra mạng, hoặc copy `models/` từ máy nguồn |
| Database error | Kiểm tra `docker compose logs db` |
| GPU memory hết | Dùng GGUF model (CPU), hoặc tắt process khác đang dùng GPU |
