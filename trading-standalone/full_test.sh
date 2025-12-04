#!/bin/bash
# 完整的更新、重启和验证流程

set -e  # Exit on error

echo "=========================================="
echo "🔧 双重触发问题修复 - 完整测试流程"
echo "=========================================="
echo ""

# Step 1: 拉取最新代码
echo "📥 Step 1: 拉取最新代码..."
git pull origin exp
echo "✅ 代码更新完成"
echo ""

# Step 2: 停止旧服务
echo "🛑 Step 2: 停止旧服务..."
docker-compose down
echo "✅ 旧服务已停止"
echo ""

# Step 3: 重新构建和启动
echo "🔨 Step 3: 重新构建和启动服务..."
docker-compose up -d --build
echo "✅ 服务启动中..."
echo ""

# Step 4: 等待服务就绪
echo "⏳ Step 4: 等待服务就绪（30秒）..."
sleep 30
echo "✅ 服务应该已就绪"
echo ""

# Step 5: 检查服务状态
echo "📊 Step 5: 检查服务状态..."
docker ps | grep trading
echo ""

# Step 6: 分析启动日志
echo "=========================================="
echo "📋 Step 6: 分析启动日志"
echo "=========================================="
echo ""

echo "6.1 检查 Trading System 启动次数:"
TRADING_START_COUNT=$(docker logs trading_service 2>&1 | grep -c "🚀 Starting trading system" || echo "0")
echo "  结果: $TRADING_START_COUNT 次"
if [ "$TRADING_START_COUNT" -eq "1" ]; then
    echo "  ✅ 正常（应该=1）"
else
    echo "  ❌ 异常（应该=1，实际=$TRADING_START_COUNT）"
fi
echo ""

echo "6.2 检查 Scheduler 启动次数:"
SCHEDULER_START_COUNT=$(docker logs trading_service 2>&1 | grep -c "Trading scheduler started" || echo "0")
echo "  结果: $SCHEDULER_START_COUNT 次"
if [ "$SCHEDULER_START_COUNT" -eq "1" ]; then
    echo "  ✅ 正常（应该=1）"
else
    echo "  ❌ 异常（应该=1，实际=$SCHEDULER_START_COUNT）"
fi
echo ""

echo "6.3 检查是否有重复启动警告:"
DUPLICATE_WARNING=$(docker logs trading_service 2>&1 | grep -c "already started" || echo "0")
echo "  结果: $DUPLICATE_WARNING 次警告"
if [ "$DUPLICATE_WARNING" -eq "0" ]; then
    echo "  ✅ 正常（应该=0）"
else
    echo "  ⚠️  发现重复启动尝试（$DUPLICATE_WARNING 次）"
fi
echo ""

echo "6.4 查看 Analysis Cycle 记录:"
docker logs trading_service 2>&1 | grep "📊 Analysis Cycle" | head -5
echo ""

echo "6.5 查看下次分析计划时间:"
docker logs trading_service 2>&1 | grep "Next analysis scheduled" | tail -1
echo ""

# Step 7: 提示实时监控
echo "=========================================="
echo "📊 Step 7: 实时监控（可选）"
echo "=========================================="
echo ""
echo "修复验证完成！"
echo ""
echo "如需实时监控，运行以下命令:"
echo "  ./verify_fix.sh"
echo ""
echo "或者查看完整日志:"
echo "  docker logs -f trading_service"
echo ""
echo "=========================================="
echo "✅ 测试流程完成"
echo "=========================================="
