# 专家群聊中枢设计方案（Dashboard 替换）

## 1. 背景与目标
当前 `Dashboard` 页面信息密度较低、用户决策价值有限。目标是将首页改为一个“专家群聊中枢”，让用户进入系统后即可直接发起对话，获得主智能体（Leader）和专业智能体协作支持。

核心目标：
1. 首页即工作台：登录后直接进入可对话界面。
2. 默认主智能体：用户不指定对象时，由 Leader 负责响应与协作编排。
3. 精准直连专家：用户可通过 `@` 直接指定某个专业智能体，绕过 Leader。
4. 群聊协作可见：当 Leader 拉起其他智能体时，过程与结果在同一会话中可见。
5. 原生多模态：基于 Gemini 能力，文本/图片/PDF 等统一纳入对话上下文。

## 2. 设计原则
1. 用户心智简单：默认就聊，不需要先选模式。
2. 协作关系明确：谁在回答、谁被拉起、为什么拉起，都应可见。
3. 控制优先：`@` 直连始终优先于自动路由。
4. 可演进：先做可用，再逐步增强多智能体并发、记忆与工具治理。
5. 兼容现有：尽量复用 `Roundtable` 与 `Conversation` 现有后端能力，减少重写。

## 3. 用户交互模型

### 3.1 默认对话（无 @）
- 用户输入消息，不包含 `@agent`。
- 消息先路由给 Leader。
- Leader 可选择：
  - 直接回答用户。
  - 主动 `@` 一个或多个专业智能体协作，再汇总回复。

### 3.2 直连专家（有 @）
- 用户显式输入：`@市场分析师 ...` / `@market-analyst ...`。
- 消息直接路由到指定专家。
- Leader 不介入该轮（除非用户又显式 @Leader，或专家请求升级并得到用户确认）。

### 3.3 群聊可见性
- 所有参与者消息都在同一时间轴显示，保留发送者标识。
- 系统消息应明确展示：
  - “Leader 已邀请 @xxx 参与”
  - “@xxx 已完成分析”

### 3.4 多模态输入
- 用户可上传图片/PDF/文档并附带问题。
- 路由逻辑不变：
  - 无 @ -> Leader 先处理
  - 有 @ -> 直接专家处理
- 附件在消息模型中作为 `attachments[]` 统一传递。

## 4. 功能范围（MVP / V1 / V2）

### 4.1 MVP（建议先做）
1. Dashboard 替换为 ChatHub 页面。
2. 支持单会话实时聊天（WebSocket）。
3. 支持 `@agent` 路由。
4. 默认 Leader 回答。
5. Leader 可拉起 1 个专家协作。
6. 基础多模态（文本 + 图片 + PDF 引用）。

### 4.2 V1
1. Leader 多专家协作（串行/并行）。
2. 会话级知识库开关和范围选择（沿用你现有“是否启用 + 下拉范围”）。
3. 消息追踪（message_id、reply_to、delegation_trace）。
4. 会话持久化（可在报告中复用）。

### 4.3 V2
1. 专家并发调度与超时降级。
2. 用户级偏好记忆（常用专家、语言、风险偏好）。
3. 专家回答质量评分与路由优化。
4. 多会话管理与会话搜索。

## 5. 前端方案

## 5.1 路由与导航
- 将 `/`（`Dashboard`）替换为 `ChatHubView`。
- 侧边栏 `dashboard` 菜单替换为 `chat`（或保留 id 为 dashboard，label 改为“专家群聊”以减少改动）。
- `AuthenticatedLayout` 页标题映射更新为“专家群聊中枢 / Expert Chat Hub”。

## 5.2 ChatHub 页面结构
1. 左侧（可选）
   - 会话列表（当前可先隐藏，仅保留“当前会话”）。
2. 主区
   - 消息流（统一展示 Leader/专家/系统/用户消息）。
   - 输入区（多行输入 + 附件上传 + 发送）。
3. 右侧（可选）
   - 在线专家面板（可点击 @）。
   - 知识库开关与范围下拉。

## 5.3 输入与 @ 交互
- 输入框支持 mention 自动补全：`@` 后显示专家列表。
- 支持别名匹配：中文名、英文名、agent id。
- 解析优先级：
  1. 用户显式 @（最高优先）
  2. 默认 Leader

## 5.4 消息展示规范
- 每条消息最少字段：`sender`、`role`、`content`、`timestamp`。
- 额外字段：`route_mode`（leader/direct）、`delegation`（是否协作产生）。
- 系统提示统一为弱视觉样式，避免噪音。

## 6. 后端方案

## 6.1 入口接口
建议新增专用 WS 端点：
- `GET /ws/expert-chat`

