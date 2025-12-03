# MCP统一重构 - 进度报告

## 📅 日期
2025-12-03

## 🎯 总体目标
将所有工具调用统一使用 MCP (Model Context Protocol) 架构,替代之前的硬解析和直接HTTP调用方式。

---

## ✅ 已完成工作

### 阶段1: Web Search Service MCP接口 (✅ 完成)

**文件变更**:
1. `backend/services/web_search_service/app/main.py`
   - 添加 `POST /mcp/tools/{tool_name}` 端点
   - 添加 `GET /mcp/tools` 列表端点
   - 添加 `GET /health` 健康检查
   - 支持 `search` 和 `news_search` 工具

2. `backend/services/report_orchestrator/app/core/roundtable/mcp_client.py`
   - 修复 `HTTPMCPConnection.call_tool()` 路径逻辑
   - 实现三层路径 fallback: `/mcp/tools/{tool_name}` → `/tools/{tool_name}` → `/{tool_name}`

3. `backend/services/report_orchestrator/app/core/roundtable/mcp_tools.py`
   - 重构 `TavilySearchTool` 使用 MCP Client
   - 添加全局 `get_mcp_client()` 辅助函数
   - 移除直接 HTTP 调用,改用 `mcp_client.call_tool()`

**测试验证**: ✅ 通过
- 创建测试脚本 `/tmp/test_tavily_mcp.py`
- 验证 MCP Client 配置加载
- 验证工具调用返回正确格式

**架构变化**:
```
之前: TavilySearchTool → httpx.post(web_search_service/search)
现在: TavilySearchTool → MCPClient.call_tool("web-search", "search")
                       → HTTPMCPConnection.call_tool()
                         → POST http://web_search_service:8010/mcp/tools/search
```

---

### 阶段2: Trading Tools MCP重构 (✅ 部分完成)

**文件变更**:
1. `backend/services/report_orchestrator/app/core/trading/trading_tools.py`
   - 重构 `_tavily_search()` 方法使用 MCP Client
   - 移除直接 Tavily API 调用
   - 改用 `get_mcp_client()` 调用 `web-search` 服务

**状态**: Trading Tools 中的 Tavily 搜索已迁移到 MCP

---

## 🔄 进行中的工作

### PublicDataTool 和 KnowledgeBaseTool 重构

**当前状态**:
- `PublicDataTool`: 直接调用 `http://external_data_service:8006` (服务不存在)
- `KnowledgeBaseTool`: 直接调用 `http://internal_knowledge_service:8009` (服务已配置但未集成)

**问题分析**:
1. `external_data_service` 未在 docker-compose 中定义,也没有对应的 MCP 配置
2. `knowledge-base` 服务已在 MCP 配置中定义 (`http://internal_knowledge_service:8009`),但工具未使用 MCP

**下一步行动**:
1. ✅ 确认 `PublicDataTool` 是否需要保留 (可能映射到 `financial-data` MCP 服务)
2. ⏳ 重构 `KnowledgeBaseTool` 使用 MCP Client 调用 `knowledge-base` 服务
3. ⏳ 验证 `knowledge-base` 服务是否实现了 MCP 接口

---

## 📋 待办事项

### 高优先级
1. [ ] 决定 `PublicDataTool` 的处理方式:
   - 选项A: 映射到 `financial-data` MCP 服务的具体工具
   - 选项B: 暂时禁用,等待 external_data_service 实现

2. [ ] 重构 `KnowledgeBaseTool` 使用 MCP:
   ```python
   # 当前
   async with httpx.AsyncClient() as client:
       response = await client.post(f"{self.knowledge_service_url}/search", ...)

   # 目标
   result = await mcp_client.call_tool(
       server_name="knowledge-base",
       tool_name="search_documents",
       query=query,
       top_k=top_k
   )
   ```

3. [ ] 检查 `internal_knowledge_service` 是否已实现 MCP 接口
   - 如果未实现,需要添加 MCP 端点 (参考 web_search_service)

### 中优先级
4. [ ] 验证所有场景的端到端测试
   - Early Stage Analysis
   - Growth Stage Analysis
   - Public Market Analysis
   - Alternative Investment
   - Industry Research
   - **Trading Scenario** (重点测试)

5. [ ] 检查其他可能使用直接 HTTP 调用的工具
   ```bash
   grep -r "httpx.AsyncClient" backend/services/report_orchestrator/app/core/
   grep -r "requests.post" backend/services/report_orchestrator/app/core/
   ```

### 低优先级
6. [ ] 添加 MCP 调用监控和日志
   - 使用 `MCPClient.get_statistics()` 收集调用数据
   - 记录失败率、延迟等指标

7. [ ] 更新文档
   - 更新 `SYSTEM_ARCHITECTURE.md` 反映 MCP 架构
   - 添加 MCP 工具开发指南

---

## 📊 统计数据

### 工具迁移状态

