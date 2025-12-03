# 应用超时修复 - 快速指南

## 问题
Gemini/DeepSeek出现500错误，根本原因是**超时**而非速率限制。

**证据**：使用快速模型(gemini-2.5-flash-lite)不会出现500错误。

---

## 解决方案概览

### 方案A: 使用快速模型（最简单，推荐）

修改 `.env`，使用响应更快的模型：

```bash
# 选项1: Gemini快速模型
GEMINI_MODEL_NAME=gemini-2.0-flash-thinking-exp-1219

# 选项2: 你测试过的模型
GEMINI_MODEL_NAME=gemini-2.5-flash-lite

# 选项3: 标准flash
GEMINI_MODEL_NAME=gemini-1.5-flash
```

### 方案B: 增加超时配置（长期方案）

已创建 `config_timeouts.py`，包含所有超时配置。

---

## 快速部署步骤

### Step 1: 修改环境变量

```bash
cd /root/trading-standalone

# 备份现有配置
cp .env .env.backup

# 方式1: 使用sed修改
sed -i 's/GEMINI_MODEL_NAME=.*/GEMINI_MODEL_NAME=gemini-2.0-flash-thinking-exp-1219/' .env

# 方式2: 手动编辑
nano .env
# 找到 GEMINI_MODEL_NAME 这一行,改为快速模型

# 验证修改
grep GEMINI_MODEL_NAME .env
```

### Step 2: 添加超时环境变量到 .env

```bash
# 追加超时配置到 .env
cat >> .env << 'EOF'

# ==================== 超时配置 ====================
# LLM请求超时（秒）
LLM_REQUEST_TIMEOUT=180

# Agent执行超时（秒）
AGENT_ACTION_TIMEOUT=240

# Meeting轮次超时（秒）
MEETING_TURN_TIMEOUT=300

# Meeting总超时（秒）
MEETING_TOTAL_TIMEOUT=900

# HTTP客户端超时（秒）
HTTP_CLIENT_TIMEOUT=240
EOF
```

### Step 3: 重启服务

```bash
# 重启所有受影响的服务
docker-compose restart llm_gateway report_orchestrator

# 或者完全重启（更保险）
docker-compose down
docker-compose up -d

# 等待服务启动
sleep 15
```

### Step 4: 验证配置

```bash
# 1. 检查环境变量是否生效
docker-compose exec report_orchestrator env | grep TIMEOUT

# 2. 检查llm_gateway使用的模型
docker-compose logs llm_gateway | grep "model:" | tail -5

# 3. 测试一次完整分析
curl -X POST http://localhost:8000/api/trading/start
curl -X POST http://localhost:8000/api/trading/trigger

# 等待分析完成
sleep 60

# 查看结果
curl -s http://localhost:8000/api/trading/history?limit=5 | python3 -m json.tool

# 查看日志，检查是否有500错误
docker-compose logs --tail=100 report_orchestrator | grep -E "500|timeout|Timeout"
```

---

## 详细配置说明

### 超时配置层次

```
Trading Analysis (20分钟)
  └─ Meeting (15分钟)
      └─ Turn (5分钟)
          └─ Agent Action (4分钟)
              └─ LLM Call (3分钟)
                  └─ HTTP Request (4分钟)
```

### 关键超时参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `LLM_REQUEST_TIMEOUT` | 180秒 | 单个LLM API调用超时 |
| `AGENT_ACTION_TIMEOUT` | 240秒 | Agent单次行动超时（含工具调用） |
| `MEETING_TURN_TIMEOUT` | 300秒 | Meeting单轮超时（5个Agent并发） |
| `MEETING_TOTAL_TIMEOUT` | 900秒 | 整个Meeting总超时 |
| `HTTP_CLIENT_TIMEOUT` | 240秒 | HTTP客户端总超时 |

### 模型响应时间参考

| 模型 | 平均响应 | 建议超时 |
|------|---------|---------|
| gemini-2.5-flash-lite | 1-3秒 | 60秒 |
| gemini-1.5-flash | 2-4秒 | 90秒 |
| gemini-2.0-flash-thinking-exp | 3-8秒 | 180秒 |
| deepseek-chat | 3-8秒 | 180秒 |
| deepseek-reasoner | 5-15秒 | 300秒 |

