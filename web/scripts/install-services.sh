#!/bin/bash
# VieNeu TTS API — Install as systemd service
# Usage: sudo bash install-services.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")/backend"
USER=$(whoami)

echo "🦜 VieNeu TTS API — Service Installer"
echo "======================================="
echo "Backend: $BACKEND_DIR"
echo "User: $USER"

# 1. Create systemd service
cat > /etc/systemd/system/vietneu-api.service << EOF
[Unit]
Description=VieNeu TTS API Server
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8888
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Created /etc/systemd/system/vietneu-api.service"

# 2. Reload and enable
systemctl daemon-reload
systemctl enable vietneu-api
systemctl start vietneu-api

echo "✅ Service started and enabled"
echo ""
echo "Commands:"
echo "  systemctl status vietneu-api"
echo "  systemctl restart vietneu-api"
echo "  journalctl -u vietneu-api -f"
echo ""
echo "🎉 Done! API at http://localhost:8888"
