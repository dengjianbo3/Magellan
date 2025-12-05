# Tool Calling 架构重构报告

## 概述

本次重构消除了硬编码的正则表达式工具检测，改用 Agent 类原生的 Tool Calling 机制。

## 主要变更

### 1. TradeExecutorWrapper (trading_meeting.py)

**重构前:**
- 使用硬编码正则 `[USE_TOOL: xxx]` 检测工具调用
- 不支持 OpenAI 原生 tool_calls 格式

**重构后:**
- 调用 `Agent._call_llm()` 发送 LLM 请求
- **支持原生 tool_calls** (OpenAI 格式)
- **支持 Legacy [USE_TOOL: xxx] 格式** (兼容)
- **备用文本推断逻辑** (从自然语言推断决策)

```python
# 新架构流程
1. Agent._call_llm() 发送请求 + 工具 schema
2. 检测原生 tool_calls → 执行工具
3. 检测 Legacy [USE_TOOL: xxx] → 执行工具
4. 备用: 从响应文本推断决策 → 执行工具
5. 返回 TradingSignal
```

### 2. _run_agent_turn (trading_meeting.py)

**新增:** 原生 tool_calls 支持

分析 agent (TechnicalAnalyst, MacroEconomist 等) 现在支持:
- 原生 tool_calls (OpenAI 格式)
- Legacy [USE_TOOL: xxx] 格式

### 3. _on_analysis_cycle (trading_routes.py)

**修复:** 防止重复执行交易

- 检查持仓是否已存在
- 如果 TradeExecutor 已执行，跳过 `_execute_signal`
- 作为备用方案保留 `_execute_signal`

## 工具调用流程

```
用户请求
    ↓
TradingScheduler.on_analysis_cycle()
    ↓
TradingMeeting.run()
    ├── Phase 1-3: 分析 Agent 使用 _run_agent_turn
    │   └── 支持原生 tool_calls + Legacy 格式
    │
    ├── Phase 4: Leader 总结 (无交易执行)
    │
    └── Phase 5: TradeExecutorWrapper.run()
        ├── Agent._call_llm() 发送请求
        ├── 检测原生 tool_calls → 执行工具
        ├── 检测 Legacy 格式 → 执行工具
        └── 备用: 文本推断 → 执行工具
            ↓
        工具函数执行交易
        (open_long_tool, open_short_tool, etc.)
            ↓
        paper_trader.open_position()
            ↓
        返回 TradingSignal
```

## 防重复执行机制

1. **paper_trader._open_position()**: 使用 `asyncio.Lock` 防止并发
2. **持仓检查**: 如果已有持仓且方向相同，跳过开仓
3. **_on_analysis_cycle**: 检查持仓是否匹配，避免重复调用 `_execute_signal`

## 测试建议

1. **原生 tool_calls 测试**: 使用支持 function calling 的 LLM 模型
2. **Legacy 格式测试**: 使用输出 `[USE_TOOL: xxx]` 格式的模型
3. **文本推断测试**: 使用不输出工具调用格式的模型

## 文件变更

- `backend/services/report_orchestrator/app/core/trading/trading_meeting.py`
  - 重写 `_create_trade_executor_agent_instance()`
  - 新增 `TradeExecutorWrapper` 类
  - 修改 `_run_agent_turn()` 支持原生 tool_calls

- `backend/services/report_orchestrator/app/api/trading_routes.py`
  - 修改 `_on_analysis_cycle()` 防止重复执行