也可复用现有：
- `/ws/conversation`（推荐逐步迁移，避免混杂 DD 历史逻辑）

## 6.2 核心组件
1. `ChatSessionManager`
   - 管理会话状态、上下文窗口、参与者。
2. `MentionRouter`
   - 解析用户消息中的 `@`。
   - 决定 direct/leader 路由。
3. `LeaderOrchestrator`
   - 无 @ 时接收用户消息。
   - 决定直接回答或委派专家。
4. `SpecialistAgentAdapter`
   - 复用现有 roundtable agent 工厂（`config/agents` + `investment_agents`）。
5. `ToolPolicy`
   - 控制 search/knowledge 工具调用权限与范围。

## 6.3 路由策略（关键）
- `mode = direct`：消息含有效 @expert。
  - 直接调用目标专家。
  - Leader 不参与该轮。
- `mode = leader`：无 @。
  - Leader 先处理。
  - 如需协作，Leader 触发委派任务给专家。
  - 结果可“专家先发言 + Leader总结”或“仅 Leader 汇总”。

## 6.4 消息协议（建议）

Client -> Server:
```json
{
  "type": "user_message",
  "session_id": "chat_xxx",
  "content": "@market-analyst 评估一下BTC短期波动",
  "attachments": [],
  "language": "zh",
  "knowledge": {
    "enabled": true,
    "category": "market"
  }
}
```

Server -> Client（示例事件）:
```json
{ "type": "session_started", "session_id": "chat_xxx" }
{ "type": "route_decided", "mode": "direct", "target": "market-analyst" }
{ "type": "agent_thinking", "agent": "market-analyst" }
{ "type": "agent_message", "agent": "market-analyst", "content": "..." }
{ "type": "delegation_started", "from": "Leader", "to": ["risk-assessor"] }
{ "type": "error", "message": "..." }
```

## 6.5 数据持久化（建议）
新增会话模型（可先放 Redis + SessionStore）：
- `chat_session`: id, user_id, created_at, updated_at, title, status
- `chat_message`: id, session_id, sender_type(user/leader/agent/system), sender_id, content, attachments, route_mode, metadata, created_at

后续可将会话沉淀为报告输入源或会议纪要输入源。

## 7. Leader 与专家的行为契约

### 7.1 Leader 契约
1. 无 @ 时必须响应。
2. 判断是否需要专家协作。
3. 委派时给出明确任务边界（问题、时间范围、输出格式）。
4. 汇总时标注来源与不确定性。

### 7.2 专家契约
1. 仅在被 @ 或被 Leader 委派时响应。
2. 聚焦领域边界，不重复 Leader 统筹内容。
3. 回复结构化（结论 + 依据 + 风险 + 下一步）。

## 8. 错误处理与降级
1. 专家超时：Leader 给出“部分结果 + 未完成项”。
2. 工具失败：降级为无外部检索回答，并显式声明。
3. WebSocket 中断：前端自动重连，恢复 session_id。
4. 单智能体故障：不影响其他专家与 Leader 主流程。

## 9. 权限与安全
1. WebSocket 必须携带并校验 token（沿用现有 `resolve_user_from_token`）。
2. 会话按 user_id 隔离。
3. 附件访问走受控 file_id，不透传本地路径。
4. 审计日志记录：路由决策、工具调用、失败原因。

## 10. 迁移计划（建议 3 个迭代）

### 迭代 1：页面替换 + 单路由
- 前端：Dashboard -> ChatHub。
- 后端：新增 `/ws/expert-chat` 基础对话。
- 路由：无 @ -> Leader；有 @ -> 直连专家。

### 迭代 2：Leader 协作编排
- 支持 Leader 委派 1-N 专家。
- 增加 delegation 事件。
- 增加知识库开关与范围透传。

### 迭代 3：持久化与资产化
- 会话落库与历史会话。
- 一键生成会话纪要/报告。
- 引入评分与路由优化。

## 11. 验收标准（Definition of Done）
1. 登录后默认进入聊天中枢。
2. 无 @ 时由 Leader 正常回复。
3. `@专家` 时 Leader 不介入、专家直接回复。
4. Leader 委派专家流程可见。
5. 支持图片/PDF 输入并进入同一路由逻辑。
6. 断线可重连并恢复会话。
7. 中英文界面文案完整。

## 12. 待确认决策（你拍板）
1. 首页菜单命名：`专家群聊` 还是 `智能协作`？
2. `@` 语法是否允许多专家（如 `@市场分析师 @风险评估师`）？
3. 专家回复是否必须经 Leader 二次确认后再展示？
4. 多模态文件大小与类型上限。
5. 会话是否默认自动沉淀为报告草稿。

---

该方案为“先设计不实现”版本，可直接作为下一阶段开发蓝图。
