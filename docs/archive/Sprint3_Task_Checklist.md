# Sprint 3 开发任务清单

**基于**: `docs/Sprint3_Technical_Design.md`  
**目标**: 实现 DD 工作流与核心分析模块  
**预计时间**: 9-12 天

---

## ✅ Phase 1: 基础重构（2-3天）**已完成**

### Task 1.1: 创建新的数据模型 ✅
- [x] 在 `backend/services/report_orchestrator/app/models/` 创建 `dd_models.py`
  - [x] `DDAnalysisRequest`
  - [x] `BPStructuredData` 及相关子模型（`TeamMember`, `FinancialProjection` 等）
  - [x] `TeamAnalysisOutput`
  - [x] `MarketAnalysisOutput`
  - [x] `DDQuestion`
  - [x] `PreliminaryIM`
  - [x] `DDStep`
  - [x] `DDWorkflowMessage`

### Task 1.2: 实现状态机 ✅
- [x] 创建 `backend/services/report_orchestrator/app/core/dd_state_machine.py`
  - [x] 定义 `DDWorkflowState` 枚举
  - [x] 实现 `DDStateMachine` 类
  - [x] 实现状态转换逻辑
  - [x] 添加错误处理和恢复机制

### Task 1.3: 创建新的 API 端点 ✅
- [x] 在 `main.py` 中添加 WebSocket 端点 `/ws/start_dd_analysis`
- [x] 添加 HTTP 端点 `/start_dd_analysis_http` (用于测试)
- [x] 添加会话查询端点 `/dd_session/{session_id}`

### Task 1.4: 编写单元测试 ✅
- [x] 创建 `tests/test_dd_models.py` - 测试数据模型的验证逻辑

### Task 1.5: 创建占位符 Agents (提前完成) ✅
- [x] 创建 `bp_parser.py` - BP 解析器
- [x] 创建 `team_analysis_agent.py` - 团队分析占位符
- [x] 创建 `market_analysis_agent.py` - 市场分析占位符
- [x] 创建 `risk_agent.py` - 风险分析占位符

**Phase 1 状态**: ✅ **已完成** (2025-10-22)  
**详细报告**: `docs/Sprint3_Phase1_Completion_Report.md`

---

## ✅ Phase 2: Agent 实现（3-4天）**已完成**

### Task 2.1: 实现 TeamAnalysisAgent ✅
- [x] 创建 `backend/services/report_orchestrator/app/agents/team_analysis_agent.py`
- [x] 实现 `analyze()` 方法
  - [x] 设计综合分析 Prompt
  - [x] 调用 LLM Gateway
  - [x] 解析和验证输出
- [x] 实现辅助方法
  - [x] `_build_context()` - 构建分析上下文
  - [x] `_format_search_results()` - 格式化搜索结果
  - [x] `_search_team_background()` - 搜索团队背景
  - [x] `_create_fallback_analysis()` - 降级方案
- [x] 集成 Web Search Service
- [x] 集成 LLM Gateway

### Task 2.2: 实现 MarketAnalysisAgent ✅
- [x] 创建 `backend/services/report_orchestrator/app/agents/market_analysis_agent.py`
- [x] 实现 `analyze()` 方法
  - [x] 设计市场验证 Prompt
  - [x] 整合多源市场数据
  - [x] 识别市场红旗
- [x] 实现辅助方法
  - [x] `_search_market_data()` - 搜索市场数据
  - [x] `_search_competitors()` - 搜索竞品
  - [x] `_query_internal_knowledge()` - 查询内部知识库
  - [x] `_create_fallback_analysis()` - 降级方案
- [x] 集成 Web Search Service
- [x] 集成 Internal Knowledge Service
- [x] 集成 LLM Gateway