| 工具名称 | 位置 | MCP状态 | 备注 |
|---------|------|---------|------|
| TavilySearchTool (roundtable) | `mcp_tools.py` | ✅ 已迁移 | 使用 `web-search` MCP 服务 |
| tavily_search (trading) | `trading_tools.py` | ✅ 已迁移 | 使用 `web-search` MCP 服务 |
| PublicDataTool | `mcp_tools.py` | ❌ 直接HTTP | 服务不存在,需决策 |
| KnowledgeBaseTool | `mcp_tools.py` | ❌ 直接HTTP | 需迁移到 `knowledge-base` MCP |
| get_market_price | `trading_tools.py` | ⚠️ 直接API | Binance API,无需MCP |
| get_klines | `trading_tools.py` | ⚠️ 直接API | Binance API,无需MCP |
| calculate_indicators | `trading_tools.py` | ⚠️ 直接API | Binance API,无需MCP |
| get_fear_greed_index | `trading_tools.py` | ⚠️ 直接API | alternative.me API,无需MCP |
| get_funding_rate | `trading_tools.py` | ⚠️ 直接API | Binance API,无需MCP |
| open_long/short/close_position | `trading_tools.py` | 🔵 本地调用 | PaperTrader,无需MCP |
| hold | `trading_tools.py` | 🔵 本地调用 | 纯逻辑,无需MCP |

**说明**:
- ✅ 已迁移: 已使用 MCP Client
- ❌ 直接HTTP: 直接调用内部服务,应使用 MCP
- ⚠️ 直接API: 直接调用外部 API (Binance, alternative.me 等),**无需迁移到MCP**
- 🔵 本地调用: 本地函数/类方法,无需 MCP

---

## 🎓 经验教训

### MCP 重构原则

1. **区分内部服务和外部 API**
   - ✅ 内部服务 (web_search_service, knowledge_service 等) → 使用 MCP
   - ❌ 外部 API (Binance, CoinGecko, alternative.me) → 直接调用,无需 MCP
   - 🔵 本地计算 (Paper Trading, 指标计算) → 直接调用,无需 MCP

2. **MCP 的核心价值**
   - 统一内部服务接口
   - 统一认证和错误处理
   - 统一监控和日志
   - 服务发现和负载均衡

3. **不要过度使用 MCP**
   - 外部 API 已有自己的SDK和错误处理
   - 本地函数调用无需额外抽象
   - MCP 应该简化架构,而不是增加复杂度

---

## 🐛 已修复的问题

### 问题1: Pydantic验证错误
**错误**: `published_date: Input should be a valid string [type=string_type, input_value=None]`
**原因**: `SearchResult.published_date` 类型为 `str` 但接收到 `None`
**修复**: 改为 `Optional[str] = Field(default=None)`

### 问题2: MCP配置路径错误
**错误**: `Unknown MCP server: web-search`
**原因**: 相对路径 `../../config/mcp_config.yaml` 不正确
**修复**: 使用 `../../../config/mcp_config.yaml` (从 `app/core/roundtable/` 到 `/usr/src/app/`)

### 问题3: None参数验证失败
**错误**: `time_range: Input should be a valid string [type=string_type, input_value=None]`
**原因**: Pydantic不接受None作为可选字符串参数
**修复**: 只传递非None参数到 `SearchRequest`

---

## 📌 关键设计决策

### 决策1: Trading Tools 不全部迁移到 MCP

**背景**: Trading Tools 大量使用 Binance/OKX API 获取实时行情数据

**决策**:
- ✅ 迁移 `tavily_search` (内部 web_search_service)
- ❌ **不迁移** `get_market_price`, `get_klines` 等 (外部 Binance API)
- ❌ **不迁移** `open_long`, `close_position` 等 (本地 PaperTrader)

**理由**:
1. Binance API 已经是成熟的外部服务,有完善的错误处理
2. 添加 MCP 层会增加延迟,影响交易时效性
3. MCP 适合统一内部服务,不适合包装外部 API

### 决策2: 使用全局 MCP Client 实例

**设计**: 使用 `get_mcp_client()` 返回单例 MCP Client

**优点**:
- 避免重复加载配置
- 连接池复用
- 统一调用历史记录

**缺点**:
- 需要手动管理生命周期
- 测试时需要 `reset_mcp_client()`

---

## 🚀 下一步计划

### 立即行动 (今天)
1. 决定 `PublicDataTool` 处理方式
2. 检查 `internal_knowledge_service` MCP 接口实现
3. 重构 `KnowledgeBaseTool` (如果服务支持)

### 短期 (本周)
4. 运行完整的 5 个场景回归测试
5. 修复发现的问题
6. 完成 Phase 2 报告

### 长期 (下周)
7. 添加 MCP 监控和指标
8. 优化 MCP 调用性能
9. 编写 MCP 工具开发文档

---

## 🔗 相关文档

- [MCP_REFACTORING_PHASE1_COMPLETE.md](./MCP_REFACTORING_PHASE1_COMPLETE.md) - Phase 1 完成报告
- [MCP_UNIFIED_REFACTORING_PLAN.md](./MCP_UNIFIED_REFACTORING_PLAN.md) - 初始重构计划
- [TOOL_CALLING_IMPLEMENTATION_COMPLETE.md](./TOOL_CALLING_IMPLEMENTATION_COMPLETE.md) - LLM Tool Calling 实现
- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) - 系统架构文档

---

**最后更新**: 2025-12-03
**负责人**: Claude Code
**状态**: ✅ Phase 1 完成, 🔄 Phase 2 进行中
