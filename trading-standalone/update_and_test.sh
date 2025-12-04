#!/bin/bash
# 服务器更新和测试脚本

echo "=========================================="
echo "Trading Service - 更新和测试"
echo "=========================================="
echo ""

# Step 1: 拉取最新代码
echo "📥 Step 1: 拉取最新代码..."
git pull origin exp
if [ $? -ne 0 ]; then
    echo "❌ Git pull failed"
    exit 1
fi
echo "✅ 代码更新完成"
echo ""

# Step 2: 重启服务
echo "🔄 Step 2: 重启Docker服务..."
docker-compose down
echo "等待5秒..."
sleep 5
docker-compose up -d --build
echo "等待服务启动（30秒）..."
sleep 30
echo "✅ 服务重启完成"
echo ""

# Step 3: 检查服务状态
echo "🔍 Step 3: 检查服务状态..."
docker ps | grep trading
echo ""

# Step 4: 检查健康状态
echo "🏥 Step 4: 检查服务健康..."
curl -s http://localhost:8000/health | jq '.' || echo "健康检查失败"
echo ""

# Step 5: 检查账户状态
echo "💰 Step 5: 检查账户状态..."
curl -s http://localhost:8000/api/trading/account | jq '.' || echo "账户查询失败"
echo ""

# Step 6: 触发新的分析
echo "🚀 Step 6: 触发新的交易分析..."
curl -X POST http://localhost:8000/api/trading/analyze
echo ""
echo ""

# Step 7: 查看最近的日志
echo "📋 Step 7: 查看最近的日志..."
echo "等待分析完成（10秒）..."
sleep 10
docker logs --tail 100 trading_service | grep -E "(SignalExtraction|Leader|TradeExecutor|SIGNAL_DEBUG)"
echo ""

echo "=========================================="
echo "✅ 更新和测试完成"
echo "=========================================="
echo ""
echo "📊 下一步操作："
echo "1. 查看完整日志: docker logs -f trading_service"
echo "2. 查看信号历史: curl http://localhost:8000/api/trading/history"
echo "3. 查看前端: http://localhost:8888"
echo ""