### Task 2.3: 升级 RiskAgent ✅
- [x] 完善 `backend/services/report_orchestrator/app/agents/risk_agent.py`
- [x] 实现 `generate_dd_questions()` 方法
  - [x] 设计 DD 问题生成 Prompt
  - [x] 分类问题（Team/Market/Product/Financial/Risk）
  - [x] 关联 BP 引用和优先级
- [x] 实现 `_identify_weak_points()` - 识别 BP 薄弱环节
- [x] 实现 `_create_fallback_questions()` - 降级方案
- [x] 集成 LLM Gateway

### Task 2.4: 优化 BP 解析器 ✅
- [x] 优化 `backend/services/report_orchestrator/app/parsers/bp_parser.py`
- [x] 优化 `parse_bp()` 方法
  - [x] 调用 LLM Gateway 的文件理解 API
  - [x] 优化结构化提取 Prompt
  - [x] 数据类型转换（数字→字符串）
  - [x] 解析并验证返回的 JSON
- [x] 处理解析失败的降级方案
- [x] 通过端到端测试验证

**Phase 2 状态**: ✅ **已完成** (2025-10-22)  
**详细报告**: `docs/Sprint3_Phase2_Completion_Report.md`

---

## ✅ Phase 3: 服务集成（2-3天）

### Task 3.1: 集成 LLM Gateway
- [ ] 在状态机的 `DOC_PARSE` 状态中调用 BP 解析器
- [ ] 处理文件上传和传递
- [ ] 实现解析进度反馈
- [ ] 错误处理和重试逻辑

### Task 3.2: 集成 External Data Service
- [ ] 在 `TDD` 状态中调用 External Data Service
  - [ ] 根据团队成员姓名查询工商/LinkedIn 数据
  - [ ] 处理未找到数据的情况
- [ ] 实现缓存机制（避免重复查询）

### Task 3.3: 集成 Web Search Service
- [ ] 在 `TDD` 状态中进行团队背景搜索
  - [ ] 构建搜索查询（如 "张三 阿里巴巴 P9 背景"）
  - [ ] 过滤不相关结果
- [ ] 在 `MDD` 状态中进行市场验证搜索
  - [ ] 搜索市场规模数据
  - [ ] 搜索竞品信息

### Task 3.4: 集成 Internal Knowledge Service
- [ ] 在 `MDD` 状态中查询内部历史项目
  - [ ] 构建相似项目查询
  - [ ] 提取相关洞察
- [ ] 处理知识库为空的情况

### Task 3.5: 实现交叉验证逻辑
- [ ] 在 `CROSS_CHECK` 状态中实现验证
  - [ ] 对比 BP 数据与外部数据
  - [ ] 识别不一致之处
  - [ ] 生成警告信息
- [ ] 编写验证规则
  - [ ] 团队背景验证
  - [ ] 市场规模验证
  - [ ] 竞品信息验证

---

## ✅ Phase 4: 测试与调优（2天）

### Task 4.1: 准备测试数据
- [ ] 创建测试用的 BP PDF 文件
  - [ ] 包含完整的团队、市场、产品信息
  - [ ] 故意设置一些"陷阱"（如夸大市场规模）
- [ ] 准备 mock 外部 API 响应

### Task 4.2: 编写集成测试
- [ ] 创建 `tests/test_dd_workflow_integration.py`
- [ ] 实现里程碑测试
  ```python
  async def test_complete_dd_workflow():
      # 上传 BP，触发完整 DD 流程
      # 验证生成的团队分析和市场分析
      # 验证 DD 问题清单的数量和质量
  ```
- [ ] 测试 WebSocket 通信
- [ ] 测试 HITL 节点的暂停和恢复

### Task 4.3: 性能优化
- [ ] 实现 TDD 和 MDD 的并行执行
  ```python
  team_task = asyncio.create_task(execute_tdd())
  market_task = asyncio.create_task(execute_mdd())
  await asyncio.gather(team_task, market_task)
  ```
