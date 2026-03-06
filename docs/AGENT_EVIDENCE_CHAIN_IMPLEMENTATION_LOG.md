# Agent Evidence Chain Implementation Log

## Scope
- 目标：将证据展示从“全局抽取面板”改为“每条专家消息下方的原始调用证据链”。
- 覆盖模块：Expert Chat、Roundtable。

## Step Log

### Step 1: Backend evidence plumbing (expert chat)
- 文件：
  - `backend/services/report_orchestrator/app/main.py`
- 改动：
  - 新增证据清洗函数：
    - `_sanitize_evidence_chain`
    - `_sanitize_evidence_packet`
  - `_run_expert_chat_agent_once` 改为返回：
    - `content`
    - `evidence_chain`
  - `_ask_specialist` 返回中增加：
    - `evidence_chain`
    - `evidence_packet`（清洗后）
  - `_leader_direct_reply` / `_leader_summarize_with_specialists` 改为返回结构化结果（含 `evidence_chain`）。
  - `agent_message` websocket payload 增加：
    - `evidence_chain`
    - `evidence_packet`
  - assistant 历史消息保留：
    - `evidence_chain`
    - `evidence_packet`
    - `mode`
  - 断线恢复重放 `_replay_missing_assistant_messages` 增加证据字段。
- 结果：
  - Expert Chat 每条回复具备证据链透传能力。

### Step 2: Backend evidence plumbing (roundtable)
- 文件：
  - `backend/services/report_orchestrator/app/core/roundtable/meeting.py`
- 改动：
  - `Meeting._on_message` 发布 `AgentEvent` 时增加：
    - `data.metadata`
    - `data.evidence_chain`
    - `data.evidence_summary`
- 结果：
  - Roundtable 的 `agent_event.result` 可直接携带原始证据链。

### Step 3: Frontend per-message evidence UI
- 新文件：
  - `frontend/src/components/common/InlineEvidenceChain.vue`
- 改动：
  - 新增内联可折叠证据链组件，展示：
    - step/tool/status/duration
    - params
    - output_preview
    - numeric_outputs
    - sources
    - error
- 结果：
  - 两个页面统一复用同一证据展示组件。

### Step 3.1: Readability hardening for non-technical users
- 文件：
  - `frontend/src/components/common/InlineEvidenceChain.vue`
- 改动：
  - 取消主视图中的原始 JSON 展示。
  - 主视图改为“可读摘要 + 关键指标 + 来源链接”。
  - 增加“本次任务”字段（每条 agent 回复显示收到的任务摘要）。
- 结果：
  - 证据链从“工程日志视图”切换为“业务证据视图”。

### Step 4: Replace global evidence panel in Expert Chat
- 文件：
  - `frontend/src/views/ChatHubView.vue`
- 改动：
  - 删除全局证据面板按钮/抽屉/右侧栏逻辑。
  - assistant 消息改为内联渲染 `InlineEvidenceChain`。
  - `agent_message` 处理增加 `evidence_chain/evidence_packet` 存储。
  - 本地会话序列化与 resume history 增加证据字段。
- 结果：
  - 证据与单条消息绑定，且会话恢复后仍可查看。
  - 每条消息可显示 `task_brief`（本次任务）。

### Step 5: Replace global evidence panel in Roundtable
- 文件：
  - `frontend/src/views/RoundtableView.vue`
- 改动：
  - 删除全局证据面板入口和显示层。
  - `agent_event.result` -> 消息对象时注入 `evidence_chain/evidence_packet`。
  - agent 消息下方渲染 `InlineEvidenceChain`。
- 结果：
  - Roundtable 中每位专家消息均可独立展开证据链。
  - ReWOO Agent 的 `task_brief` 已透传并展示。

### Step 6: Remove obsolete extraction-panel artifacts
- 删除文件：
  - `frontend/src/components/common/EvidenceLedgerPanel.vue`
  - `frontend/src/composables/useEvidenceLedger.js`
- 结果：
  - 避免“抽取式证据”路径继续被误用。

## Issues Found During Refactor
- 历史逻辑默认把证据放在全局面板，导致消息对象里没有稳定证据字段。
  - 处理：补齐消息级 `evidence_chain/evidence_packet` 持久化与重放。
- Leader 直答/总结原先返回纯字符串，证据透传会丢失。
  - 处理：改为结构化返回并更新所有调用方。

## Validation Checklist
- [x] Python 语法检查：
  - `backend/services/report_orchestrator/app/main.py`
  - `backend/services/report_orchestrator/app/core/roundtable/meeting.py`
- [x] 前端构建：
  - `frontend` 执行 `npm run build`
- [ ] 运行时验证（待你在交互路径上确认）：
  - Expert Chat 发起触发工具调用的问题，检查单条回复下证据折叠块。
  - Roundtable 发起讨论，检查每个专家消息下证据折叠块。
  - 断线重连/恢复会话后，证据块仍可展开。
