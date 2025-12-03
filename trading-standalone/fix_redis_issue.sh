#!/bin/bash

echo "=== Redis启动失败诊断和修复脚本 ==="
echo ""

# 1. 检查Redis容器状态
echo "1. 检查Redis容器状态..."
docker ps -a | grep redis

echo ""
echo "2. 查看Redis容器日志..."
docker logs trading-redis 2>&1 | tail -30

echo ""
echo "3. 检查Redis数据目录权限..."
ls -la data/redis/ 2>/dev/null || echo "Redis数据目录不存在"

echo ""
echo "4. 尝试修复方案..."

# 方案1: 停止并删除现有的Redis容器
echo "停止并删除现有Redis容器..."
docker stop trading-redis 2>/dev/null
docker rm trading-redis 2>/dev/null

# 方案2: 清理Redis数据目录（如果存在权限问题）
echo "检查并修复Redis数据目录..."
if [ -d "data/redis" ]; then
    sudo chown -R 999:999 data/redis 2>/dev/null || chown -R 999:999 data/redis
fi

# 方案3: 重新创建数据目录
mkdir -p data/redis
chmod 755 data/redis

echo ""
echo "5. 重新启动服务..."
docker compose up -d redis

echo ""
echo "6. 等待Redis启动..."
sleep 5

echo ""
echo "7. 检查Redis健康状态..."
docker ps | grep redis
docker logs trading-redis --tail 20

echo ""
echo "=== 诊断完成 ==="
