# 原子专家统一化改造路线图（P0/P1）

## 1. 核心目标

建立并长期维护一条统一原则：

- 所有业务场景（分析、头脑风暴、专家群聊、自动交易）都由同一套原子 Agent 组成。
- 差异只来自组织方式（编排流程），不来自“临时专家”或“场景专用专家”。
- 后续迭代重点只有两件事：  
  1) 提升原子 Agent 能力；  
  2) 优化组织方式（编排效率、协作质量、交互体验）。

---

## 2. 当前主要不一致点

### 2.1 注册中心分叉

- `app/core/agent_registry.py`（workflow/roundtable/trading在用）
- `app/core/agents/registry.py`（messaging agent service在用）

影响：

- 同名 Agent 在不同链路能力可能不一致。
- 新增 Agent 或改能力时容易漏改。

### 2.2 专家清单存在硬编码分散

- 头脑风暴的 `AGENT_FACTORIES` 手工维护。
- 专家群聊的 `EXPERT_CHAT_AGENT_PROFILES` 与 `EXPERT_CHAT_AGENT_REGISTRY_IDS` 手工维护。
- 自动交易单独维护 `analysis_agent_ids`。

影响：

- `agents.yaml` 与实际可调用专家不一致。
- 前端可 @ 专家集合与后端真实能力脱节。

### 2.3 上下文传递断裂（分析链路）

- workflow 虽有 `depends_on`，但实际 `_execute_agent_step()` 对每一步都主要传 `request.target`，前序结果没有系统化传入后续 Agent。

影响：

- 重复搜索严重。
- 后续专家无法复用前序证据，协作弱化为“并列单聊”。

### 2.4 失败降级策略与理念冲突

- ReWOO 计划失败会 fallback 到无工具直接回答。

影响：

- 产出看似可读，但不是“专家能力”结果，容易误导。

### 2.5 工具装配规则未统一配置化

- 大量工具绑定散落在代码 `if/elif` 中，而不是单一配置源。

影响：

- 原子 Agent 能力随场景漂移。
- 调整成本高，回归风险高。

---

## 3. 目标架构（统一模型）

### 3.1 四层结构

- 原子能力层：`agents.yaml` + 原子工厂 + 工具能力配置（单一来源）
- 编排层：workflow/meeting/chat/trading 仅定义“谁先说、何时说、如何汇总”
- 会话证据层：统一 Evidence Bus（检索结果、关键数据、结论片段）
- 展示层：前端只消费事件与消息，不绑定具体实现细节

### 3.2 架构红线

- 禁止新增“场景专用专家 Agent”。
- 新需求优先通过：
  1) 增强原子 Agent；
  2) 调整编排模板；
  3) 扩展工具能力。

### 3.3 统一记忆层（qmd）

目标：

- 所有原子 Agent 共用同一记忆底座，但按账号隔离、按专家分区。
- 不把 memory 做成场景功能（不是“头脑风暴记忆”或“交易记忆”），而是原子专家的长期能力。

记忆分层与命名（collection）：

- `u:{user_id}:a:{agent_id}:episodic`：短中期对话/任务片段。
- `u:{user_id}:a:{agent_id}:lessons`：沉淀后的稳定经验、反思规则。
- `u:{user_id}:shared:evidence`：同账号下可复用证据池（跨专家共享）。

读写路径：

- 读：`user_id + agent_id + intent + 当前上下文` -> qmd `query(top_k)`。
- 写：每次专家完成后写入 `question/answer/evidence_ids/confidence/outcome_feedback`。
- 压缩：定期将 episodic 归纳为 lessons，减少冗余和 token 负担。

边界与失败语义：

- 严格禁止跨账号读取。
- 不允许 A 专家覆盖 B 专家的 lessons（shared:evidence 除外）。
- qmd 不可用时进入 degraded 模式并显式提示，不伪造“记忆已命中”。

---

## 4. 分阶段执行计划

## Phase A（P0）统一内核一致性

### A1. 收敛成唯一 Agent Registry

目标：

