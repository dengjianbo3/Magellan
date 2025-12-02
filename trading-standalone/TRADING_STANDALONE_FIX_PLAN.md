# Trading-Standalone 复刻问题分析与修复计划

## 1. 问题概述

trading-standalone 是主项目 Magellan 自动交易功能的独立部署版本。测试发现以下问题：
- 分析 Agent (technical_analyst, macro_economist 等) 未能正确加载
- 工具 (tavily_search, get_market_price 等) 已注册但未被 LLM 调用
- LLM 直接生成文本而不是调用工具

---

## 2. 根本原因分析

### 2.1 Agent 加载失败

**错误日志**:
```
Failed to load agent 'technical_analyst' from registry: Agent 'technical_analyst' not found in registry
Failed to load agent 'macro_economist' from registry: Agent 'macro_economist' not found in registry
...
```

**原因分析**:
- `trading_agents.py` 通过 `AgentRegistry` 从 `config/agents.yaml` 加载 agent
- `AgentRegistry` 在初始化时寻找 `config/agents.yaml` 文件
- Docker 容器中 `config/agents.yaml` 可能未正确挂载或路径不对

**验证方法**:
```bash
# 进入 trading-service 容器检查
docker exec -it trading-service ls -la /app/config/
docker exec -it trading-service cat /app/config/agents.yaml
```

### 2.2 工具未被调用

**错误日志**:
```
[Agent:Leader] Tool registered: tavily_search
...
No decision tool (open_long/open_short/hold) was executed by Leader
```

**原因分析**:
1. **工具调用格式**: `trading_meeting.py` 期望 LLM 输出 `[USE_TOOL: tool_name(params)]` 格式
2. **Prompt 不足**: Agent 的 system_prompt 没有明确说明工具调用格式
3. **LLM 提供商差异**: Deepseek 可能不支持或不习惯这种自定义工具调用格式

**关键代码** (trading_meeting.py:659-661):
```python
# Check for tool calls in the content using [USE_TOOL: tool_name(params)] format
tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
tool_matches = re.findall(tool_pattern, content)
```

### 2.3 只有 Leader Agent 存在

**原因**: 分析 agent 加载失败后，`create_trading_agents()` 只成功创建了 Leader
- Leader 是通过 `create_leader()` 函数直接创建，不依赖 AgentRegistry
- 其他 agent 依赖 AgentRegistry 从 agents.yaml 加载

---

## 3. 组件对比清单

### 3.1 必需文件清单

| 文件 | 主项目位置 | trading-standalone | 状态 |
|------|-----------|-------------------|------|
| agents.yaml | `config/agents.yaml` | 需要挂载到容器 | ❌ 待验证 |
| workflows.yaml | `config/workflows.yaml` | 需要挂载到容器 | ❌ 待验证 |
| trading_agents.py | `app/core/trading/` | 共用主项目代码 | ✅ 已存在 |
| trading_meeting.py | `app/core/trading/` | 共用主项目代码 | ✅ 已存在 |
| trading_tools.py | `app/core/trading/` | 共用主项目代码 | ✅ 已存在 |
| investment_agents.py | `app/core/roundtable/` | 共用主项目代码 | ✅ 已存在 |
| agent_registry.py | `app/core/` | 共用主项目代码 | ✅ 已存在 |

### 3.2 Agent 配置对比

**主项目 agents.yaml 中的交易相关 Agent**:
- `technical_analyst`: 技术分析师 (K线、技术指标)
- `macro_economist`: 宏观经济分析师
- `sentiment_analyst`: 情绪分析师
- `risk_assessor`: 风险评估师
- `quant_strategist`: 量化策略师

**trading_agents.py 期望加载的 Agent**:
```python
analysis_agent_ids = [
    "technical_analyst",
    "macro_economist",
    "sentiment_analyst",
    "risk_assessor",
    "quant_strategist",
]
```

### 3.3 工具配置对比

