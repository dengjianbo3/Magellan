#!/bin/bash
# 检查服务器交易日志

SERVER="45.76.159.149"

echo "========== 检查服务器日志 =========="
echo ""

# 这个需要 SSH 访问，你可以直接在服务器上运行以下命令：
cat << 'EOF'
请在服务器上运行以下命令查看日志：

# 查看最近的交易服务日志
docker compose logs --tail=100 trading_service | grep -E "analysis|error|Error|cycle|scheduler|meeting"

# 查看是否有异常
docker compose logs --tail=50 trading_service | grep -i error

# 查看调度器状态
docker compose logs trading_service | grep -E "Scheduler|Next analysis|Starting analysis"

# 实时跟踪日志
docker compose logs -f trading_service
EOF
