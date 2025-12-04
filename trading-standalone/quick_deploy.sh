#!/bin/bash
# 快速部署脚本 - v1.1.0 Position-Aware System
# 使用方法: ./quick_deploy.sh

set -e  # 遇到错误立即退出

echo "🚀 开始部署 v1.1.0 - Position-Aware System"
echo "========================================"
echo ""

# 1. 检查当前分支
echo "📌 Step 1: 检查Git分支"
current_branch=$(git rev-parse --abbrev-ref HEAD)
echo "   当前分支: $current_branch"

if [ "$current_branch" != "exp" ]; then
    echo "   ⚠️  警告: 当前不在exp分支，正在切换..."
    git checkout exp
fi

# 2. 拉取最新代码
echo ""
echo "📥 Step 2: 拉取最新代码"
git fetch origin
git pull origin exp
echo "   ✅ 代码已更新"

# 3. 查看最新commit
echo ""
echo "📋 Step 3: 最新更新"
git log -1 --oneline
echo ""

# 4. 停止现有服务
echo "🛑 Step 4: 停止现有服务"
docker-compose down
echo "   ✅ 服务已停止"

# 5. 重新构建镜像
echo ""
echo "🔨 Step 5: 重新构建trading-service镜像"
echo "   (这可能需要2-3分钟...)"
docker-compose build --no-cache trading-service
echo "   ✅ 镜像构建完成"

# 6. 启动服务
echo ""
echo "▶️  Step 6: 启动服务"
docker-compose up -d
echo "   ✅ 服务已启动"

# 7. 等待服务就绪
echo ""
echo "⏳ Step 7: 等待服务启动 (30秒)..."
sleep 30

# 8. 检查服务状态
echo ""
echo "🔍 Step 8: 检查服务状态"
docker-compose ps
echo ""

# 9. 检查日志
echo "📄 Step 9: 最近日志 (最后20行)"
echo "========================================"
docker-compose logs trading-service | tail -20
echo "========================================"
echo ""

# 10. 验证API
echo "🧪 Step 10: 验证API"
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ API健康检查通过"
else
    echo "   ❌ API健康检查失败"
    exit 1
fi

# 完成
echo ""
echo "🎉 部署完成！"
echo "========================================"
echo ""
echo "📊 下一步："
echo "   1. 触发分析:"
echo "      curl -X POST http://localhost:8000/api/trading/start"
echo ""
echo "   2. 监控日志:"
echo "      docker-compose logs -f trading-service | grep -E \"(持仓|Position|决策)\""
echo ""
echo "   3. 查看持仓:"
echo "      curl http://localhost:8000/api/trading/position | jq '.'"
echo ""
echo "   4. 查看历史:"
echo "      curl http://localhost:8000/api/trading/history?limit=5 | jq '.'"
echo ""
echo "📚 详细文档: ./DEPLOY_GUIDE.md"
echo ""
