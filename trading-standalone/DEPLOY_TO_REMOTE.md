# 部署到远端服务器 - 完整步骤

**服务器**: 45.76.159.149
**部署路径**: /root/trading-standalone
**分支**: exp
**日期**: 2025-12-03

---

## 需要部署的更新

### 1. 前端修复 (status.html)
**Commits**:
- `87f3772` - 修复TP/SL显示问题 (移除fallback字段)
- `bad3a1d` - 改进Signals展示 (参考remote-status.sh,修复confidence显示)

**改动**: `trading-standalone/status.html`

### 2. 后端优化 (trading_agents.py)
**Commit**:
- `e87aa54` - 移除Leader的冗余分析工具 (15→4工具)

**改动**: `backend/services/report_orchestrator/app/core/trading/trading_agents.py`

### 3. 文档
- `DEEPSEEK_500_ERROR_ANALYSIS.md` - DeepSeek问题完整分析
- `TRADING_DECISION_MISMATCH_ANALYSIS.md` (已存在)

---

## 部署步骤

### Step 1: SSH连接到远端

```bash
ssh root@45.76.159.149
# 输入密码
```

### Step 2: 进入项目目录并备份

```bash
cd /root/trading-standalone

# 备份当前配置 (可选但推荐)
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
cp status.html status.html.backup.$(date +%Y%m%d_%H%M%S)

# 查看当前状态
git status
git log --oneline -5
```

### Step 3: 拉取最新代码

```bash
# 拉取exp分支的最新代码
git fetch origin exp
git pull origin exp

# 验证是否成功
git log --oneline -5
# 应该看到:
# e87aa54 fix: 移除Leader的冗余分析工具,只保留决策工具 (15→4工具)
# bad3a1d feat: 改进status.html的Signals展示,参考remote-status.sh
# 87f3772 fix: 修复status.html的TP/SL显示问题
```

### Step 4: 验证status.html更新

```bash
# 检查status.html的关键修复
cat status.html | grep -A 5 "Recent Signals"
# 应该看到: <div class="card-title">Recent Signals</div>

cat status.html | grep "take_profit_price"
# 应该看到: position.take_profit_price (没有fallback)

cat status.html | grep "confidence}%"
# 应该看到: ${confidence}% (不是{confidence:.0%})
```

### Step 5: 重启report_orchestrator服务

```bash
# 重启服务以应用trading_agents.py的更改
docker-compose restart report_orchestrator

# 等待服务启动
sleep 10

# 查看日志,确认Leader只注册了4个工具
docker-compose logs --tail=50 report_orchestrator | grep "Registered"
# 应该看到类似:
# Registered 11 analysis tools to TechnicalAnalyst
# Registered 11 analysis tools to MacroEconomist
# ...
# Registered 4 execution tools to Leader (no analysis tools needed)
```

### Step 6: 验证status.html生效

```bash
# 方式1: 使用curl查看HTML
curl -s http://localhost:8000/api/trading/dashboard | grep "Recent Signals"

# 方式2: 触发一次分析,然后查看dashboard
curl -X POST http://localhost:8000/api/trading/trigger

# 等待30秒让分析完成
sleep 30

# 在浏览器打开: http://45.76.159.149:8000/api/trading/dashboard
# 检查:
# 1. TP/SL是否显示正确的数字 (不是N/A)
# 2. Recent Signals区域是否显示信号
# 3. Confidence是否显示正确 (例如55%,不是5500%)
```

### Step 7: 验证Leader工具减少

```bash
# 触发一次交易分析
curl -X POST http://localhost:8000/api/trading/trigger

# 等待分析完成
sleep 40

# 查看日志,确认Leader只使用4个工具
docker-compose logs --tail=100 report_orchestrator | grep -E "Leader|tool"

# 应该看到Leader只调用了: open_long, open_short, hold, close_position
# 不应该看到Leader调用: get_market_price, get_klines等分析工具
```

---

## 验证检查清单

### ✅ 前端 (status.html)

1. [ ] 打开 http://45.76.159.149:8000/api/trading/dashboard
2. [ ] TP/SL显示正确数字 (不是$N/A)
3. [ ] 标题显示 "Recent Signals" (不是"Decision History")
4. [ ] Confidence显示正确 (例如 55%, 不是 5500%)
5. [ ] Status字段显示 (例如 executed, skipped等)
6. [ ] Timestamp格式正确 (YYYY-MM-DD HH:mm:ss)

### ✅ 后端 (trading_agents.py)