- 所有链路统一走 `app/core/agent_registry.py`（配置驱动、class_path 动态创建）。

动作：

- 迁移 `messaging/services/agent_service.py` 依赖到统一 registry。
- 停用 `app/core/agents/registry.py` 的创建职责（保留兼容壳或删除）。

涉及文件：

- `backend/services/report_orchestrator/app/messaging/services/agent_service.py`
- `backend/services/report_orchestrator/app/core/agents/registry.py`
- `backend/services/report_orchestrator/app/core/agent_registry.py`

验收：

- 分析/头脑风暴/专家群聊/自动交易创建同一 agent_id 时，工厂来源一致。

---

### A2. 统一“专家清单来源”机制

目标：

- 所有可选专家与 @ 列表从 `agents.yaml` 自动生成，不再手写多份字典。

动作：

- 新建统一函数：按 `scope` + `tags` + `enabled` 生成专家清单。
- 头脑风暴、专家群聊、自动交易都调用该函数构建候选专家。

涉及文件：

- `backend/services/report_orchestrator/app/main.py`
- `backend/services/report_orchestrator/app/core/trading/trading_agents.py`
- `backend/services/report_orchestrator/config/agents.yaml`

验收：

- 新增/下线一个原子 Agent 后，只改 `agents.yaml` 即可反映到三个场景。

---

### A3. 修复分析链路上下文传递

目标：

- workflow 后续步骤必须获得前序步骤证据，不再重复全量搜。

动作：

- `BaseOrchestrator._execute_agent_step()` 改为传递结构化 `context`：
  - `previous_step_results`
  - `evidence_refs`
  - `dependency_outputs`（按 `depends_on`）

涉及文件：

- `backend/services/report_orchestrator/app/core/orchestrators/base_orchestrator.py`
- `backend/services/report_orchestrator/app/messaging/services/agent_service.py`

验收：

- 在日志中可见后续 Agent 消费前序结果；重复搜索次数显著下降。

---

### A4. 失败语义收敛（禁止劣质回退）

目标：

- 专家失败就明确失败，不回退为“无工具猜测答案”。

动作：

- ReWOO 计划失败时返回结构化错误（含失败阶段、失败原因、建议补充数据）。
- 编排层聚合失败信息给 Leader，不输出伪结论。

涉及文件：

- `backend/services/report_orchestrator/app/core/roundtable/rewoo_agent.py`
- `backend/services/report_orchestrator/app/core/roundtable/meeting.py`
- `backend/services/report_orchestrator/app/main.py`（expert chat 聚合逻辑）

验收：

- 出错时前端显示“专家执行失败+可恢复建议”，不再出现低质量兜底回答。

---

### A5. 补齐原子专家覆盖一致性

目标：

- roundtable/expert-chat/trading 默认候选专家集合与 `agents.yaml` 对齐。

动作：

- roundtable 增加 onchain/contrarian 到可选集合。
- contrarian 注册与其他 ReWOO 专家同级的工具能力（至少 `web_search` + `knowledge`）。

涉及文件：

- `backend/services/report_orchestrator/app/main.py`
- `backend/services/report_orchestrator/app/core/roundtable/investment_agents.py`
- `backend/services/report_orchestrator/app/core/roundtable/mcp_tools.py`

验收：

- 前端 @ 列表、后端可实例化清单、配置清单三者一致。

---

### A6. 建立 qmd 记忆底座（P0 必做）

目标：

- 先打通统一 memory 抽象与 qmd adapter，让所有场景都能复用同一记忆接口。

动作：

- 新增记忆接口层：
  - `app/core/memory/interface.py`（MemoryStore 协议）
  - `app/core/memory/qmd_store.py`（qmd 适配）
  - `app/core/memory/noop_store.py`（降级实现）
- 在配置中加入 memory provider 与降级开关（qmd / redis / noop）。
- 注入基础读写 hook（先不做复杂压缩策略）：
  - 分析链路：`BaseOrchestrator._execute_agent_step()`
  - 头脑风暴：`ReWOOAgent.think_and_act()` / `analyze_with_rewoo()`
  - 专家群聊：`main.py` 的 `_ask_specialist` 与 leader 路由分支
  - 自动交易：复用 `core/trading/agent_memory.py` 的 user scope，逐步迁移到统一 MemoryStore