**TradingToolkit 提供的工具**:
| 工具 | 功能 | 分类 |
|------|------|------|
| get_market_price | 获取市场价格 | analysis |
| get_klines | 获取K线数据 | analysis |
| calculate_technical_indicators | 计算技术指标 | analysis |
| get_account_balance | 获取账户余额 | analysis |
| get_current_position | 获取当前持仓 | analysis |
| get_fear_greed_index | 恐慌贪婪指数 | analysis |
| get_funding_rate | 资金费率 | analysis |
| get_trade_history | 交易历史 | analysis |
| tavily_search | 网络搜索 | analysis |
| open_long | 开多仓 | execution |
| open_short | 开空仓 | execution |
| close_position | 平仓 | execution |
| hold | 观望 | execution |

---

## 4. 修复计划

### Phase 1: 配置文件挂载修复

**问题**: Docker 容器中缺少 config/agents.yaml 和 config/workflows.yaml

**修复步骤**:
1. 修改 `docker-compose.yml`，添加配置文件挂载
2. 验证容器内配置文件正确加载

**具体修改 (docker-compose.yml)**:
```yaml
trading_service:
  volumes:
    - ./logs:/app/logs
    - ./config.yaml:/app/config.yaml:ro
    # 添加以下挂载
    - ../backend/services/report_orchestrator/config/agents.yaml:/app/config/agents.yaml:ro
    - ../backend/services/report_orchestrator/config/workflows.yaml:/app/config/workflows.yaml:ro
```

### Phase 2: 工具调用格式修复

**问题**: LLM 不知道如何调用工具

**修复方案**: 在 Agent 的 system_prompt 中添加工具调用指令

**方案 A: 修改 ReWOOAgent/Agent 基类** (推荐)

在 `agent.py` 或 `rewoo_agent.py` 的 `_build_system_prompt()` 方法中添加工具使用说明：