1. [ ] 重启日志显示 "Registered 4 execution tools to Leader"
2. [ ] 分析Agent日志显示 "Registered 11 analysis tools"
3. [ ] Leader决策日志不包含分析工具调用
4. [ ] 交易决策仍然正常工作 (能生成long/short/hold信号)

### ✅ 系统健康

1. [ ] 服务正常运行: `docker-compose ps`
2. [ ] 无错误日志: `docker-compose logs --tail=50 report_orchestrator`
3. [ ] API响应正常: `curl http://localhost:8000/api/trading/status`

---

## 回滚步骤 (如果出现问题)

### 回滚代码

```bash
cd /root/trading-standalone

# 回滚到上一个commit (bad3a1d之前)
git reset --hard <previous_commit_hash>

# 或者回滚单个文件
git checkout HEAD~3 trading-standalone/status.html
git checkout HEAD~1 backend/services/report_orchestrator/app/core/trading/trading_agents.py

# 重启服务
docker-compose restart report_orchestrator
```

### 回滚配置

```bash
# 恢复备份的.env
cp .env.backup.YYYYMMDD_HHMMSS .env

# 恢复备份的status.html
cp status.html.backup.YYYYMMDD_HHMMSS status.html

# 重启
docker-compose restart report_orchestrator
```

---

## 常见问题

### Q1: status.html更新了但浏览器还是显示旧版本?

**A**: 浏览器缓存问题

```bash
# 在浏览器中:
1. 打开 http://45.76.159.149:8000/api/trading/dashboard
2. 按 Ctrl+Shift+R (Windows/Linux) 或 Cmd+Shift+R (Mac) 硬刷新
3. 或者打开开发者工具,勾选 "Disable cache"
```

### Q2: 重启report_orchestrator后日志还是显示15个工具?

**A**: 代码没有正确更新

```bash
# 检查文件是否真的更新了
cat backend/services/report_orchestrator/app/core/trading/trading_agents.py | grep -A 10 "is_leader"

# 应该看到:
# is_leader = hasattr(agent, 'id') and agent.id == "Leader"
#
# if not is_leader:
#     # Analysis agents get analysis tools
```

### Q3: 交易决策不再工作了?

**A**: 可能是Leader没有获得执行工具

```bash
# 检查日志
docker-compose logs report_orchestrator | grep "execution tools"

# 应该看到:
# Registered 4 execution tools to Leader

# 如果没看到,回滚代码并重新部署
```

---

## 预期改进

### 性能改进

| 指标 | 修复前 | 修复后 | 改进 |
|------|--------|--------|------|
| Leader工具数量 | 15个 | 4个 | -73% |
| 请求大小 | ~35KB | ~15KB | -57% |
| Token使用 | ~8K tokens | ~3K tokens | -62% |

### DeepSeek兼容性

- ✅ 请求大小从35KB降到15KB (更可能符合DeepSeek限制)
- ✅ 工具数量从15个降到4个 (更可能符合DeepSeek限制)
- ⏳ 待测试: 是否可以将DEFAULT_LLM_PROVIDER改回deepseek

---

## 部署完成确认

完成以上步骤后,请在此确认:

- [ ] 代码已成功拉取 (git log显示最新commits)
- [ ] status.html修复已验证 (浏览器显示正确)
- [ ] report_orchestrator已重启 (日志显示4个工具)
- [ ] 交易功能正常 (能触发分析并生成信号)
- [ ] 无错误日志 (docker-compose logs正常)

**部署时间**: _______________
**部署人**: _______________
**验证人**: _______________

---

## 下一步 (可选)

### 测试DeepSeek

现在工具数量减少了,可以尝试测试DeepSeek是否可以工作:

```bash
# 备份当前环境变量
cp .env .env.gemini

# 修改为DeepSeek
nano .env
# 将 DEFAULT_LLM_PROVIDER=gemini 改为 DEFAULT_LLM_PROVIDER=deepseek

# 重启服务
docker-compose restart report_orchestrator

# 等待启动
sleep 10

# 触发测试
curl -X POST http://localhost:8000/api/trading/trigger

# 等待分析
sleep 40

# 查看日志,检查是否还有500错误
docker-compose logs --tail=100 report_orchestrator | grep -E "500|error|Leader"

# 如果还是失败,改回Gemini
cp .env.gemini .env
docker-compose restart report_orchestrator
```

---

**文档创建日期**: 2025-12-03
**最后更新**: 2025-12-03
**相关文档**:
- DEEPSEEK_500_ERROR_ANALYSIS.md
- TRADING_DECISION_MISMATCH_ANALYSIS.md
