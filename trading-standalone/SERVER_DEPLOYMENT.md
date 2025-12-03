# Trading-Standalone 服务器部署指南

## 问题诊断

如果看到以下错误:
```
[Agent:Leader] Using Tool Calling with 15 tools
HTTP Request: POST http://llm_gateway:8003/v1/chat/completions "HTTP/1.1 500 Internal Server Error"
[Agent:Leader] LLM call failed on attempt 1/3
```

说明 LLM provider 配置不正确。

## 部署步骤

### 1. 拉取最新代码

```bash
cd /path/to/Magellan
git pull origin exp
```

### 2. **关键步骤: 更新 .env 文件**

⚠️ **重要**: 必须更新 `.env` 文件中的 `DEFAULT_LLM_PROVIDER`

```bash
cd trading-standalone

# 方法1: 直接编辑 .env 文件
nano .env

# 修改这一行:
DEFAULT_LLM_PROVIDER=deepseek  # 从 gemini 改为 deepseek

# 方法2: 使用 sed 命令直接替换
sed -i 's/DEFAULT_LLM_PROVIDER=.*/DEFAULT_LLM_PROVIDER=deepseek/' .env
```

### 3. 验证 .env 配置

```bash
# 检查 DEFAULT_LLM_PROVIDER 是否正确
grep DEFAULT_LLM_PROVIDER .env

# 应该显示:
# DEFAULT_LLM_PROVIDER=deepseek
```

### 4. 停止旧容器

```bash
docker-compose down
```

### 5. 重新构建镜像 (包含最新的保证金修复)

```bash
docker-compose build --no-cache trading_service
```

### 6. 启动服务

```bash
docker-compose up -d
```

### 7. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f trading_service

# 应该看到:
# - 没有 "500 Internal Server Error" 错误
# - Leader Agent 成功执行 tool calling
# - 看到 "true_available_margin" 字段
```

### 8. 测试交易功能

```bash
# 启动交易会话
curl -X POST http://localhost:8000/api/trading/start

# 触发分析
curl -X POST http://localhost:8000/api/trading/trigger

# 等待 60 秒后查看日志
sleep 60
docker-compose logs --tail=100 trading_service | grep -E "Leader|decision|true_available_margin"
```

## 验证清单

- [ ] `.env` 文件中 `DEFAULT_LLM_PROVIDER=deepseek`
- [ ] 容器已停止并重新构建
- [ ] 日志中没有 500 错误
- [ ] Leader Agent 成功执行 tool calling
- [ ] 看到 `true_available_margin` 字段
- [ ] 交易决策正常执行 (open_long/open_short/hold)

## 常见问题

### Q: 为什么要使用 deepseek 而不是 gemini?

A: Gemini 的 OpenAI 兼容 API (`/v1/chat/completions`) 对复杂 tool calling 支持不完善,尤其是:
- 15+ 工具时经常返回 500 错误
- Tool choice 强制执行不稳定
- 复杂参数 schema 处理有问题

DeepSeek 提供完整的 OpenAI API 兼容性,包括原生 tool calling 支持。

### Q: 如果服务器上没有 DeepSeek API Key 怎么办?

A: 可以使用 Kimi (Moonshot AI):
```bash
# 在 .env 中设置
DEFAULT_LLM_PROVIDER=kimi
```

Kimi 也有良好的 OpenAI API 兼容性。

### Q: 保证金修复包含哪些内容?

A: 主要修复:
1. 添加 `true_available_margin` 字段 (考虑浮动盈亏)
2. 双重余额检查防止过度开仓
3. Agent 可以看到真实可用保证金
4. 详细的错误提示信息

参见: `MARGIN_CALCULATION_FIX.md`

## 技术细节

### LLM Provider 切换原理

docker-compose.yml 中的环境变量:
```yaml
environment:
  - DEFAULT_LLM_PROVIDER=${DEFAULT_LLM_PROVIDER:-deepseek}
```

这会从 `.env` 文件读取 `DEFAULT_LLM_PROVIDER` 并传递给容器。

### 保证金计算公式

```
总权益 (Total Equity) = 账户余额 + 已用保证金 + 未实现盈亏
真实可用保证金 (True Available Margin) = 总权益 - 已用保证金
```

Agent 在查询余额时会看到:
```json
{
  "⚠️ 使用这个值开仓": "↓ true_available_margin ↓",
  "true_available_margin": "$7,500.00",
  "说明": "真实可用保证金 = 总权益 - 已用保证金 (考虑了浮动盈亏)",
  "total_equity": "$10,000.00",
  "available_balance": "$8,000.00 (仅现金余额)",
  ...
}
```

## 紧急回滚

如果新版本有问题,可以回滚到之前的 commit:

```bash
cd /path/to/Magellan
git checkout <previous_commit_hash>
cd trading-standalone
docker-compose down
docker-compose build --no-cache trading_service
docker-compose up -d
```

---

**最后更新**: 2025-12-03
**相关文档**:
- MARGIN_CALCULATION_FIX.md
- TRADING_EXECUTION_ISSUE_ANALYSIS.md
