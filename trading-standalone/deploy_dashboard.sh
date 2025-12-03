#!/bin/bash
# Deploy Dashboard to Remote Server
# 将Dashboard部署到远程服务器

set -e

SERVER="root@45.76.159.149"
REMOTE_DIR="/root/trading-standalone"

echo "=== Deploying Dashboard to Remote Server ==="
echo ""

# 1. Copy updated files
echo "1. Copying updated files..."
scp docker-compose.yml status.html "${SERVER}:${REMOTE_DIR}/"

# 2. Start web dashboard on remote
echo ""
echo "2. Starting web dashboard..."
ssh "$SERVER" "cd $REMOTE_DIR && docker compose up -d web_dashboard"

echo ""
echo "=== Dashboard Deployed Successfully ==="
echo ""
echo "You can now access the dashboard at:"
echo "  http://45.76.159.149:8888/"
echo ""