```python
def _build_system_prompt(self):
    base_prompt = self.role_prompt or self.system_prompt

    # 添加工具调用格式说明
    if hasattr(self, 'tools') and self.tools:
        tools_description = "\n## 可用工具\n"
        tools_description += "你可以使用以下工具获取数据。调用工具时，请使用以下格式：\n"
        tools_description += "`[USE_TOOL: tool_name(param1=\"value1\", param2=\"value2\")]`\n\n"
        tools_description += "可用工具列表：\n"
        for tool_name, tool in self.tools.items():
            tools_description += f"- `{tool_name}`: {tool.description}\n"

        base_prompt += tools_description

    return base_prompt
```

**方案 B: 修改 trading_meeting.py 中的 prompt**

在 `_run_market_analysis_phase()` 的 prompt 中添加工具调用格式说明：

```python
# 在每个 agent 的 prompt 前面加上工具调用格式说明
tool_instruction = """
**重要：工具调用格式**
当你需要使用工具时，请使用以下格式：
`[USE_TOOL: tool_name(param1="value1", param2="value2")]`

例如：
- 获取价格: [USE_TOOL: get_market_price(symbol="BTC-USDT-SWAP")]
- 搜索新闻: [USE_TOOL: tavily_search(query="Bitcoin news today")]
- 获取指标: [USE_TOOL: calculate_technical_indicators(symbol="BTC-USDT-SWAP", timeframe="4h")]

"""
```

### Phase 3: Agent 创建逻辑验证

**问题**: 确保 Agent 创建函数正确工作

**验证步骤**:
1. 检查 `investment_agents.py` 中是否有 `create_technical_analyst`, `create_macro_economist` 等函数
2. 确认这些函数被正确导出并可被 AgentRegistry 调用

**如果缺少创建函数，需要添加**:
```python
def create_technical_analyst(language: str = "zh", **kwargs) -> Agent:
    """创建技术分析师 Agent"""
    # ... 实现
```

### Phase 4: 测试验证

**测试步骤**:
1. 重建 Docker 镜像: `docker-compose build trading_service`
2. 启动服务: `docker-compose up -d`
3. 检查 agent 加载: `docker logs trading-service | grep -i agent`
4. 触发分析: `curl -X POST http://localhost:8000/api/trading/trigger`
5. 检查工具调用: `docker logs trading-service | grep -i "USE_TOOL\|Executing tool"`

---

## 5. 详细检查清单

### 5.1 Docker 配置检查

- [ ] `docker-compose.yml` 正确挂载 `config/agents.yaml`
- [ ] `docker-compose.yml` 正确挂载 `config/workflows.yaml`
- [ ] 容器能访问这些配置文件
- [ ] AgentRegistry 能正确加载配置

### 5.2 Agent 配置检查

- [ ] `agents.yaml` 包含 technical_analyst 定义
- [ ] `agents.yaml` 包含 macro_economist 定义
- [ ] `agents.yaml` 包含 sentiment_analyst 定义
- [ ] `agents.yaml` 包含 risk_assessor 定义
- [ ] `agents.yaml` 包含 quant_strategist 定义
- [ ] 每个 agent 的 `class_path` 指向正确的创建函数

### 5.3 工具调用检查

- [ ] Agent system_prompt 包含工具调用格式说明
- [ ] 工具调用格式与 `trading_meeting.py` 中的正则匹配
- [ ] LLM 能正确解析并输出工具调用格式
- [ ] 工具执行结果正确返回给 LLM

### 5.4 集成测试

- [ ] 启动服务无错误
- [ ] 触发分析创建所有 agent
- [ ] 每个 agent 都能调用分析工具
- [ ] Leader 能调用执行工具 (open_long/open_short/hold)
- [ ] tavily_search 被调用并返回结果

---

## 6. 预期结果

修复完成后，trading-standalone 应该：
1. 成功加载所有 5 个分析 agent + Leader
2. 每个 agent 在分析阶段使用工具获取数据
3. tavily_search 工具被调用获取市场新闻
4. Leader 在最终决策阶段调用 open_long/open_short/hold 工具
5. 完整的交易分析流程正常运行

---

## 7. 执行顺序

1. **Phase 1** (优先级: 高): 修复配置文件挂载
2. **Phase 2** (优先级: 高): 修复工具调用格式
3. **Phase 3** (优先级: 中): 验证 agent 创建逻辑
4. **Phase 4** (优先级: 高): 测试验证

---

## 8. 附录

### A. 相关代码文件位置

```
backend/services/report_orchestrator/
├── app/
│   ├── core/
│   │   ├── agent_registry.py        # Agent 注册表
│   │   ├── roundtable/
│   │   │   ├── agent.py             # Agent 基类
│   │   │   ├── rewoo_agent.py       # ReWOO Agent
│   │   │   ├── investment_agents.py # Agent 创建函数
│   │   │   └── tool.py              # FunctionTool 类
│   │   └── trading/
│   │       ├── trading_agents.py    # 交易 Agent 编排
│   │       ├── trading_meeting.py   # 交易会议流程
│   │       └── trading_tools.py     # 交易工具定义
│   └── api/
│       └── trading_routes.py        # API 路由
└── config/
    ├── agents.yaml                  # Agent 配置
    └── workflows.yaml               # Workflow 配置
```

### B. 工具调用正则表达式

```python
# trading_meeting.py 中的工具调用匹配模式
tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'

# 示例匹配
"[USE_TOOL: get_market_price(symbol=\"BTC-USDT-SWAP\")]"
"[USE_TOOL: tavily_search(query=\"Bitcoin news\")]"
```

---

*创建时间: 2025-12-02*
*状态: 已完成主要修复*

---

## 9. 已完成修复

### 修复 1: 配置文件挂载 (Phase 1)
在 `docker-compose.yml` 中添加了 agents.yaml 和 workflows.yaml 的挂载：
```yaml
volumes:
  - ../backend/services/report_orchestrator/config/agents.yaml:/app/config/agents.yaml:ro
  - ../backend/services/report_orchestrator/config/workflows.yaml:/app/config/workflows.yaml:ro
```

### 修复 2: 工具调用格式 (Phase 2)
在 `trading_meeting.py` 中修改 `_run_agent_turn()` 方法，使用 `agent._get_system_prompt()` 代替 `agent.system_prompt`，确保工具调用指令被包含在系统提示中。

### 修复 3: LLM 提供商配置 (额外)
更新 `.env` 文件中 `DEFAULT_LLM_PROVIDER=deepseek`，确保使用有效的 API 密钥。

### 验证结果
- 配置文件正确挂载到容器 `/app/config/` 目录
- LLM Gateway 正确使用 deepseek 提供商
- 工具已正确注册到 Leader Agent (tavily_search, open_long, open_short, close_position, hold)