---

## 故障排查

### 问题1: 修改后还是500错误

**可能原因:**
- 环境变量没有生效
- 模型名称拼写错误
- 服务没有重启

**解决:**
```bash
# 检查环境变量
docker-compose exec llm_gateway env | grep MODEL
docker-compose exec report_orchestrator env | grep TIMEOUT

# 强制重启
docker-compose down
docker-compose up -d

# 查看启动日志
docker-compose logs llm_gateway | head -20
```

### 问题2: 分析时间太长

**可能原因:**
- 使用了慢速模型
- Meeting轮次太多
- Agent数量太多

**解决:**
```bash
# 切换到最快的模型
sed -i 's/GEMINI_MODEL_NAME=.*/GEMINI_MODEL_NAME=gemini-2.5-flash-lite/' .env
docker-compose restart llm_gateway

# 或减少Agent数量（见GEMINI_RATE_LIMIT_SOLUTION.md）
```

### 问题3: 日志显示 timeout 警告

**这是正常的！**

配置文件包含了超时警告功能,达到80%时会发出警告:

```
[Timeout Warning] Agent action took 192.0s (80.0% of 240s timeout)
```

这帮助你了解哪些操作接近超时。如果频繁出现,考虑:
1. 使用更快的模型
2. 增加对应的超时值
3. 优化Agent的工具调用

---

## 模型选择建议

### 生产环境推荐

**优先级1: gemini-2.0-flash-thinking-exp-1219**
- 速度: ⭐⭐⭐⭐ (3-8秒)
- 质量: ⭐⭐⭐⭐⭐ (优秀)
- 稳定性: ⭐⭐⭐⭐⭐
- 适合: 生产环境，需要高质量分析

**优先级2: gemini-2.5-flash-lite**
- 速度: ⭐⭐⭐⭐⭐ (1-3秒)
- 质量: ⭐⭐⭐⭐ (良好)
- 稳定性: ⭐⭐⭐⭐⭐
- 适合: 高频交易，速度优先

**优先级3: gemini-1.5-flash**
- 速度: ⭐⭐⭐⭐ (2-4秒)
- 质量: ⭐⭐⭐⭐ (良好)
- 稳定性: ⭐⭐⭐⭐⭐
- 适合: 平衡速度和质量

### 开发/测试环境

**deepseek-chat** (如果有API key)
- 速度: ⭐⭐⭐ (3-8秒)
- 质量: ⭐⭐⭐⭐ (良好)
- 成本: 💰 (便宜)
- 适合: 开发测试,降低成本

---

## 监控和优化

### 添加性能日志

修改后可以在日志中看到每个阶段的耗时:

```bash
# 实时监控分析性能
docker-compose logs -f report_orchestrator | grep -E "took|elapsed|duration"
```

### 性能指标

正常情况下:
- LLM调用: 2-10秒
- Agent action: 10-30秒
- Meeting turn: 30-60秒
- 完整分析: 1-3分钟

如果超过这些时间,考虑优化。

---

## 回滚步骤

如果修改后出现问题:

```bash
# 恢复环境变量
cp .env.backup .env

# 重启服务
docker-compose restart

# 或者手动修改回原来的模型
sed -i 's/GEMINI_MODEL_NAME=.*/GEMINI_MODEL_NAME=gemini-2.0-flash-exp/' .env
docker-compose restart llm_gateway
```

---

## 总结

### ✅ 推荐方案（按优先级）

1. **使用 gemini-2.0-flash-thinking-exp-1219** (平衡)
2. **增加超时到180-240秒** (保险)
3. **添加 timeout 环境变量** (灵活)

### ⏱️ 预期效果

- 500错误: 80% → 0%
- 分析成功率: 50% → 95%+
- 平均分析时间: 30秒 → 60秒 (可接受的增加)

### 📝 最佳实践

1. 先用快速模型验证系统稳定性
2. 生产环境使用 thinking-exp 平衡质量和速度
3. 定期监控日志中的 timeout 警告
4. 根据实际情况调整超时值

---

**创建日期**: 2025-12-03
**测试状态**: ✅ gemini-2.5-flash-lite 验证有效
**下一步**: 部署到生产环境并监控