涉及文件：

- `backend/services/report_orchestrator/app/core/memory/interface.py`（新增）
- `backend/services/report_orchestrator/app/core/memory/qmd_store.py`（新增）
- `backend/services/report_orchestrator/app/core/orchestrators/base_orchestrator.py`
- `backend/services/report_orchestrator/app/core/roundtable/rewoo_agent.py`
- `backend/services/report_orchestrator/app/main.py`
- `backend/services/report_orchestrator/app/core/trading/agent_memory.py`

验收：

- 同一用户在不同场景触发同一专家时，能命中同一专家记忆。
- 关闭 qmd 时系统不崩溃，且前端可见“记忆降级”状态。

---

## Phase B（P1）组织效率与协作质量优化

### B1. qmd 共享证据总线（Evidence Bus）

目标：

- 同一会话搜过的证据可被后续 Agent 复用。

动作：

- 引入统一 Evidence Store（session_id 维度）。
- Evidence Store 后端使用 qmd `u:{user_id}:shared:evidence`。
- 工具层先查 Evidence，再查外部搜索；命中后回写 provenance。
- Agent 输出中引用 `evidence_id`，避免重复搬运长文本。

涉及文件：

- `backend/services/report_orchestrator/app/core/roundtable/search_router.py`
- `backend/services/report_orchestrator/app/core/roundtable/web_search_tool.py`
- `backend/services/report_orchestrator/app/core/orchestrators/base_orchestrator.py`

验收：

- 同会话重复查询命中率上升，token/时延下降。

---

### B2. workflow 并发执行（按依赖图）

目标：

- 对无依赖步骤并行执行，降低总耗时。

动作：

- 基于 `depends_on` 构建 DAG。
- 同层 step 并发执行，保持失败隔离。

涉及文件：

- `backend/services/report_orchestrator/app/core/orchestrators/base_orchestrator.py`
- `backend/services/report_orchestrator/config/workflows.yaml`

验收：

- 在同等任务下总时长显著下降，结果质量不退化。

---

### B3. 统一模型路由策略（角色级）

目标：

- 让“谁用 Pro、谁用 Flash”由统一策略控制，不在工厂里硬编码。

动作：

- 新增 `model_policy` 配置：
  - 路由/协调类（Leader、intent router）优先低时延模型；
  - 重分析类（技术/财务/宏观等）按用户配置使用 Pro/Flash。

涉及文件：

- `backend/services/report_orchestrator/app/core/roundtable/investment_agents.py`
- `backend/services/report_orchestrator/app/main.py`
- 配置文件（新增）

验收：

- 模型切换仅改配置，代码无需散改。

---

### B4. 编排模板化

目标：

- 把“组织方式”从代码逻辑升级为可配置模板。

动作：

- 头脑风暴模板：轮次、发言顺序、分歧处理策略。
- 专家群聊模板：leader 路由策略、委派策略、是否汇总回传。
- 自动交易模板：分析相位专家权重与风险阻断策略。

涉及文件：

- `backend/services/report_orchestrator/app/main.py`
- `backend/services/report_orchestrator/app/core/roundtable/meeting.py`
- `backend/services/report_orchestrator/app/core/trading/orchestration/*`

验收：

- 新组织方式通过配置发布，无需复制一套新业务代码。

---

### B5. 记忆治理与压缩（qmd 深化）

目标：

- 把记忆从“能用”升级为“长期可维护”，避免无限膨胀与噪音污染。

动作：

- 新增记忆写入策略：
  - 仅写高价值片段（结论、证据、失败原因、反思）。
  - 大段中间推理不直接入库，先摘要再写。
- 新增周期性压缩任务：
  - episodic -> lessons（按专家/主题聚合）
  - 低价值记忆 TTL 清理
