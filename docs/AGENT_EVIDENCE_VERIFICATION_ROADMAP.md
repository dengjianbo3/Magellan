# Agent Evidence Chain Roadmap (Per-Message)

## Goal
让每个专家回复都携带可验证的原始证据链（tool/skill/mcp/calc 调用链），并且在该条消息下方展开查看，不再使用全局证据面板。

## Product Rules
- 证据跟着消息走：每条 `agent_message` 下方可折叠展示。
- 证据必须来自原始执行链：不再从最终文本中做 URL/数字抽取来“猜测证据”。
- 恢复一致性：断线重连、会话恢复后，证据链仍可查看。

## Unified Payload Contract
- `agent_message.evidence_chain[]`
  - `tool`, `status`, `params`, `duration_ms`, `output_preview`, `sources[]`, `numeric_outputs[]`, `error`
- `agent_message.evidence_packet` (optional)
  - `summary`, `key_points[]`, `risks[]`, `confidence`

## Architecture Changes
1. Backend
   - Expert Chat: agent 执行完成后提取并透传 `evidence_chain`。
   - Roundtable: `Message.metadata.evidence_chain` 进入 `agent_event.data`。
   - Session replay/history: assistant 历史消息保留 `evidence_chain/evidence_packet`。
2. Frontend
   - ChatHub/Roundtable 都改为“消息内联证据折叠块”。
   - 删除全局证据面板与抽取型证据聚合工具。

## Delivery Note
详细实施过程、结果和问题见：
- `docs/AGENT_EVIDENCE_CHAIN_IMPLEMENTATION_LOG.md`
