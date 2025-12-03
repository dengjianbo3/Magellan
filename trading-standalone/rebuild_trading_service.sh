#!/bin/bash

echo "=== 重新构建 trading-service 以更新 status.html ==="
echo ""

# Step 1: 停止服务
echo "Step 1: 停止 trading-service..."
docker compose stop trading-service

# Step 2: 删除旧容器
echo ""
echo "Step 2: 删除旧容器..."
docker compose rm -f trading-service

# Step 3: 重新构建镜像（使用 --no-cache 确保完全重建）
echo ""
echo "Step 3: 重新构建镜像..."
docker compose build --no-cache trading-service

# Step 4: 启动新容器
echo ""
echo "Step 4: 启动新容器..."
docker compose up -d trading-service

# Step 5: 等待启动
echo ""
echo "等待 5 秒让服务启动..."
sleep 5

# Step 6: 检查状态
echo ""
echo "Step 6: 检查服务状态..."
docker compose ps | grep trading-service

# Step 7: 检查日志
echo ""
echo "Step 7: 检查最近日志..."
docker compose logs --tail 10 trading-service

# Step 8: 测试 status.html
echo ""
echo "Step 8: 测试 status.html 内容..."
echo "检查是否包含 'Recent Signals':"
curl -s http://localhost:8000/api/trading/dashboard | grep -o "Recent Signals" || echo "❌ 没找到 'Recent Signals'"
curl -s http://localhost:8000/api/trading/dashboard | grep -o "Recent Trades" && echo "❌ 还是旧版本 'Recent Trades'" || echo "✅ 已经移除 'Recent Trades'"

echo ""
echo "=== 完成 ==="
echo "现在打开浏览器测试: http://45.76.159.149:8000/api/trading/dashboard"
echo "记得按 Ctrl+Shift+R 硬刷新"