- 新增质量护栏：
  - 每条记忆必须带 provenance（source/tool/session/timestamp）
  - 冲突记忆打标签，不做静默覆盖

涉及文件：

- `backend/services/report_orchestrator/app/core/memory/*`
- `backend/services/report_orchestrator/app/core/roundtable/search_router.py`
- `backend/services/report_orchestrator/app/core/trading/*`（记忆写入策略接入）

验收：

- 记忆命中率提升且 token 成本下降。
- 多轮会话中重复搜索比例下降，且不会出现跨用户污染。

---

## 5. 验收标准（统一架构完成定义）

- 同一 agent_id 在四个场景下能力边界一致（同 prompt 基础、同工具装配、同失败语义）。
- 新增原子 Agent 时，只需改配置和该 Agent 本体，不需改三个场景的硬编码列表。
- 同会话重复检索明显下降，后续 Agent 可引用前序证据。
- 同账号下同一专家具备跨场景连续记忆；跨账号严格隔离。
- qmd 异常时系统进入显式降级而非隐式失真。
- 失败时系统输出“显式失败 + 缺失信息”，不输出伪专业结论。

---

## 6. 推荐执行顺序（建议）

1. A1 注册中心收敛  
2. A2 专家清单统一  
3. A3 上下文传递修复  
4. A4 失败语义收敛  
5. A5 覆盖一致性补齐  
6. A6 qmd 记忆底座  
7. B1 qmd Evidence Bus  
8. B2 workflow 并发  
9. B3 模型路由策略  
10. B4 编排模板化  
11. B5 记忆治理与压缩

---

## 7. 变更风险与回滚

- 风险1：统一 registry 时出现构造参数不兼容。  
  回滚：保留旧 registry 兼容层，先双写日志对比，再切流。

- 风险2：上下文注入过大导致模型超时。  
  回滚：上下文改为 evidence 引用 + 摘要，限制消息体上限。

- 风险3：禁用 fallback 后失败率短期上升。  
  回滚：仅在内部环境开启“严格失败模式”，完善后全量启用。

- 风险4：qmd 接入初期查询噪音高，命中但无价值。  
  回滚：先只启用写入 + 人工抽样评估，分阶段打开检索注入。

- 风险5：qmd 服务不可用引发请求阻塞。  
  回滚：MemoryStore 增加超时与熔断，自动退回 noop/redis 模式。

---

## 8. 长期维护原则（你的核心理念落地版）

- 原子 Agent 是“员工”，编排模板是“组织结构”。
- 任何迭代都应回答两件事：  
  1) 是否增强了员工能力？  
  2) 是否优化了组织协作？  
- 若两者都没有，就不应该进入主干。

---

## 9. 实施状态（当前分支）

- ✅ A1 注册中心收敛：`app/core/agents/registry.py` 已改为兼容壳，统一委派到 `app/core/agent_registry.py`。  
- ✅ A2 专家清单统一：专家群聊与交易专家候选改为 registry + tags/scope 生成。  
- ✅ A3 上下文传递修复：workflow context 中传入 `dependency_outputs/previous_step_results/memory_context`。  
- ✅ A4 失败语义收敛：移除 keyword fallback 与 mock 伪结果，失败显式抛错并向前端透出。  
- ✅ A5 覆盖一致性补齐：onchain/contrarian 等原子专家统一进入候选与注册链路。  
- ✅ A6 统一记忆底座：MemoryStore 抽象 + gemini_vector/redis/qmd/noop provider 已接入。  
- ✅ B1 共享证据复用：SearchRouter 已先查 shared memory，再外部检索并回写证据。  
- ✅ B2 workflow 并发：BaseOrchestrator 按 `depends_on` DAG 分层并发执行。  
- ✅ B3 模型路由策略：新增 `model_policy.yaml` + role-based model routing。  
- ✅ B4 编排模板化：新增 `orchestration_templates.yaml`，expert-chat/roundtable 已消费。  
- ✅ B5 记忆治理与压缩：接入高价值写入过滤、provenance 元数据、TTL（redis/noop/vector 查询侧）。
