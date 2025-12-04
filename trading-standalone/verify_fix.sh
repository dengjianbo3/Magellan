#!/bin/bash
# 验证双重触发问题是否已修复

echo "=========================================="
echo "🔍 验证双重触发修复 - 实时监控"
echo "=========================================="
echo ""

echo "📊 监控以下关键指标:"
echo "  1. Trading system 启动次数（应该=1）"
echo "  2. Scheduler 启动次数（应该=1）"
echo "  3. Analysis cycle 序号和时间间隔"
echo "  4. 是否有重复启动警告"
echo ""
echo "按 Ctrl+C 停止监控"
echo "=========================================="
echo ""

# 实时监控trading_service日志
docker logs -f trading_service 2>&1 | grep --line-buffered -E "(🚀 Starting trading system|Trading scheduler started|📊 Analysis Cycle|⚠️.*already|Next analysis scheduled)" | while read line; do
    timestamp=$(date '+%H:%M:%S')
    echo "[$timestamp] $line"
done
