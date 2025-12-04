#!/bin/bash

echo "🔍 检查 trading-service 容器状态..."
docker ps -a | grep trading-service

echo ""
echo "📋 最近的容器日志（最后100行）..."
docker logs trading-service --tail 100

echo ""
echo "🔍 检查容器是否在重启..."
docker inspect trading-service | grep -A 5 "RestartCount"

echo ""
echo "📊 Docker Compose 服务状态..."
if command -v docker compose &> /dev/null; then
    docker compose ps
else
    docker-compose ps
fi
