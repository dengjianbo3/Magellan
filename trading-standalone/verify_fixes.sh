#!/bin/bash
# 快速验证脚本 - 检查最新修复是否生效

echo "🔍 检查 None 检查修复..."
echo ""

cd ~/Magellan/trading-standalone || exit 1

# 1. 检查关键修复是否存在
echo "1️⃣ 验证 trading_meeting.py 修复..."
if grep -q "if not hasattr(self, 'toolkit') or not self.toolkit:" ../backend/services/report_orchestrator/app/core/trading/trading_meeting.py; then
    echo "   ✅ toolkit检查已添加"
else
    echo "   ❌ toolkit检查缺失"
fi

if grep -q "position_context.direction or 'unknown'" ../backend/services/report_orchestrator/app/core/trading/trading_meeting.py; then
    echo "   ✅ direction安全访问已添加"
else
    echo "   ❌ direction安全访问缺失"
fi

echo ""
echo "2️⃣ 验证 position_context.py 修复..."
if grep -q "(self.direction or 'unknown').upper()" ../backend/services/report_orchestrator/app/core/trading/position_context.py; then
    echo "   ✅ position_context direction安全访问已添加"
else
    echo "   ❌ position_context direction安全访问缺失"
fi

echo ""
echo "3️⃣ 检查Python语法..."
python3 -m py_compile ../backend/services/report_orchestrator/app/core/trading/trading_meeting.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ trading_meeting.py 语法正确"
else
    echo "   ❌ trading_meeting.py 有语法错误"
fi

python3 -m py_compile ../backend/services/report_orchestrator/app/core/trading/position_context.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ position_context.py 语法正确"
else
    echo "   ❌ position_context.py 有语法错误"
fi

echo ""
echo "4️⃣ 检查服务运行状态..."
if docker compose ps | grep -q "trading-service.*Up"; then
    echo "   ✅ trading-service 正在运行"
    
    echo ""
    echo "5️⃣ 检查最近日志（是否有AttributeError）..."
    ERROR_COUNT=$(docker compose logs trading-service --tail=500 | grep -c "AttributeError\|NoneType.*has no attribute")
    if [ "$ERROR_COUNT" -eq 0 ]; then
        echo "   ✅ 没有发现 AttributeError"
    else
        echo "   ⚠️  发现 $ERROR_COUNT 个 AttributeError"
        echo "   最近的错误："
        docker compose logs trading-service --tail=500 | grep "AttributeError\|NoneType.*has no attribute" | tail -3
    fi
    
    echo ""
    echo "6️⃣ 检查最近的分析周期..."
    CYCLE_COUNT=$(docker compose logs trading-service --tail=200 | grep -c "📊 Analysis Cycle.*START")
    if [ "$CYCLE_COUNT" -gt 0 ]; then
        echo "   ✅ 发现 $CYCLE_COUNT 个分析周期"
        
        ERROR_IN_CYCLE=$(docker compose logs trading-service --tail=200 | grep "Error in analysis cycle" | wc -l)
        if [ "$ERROR_IN_CYCLE" -eq 0 ]; then
            echo "   ✅ 所有分析周期都成功完成"
        else
            echo "   ⚠️  发现 $ERROR_IN_CYCLE 个分析周期错误"
        fi
    else
        echo "   ℹ️  没有发现最近的分析周期"
    fi
else
    echo "   ❌ trading-service 未运行"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 验证总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "如果所有项目都是 ✅，说明修复已正确部署。"
echo "如果有 ⚠️ 或 ❌，请检查日志并重新部署。"
echo ""
echo "完整日志查看："
echo "  bash view-logs.sh"
echo ""
