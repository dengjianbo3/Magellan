#!/bin/bash
# 触发新的交易分析

echo "正在触发新的交易分析..."
curl -X POST http://localhost:8000/api/trading/analyze

echo ""
echo "分析已触发，请查看日志："
echo "docker logs -f trading_service | grep -A 5 'SignalExtraction'"