- [ ] 优化 LLM 调用（减少 token 使用）
- [ ] 添加缓存机制
- [ ] 测量各步骤耗时，优化瓶颈

### Task 4.4: 错误处理和鲁棒性
- [ ] 测试网络错误场景
- [ ] 测试 LLM 返回格式错误
- [ ] 测试外部服务不可用
- [ ] 实现优雅降级

### Task 4.5: 文档更新
- [ ] 更新 API 文档（OpenAPI/Swagger）
- [ ] 更新部署文档（如需要新的环境变量）
- [ ] 编写开发者指南
- [ ] 更新 Sprint 3 完成报告

---

## 📋 验收标准（Acceptance Criteria）

### 功能性
- [ ] ✅ 可以上传 BP PDF，系统能解析出结构化数据
- [ ] ✅ 生成的团队分析包含：摘要、优势、担忧、评分、数据来源
- [ ] ✅ 生成的市场分析包含：市场验证、竞争格局、红旗
- [ ] ✅ DD 问题清单包含至少 10 个问题，涵盖 5 大类
- [ ] ✅ WebSocket 实时推送工作流进度
- [ ] ✅ 整个 DD 流程可在 3-5 分钟内完成

### 质量
- [ ] ✅ 所有单元测试通过（覆盖率 > 80%）
- [ ] ✅ 集成测试通过（里程碑测试）
- [ ] ✅ 代码通过 lint 检查（无警告）
- [ ] ✅ 所有 API 有完整的类型注解和文档字符串

### 性能
- [ ] ✅ BP 解析时间 < 30 秒
- [ ] ✅ 单个 Agent 分析时间 < 60 秒
- [ ] ✅ 完整流程总时间 < 5 分钟
- [ ] ✅ 支持至少 3 个并发 DD 会话

---

## 🔧 开发环境配置

### 依赖项
确保以下服务正常运行：
```bash
docker compose ps
# 应该看到：
# - llm_gateway
# - external_data_service
# - web_search_service  
# - internal_knowledge_service
# - chroma
```

### 环境变量
在 `.env` 中确保有：
```bash
GOOGLE_API_KEY=your_key
TAVILY_API_KEY=your_key
GEMINI_MODEL_NAME=gemini-1.0-pro
```

### 本地测试
```bash
# 安装测试依赖
pip install -r requirements.txt

# 运行单元测试
pytest backend/services/report_orchestrator/tests/ -v

# 运行集成测试
pytest tests/test_dd_workflow_integration.py -v -s
```

---

## 📅 时间规划

| Phase | 任务 | 预计时间 | 负责人 | 状态 |
|-------|------|---------|--------|------|
| Phase 1 | 基础重构 | 2-3天 | - | ⏳ 待开始 |
| Phase 2 | Agent 实现 | 3-4天 | - | ⏳ 待开始 |
| Phase 3 | 服务集成 | 2-3天 | - | ⏳ 待开始 |
| Phase 4 | 测试与调优 | 2天 | - | ⏳ 待开始 |

**总计**: 9-12 天

---

## 📝 开发日志

### Day 1 - [日期]
- [ ] 完成 Task 1.1
- [ ] 完成 Task 1.2
- [ ] 备注：

### Day 2 - [日期]
- [ ] 完成 Task 1.3
- [ ] 完成 Task 1.4
- [ ] 备注：

（... 继续记录每日进度 ...）

---

## 🚨 风险跟踪

| 风险 | 状态 | 缓解措施 | 更新时间 |
|------|------|---------|----------|
| LLM 解析 BP 准确率低 | 🟡 监控中 | 使用结构化 Prompt | - |
| 外部 API 限流 | 🟢 低风险 | 实现缓存 | - |

---

## 📞 联系与协作

**技术问题**: 查阅 `docs/Sprint3_Technical_Design.md`  
**进度同步**: 每日更新本清单  
**代码审查**: 每个 Phase 完成后进行

---

**最后更新**: 2025-10-22
