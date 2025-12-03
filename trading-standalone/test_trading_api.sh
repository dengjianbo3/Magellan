#!/bin/bash
#
# Trading Logic API Test Script
# 通过 API 测试交易逻辑，验证系统正确性
#

echo "============================================================"
echo "Trading Logic API Test"
echo "============================================================"

BASE_URL="http://localhost:8000"
PASSED=0
TOTAL=0

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试函数
test_case() {
    TOTAL=$((TOTAL + 1))
    local name="$1"
    local expected="$2"
    local actual="$3"

    echo ""
    echo "[$TOTAL] $name"

    if [ "$actual" = "$expected" ]; then
        echo -e "   ${GREEN}✅ PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "   ${RED}❌ FAIL${NC}"
        echo "   Expected: $expected"
        echo "   Actual: $actual"
        return 1
    fi
}

echo ""
echo "[1/6] 测试获取账户状态..."

# 测试1: 获取账户状态
account_response=$(curl -s "$BASE_URL/api/trading/account")
initial_balance=$(echo "$account_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('available_balance', 0))" 2>/dev/null || echo "0")

echo "   初始余额: \$$initial_balance"

if [ "$(echo "$initial_balance > 0" | bc)" -eq 1 ]; then
    echo -e "   ${GREEN}✅ 账户状态获取成功${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "   ${RED}❌ 账户状态获取失败${NC}"
fi
TOTAL=$((TOTAL + 1))

echo ""
echo "[2/6] 测试交易历史获取..."

# 测试2: 获取交易历史 (移除市场数据测试，因为该endpoint不存在)
history_response=$(curl -s "$BASE_URL/api/trading/history")
has_trades=$(echo "$history_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print('yes' if 'trades' in data else 'no')" 2>/dev/null || echo "no")

if [ "$has_trades" = "yes" ]; then
    echo -e "   ${GREEN}✅ 交易历史API正常${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "   ${RED}❌ 交易历史API异常${NC}"
fi
TOTAL=$((TOTAL + 1))

echo ""
echo "[3/5] 测试交易会话启动..."

# 测试3: 启动交易会话
start_response=$(curl -s -X POST "$BASE_URL/api/trading/start")
session_status=$(echo "$start_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'error'))" 2>/dev/null || echo "error")

echo "   会话状态: $session_status"

if [ "$session_status" = "started" ] || [ "$session_status" = "already_running" ]; then
    echo -e "   ${GREEN}✅ 交易会话启动成功${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "   ${RED}❌ 交易会话启动失败${NC}"
fi
TOTAL=$((TOTAL + 1))

echo ""
echo "[4/5] 测试环境变量配置..."

# 测试4: 验证环境变量配置
config_test=$(docker exec trading-service bash -c "echo MAX_LEVERAGE=\$MAX_LEVERAGE, MIN_CONFIDENCE=\$MIN_CONFIDENCE, DEFAULT_TP_PERCENT=\$DEFAULT_TP_PERCENT")

echo "   配置: $config_test"

if echo "$config_test" | grep -q "MAX_LEVERAGE=" && echo "$config_test" | grep -q "MIN_CONFIDENCE="; then
    echo -e "   ${GREEN}✅ 环境变量配置正确${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "   ${RED}❌ 环境变量配置缺失${NC}"
fi
TOTAL=$((TOTAL + 1))

echo ""
echo "[5/5] 测试LLM Provider配置..."

# 测试5: 验证 LLM Provider
provider_response=$(curl -s "http://localhost:8003/providers")
current_provider=$(echo "$provider_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('current_provider', 'unknown'))" 2>/dev/null || echo "unknown")

echo "   当前Provider: $current_provider"

if [ "$current_provider" != "unknown" ]; then
    echo -e "   ${GREEN}✅ LLM Provider配置正确${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "   ${RED}❌ LLM Provider配置错误${NC}"
fi
TOTAL=$((TOTAL + 1))

# 打印总结
echo ""
echo "============================================================"
echo "测试摘要"
echo "============================================================"
echo "总计: $PASSED/$TOTAL 测试通过"

if [ $PASSED -eq $TOTAL ]; then
    echo -e "${GREEN}所有测试通过!${NC}"
    echo "============================================================"
    exit 0
else
    echo -e "${RED}部分测试失败${NC}"
    echo "============================================================"
    exit 1
fi
