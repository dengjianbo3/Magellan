# Skills + 缓存 + 路由改造蓝图（系统加速专项）

> 状态: Draft v1.0  
> 负责人: AI Agent Team  
> 创建时间: 2026-02-26  
> 目标: 在不破坏“原子 Agent 统一化”原则下，显著降低 token 成本并缩短端到端耗时。

---

## 1. 核心目标

### 1.1 业务目标

- 缩短长流程（分析/头脑风暴）体感等待时间。
- 降低每轮上下文 token 输入量和总账单成本。
- 提高“同类问题二次提问”的复用率，避免重复搜索与重复推理。

### 1.2 技术目标（量化）

- `prompt_tokens_per_turn` 降低 35%+。
- `tool_calls_per_session` 降低 25%+（不牺牲质量）。
- `time_to_first_meaningful_event` 降低到 3 秒以内（P95 < 5 秒）。
- `full_response_p95` 降低 30%+。

### 1.3 架构约束

- 不新增“场景专用专家”，仍以原子 Agent 为唯一能力源。
- 失败时不回退到 prompt-only 伪答案。
- 所有优化必须可观测、可回滚、可灰度。

---

## 2. 方案总览

本专项分三条并行主线，统一在“上下文编译器（Context Compiler）”汇合：

1. Skills 主线: 让每个原子 Agent 只按需加载能力说明（最小化提示词）。
2. 缓存主线: 对检索、工具结果、模型前缀和会话事件做分层缓存。
3. 路由主线: 用轻量路由先决定“谁处理 + 需要哪些 skills”，减少大模型无效消耗。

---

## 3. 目标架构

## 3.1 Skills Layer（按需能力装载）

- 为每个原子 Agent 拆分:
  - `core_identity`（极短，不超过 300~500 token）
  - `skill_cards[]`（按任务触发）
  - `tool_contracts[]`（工具能力声明）
- Leader/编排层先做 skill 选择，再由 Context Compiler 合成最终提示词。

建议目录（后端）:

```text
backend/services/report_orchestrator/app/core/skills/
  manifest/
    market_analyst.yaml
    technical_analyst.yaml
    ...
  cards/
    market_analyst/
      macro_regime.md
      etf_flow.md
      orderbook_microstructure.md
```

Skill Manifest 关键字段:

- `skill_id`
- `agent_id`
- `triggers`（关键词/意图/场景）
- `dependencies`（需要的工具或前置数据）
- `token_budget_hint`
- `quality_level`（strict/standard/fast）

## 3.2 Cache Fabric（四层缓存）

- L0 会话事件缓存（已具备基础）:
  - WebSocket 事件回放与恢复。
- L1 检索缓存:
  - 搜索 query 规范化 + 时间窗 + 用户域 + agent 域。
- L2 工具结果缓存:
  - 技术指标、行情快照、公共数据 API 结果（TTL 分级）。
- L3 模型前缀缓存:
  - 固定系统前缀 + skill 组合片段可缓存（命中后减少重复输入 token）。

缓存键建议:

`{scope}:{user_id}:{agent_id}:{intent_hash}:{input_hash}:{time_bucket}`

## 3.3 Router（轻路由 + 重执行）

- Router Stage-1（轻量）:
  - 判定目标 agent、任务类型、所需 skills、是否需要工具。
- Router Stage-2（执行）:
  - 只有命中的原子 agent 进入重模型和工具链。
- 群聊/头脑风暴:
  - 由 Leader 聚合路由结果，避免所有专家全量起跑。

---

## 4. 关键设计细节

## 4.1 上下文编译策略（Context Compiler）

输入:

- 用户问题
- 路由决策
- Skill 清单
- 记忆命中
- 缓存命中

输出:

- `compiled_context`（面向目标模型的最小上下文）
- `trace`（记录每段上下文来源和 token 占比）

编译规则:

- 固定前缀前置，动态内容后置。
- 默认只注入 Top-K 证据（可按任务类型配置）。
- 严禁把完整历史会话无差别拼接进每轮。

## 4.2 质量保护

- 设置 `min_required_evidence`：证据不足禁止输出强结论。
- 输出需带 `evidence_refs` 和 `uncertainty` 字段。
- 缓存命中但过期/低置信时，必须触发增量校验而非盲信。

## 4.3 与原子 Agent 原则对齐

- Skills 是原子 Agent 的能力分层，不是新角色。
- 路由只决定“调用谁 + 调哪些能力卡片”，不替代专家分析。
- 复用能力持续沉淀到原子 Agent，而不是编排脚本硬编码。

---

## 5. 分阶段实施计划

## Phase 0: 基线测量（必须先做）

- 增加指标:
  - `prompt_tokens_in`
  - `completion_tokens_out`
  - `cache_hit_ratio`（分层）
  - `route_decision_latency_ms`
  - `tool_calls_count`
- 输出首版基线报表（按场景: 分析/群聊/头脑风暴）。

验收:

- 有可复现 benchmark 脚本与对照数据。

## Phase 1: Skills 框架落地

- 引入 Skill Manifest + Skill Card 读取器。
- Context Compiler v1: 支持 `core_identity + selected_skills`。
- 先接入 3 个高频专家:
  - `market_analyst`
  - `technical_analyst`
  - `onchain_analyst`

验收:

- 三个专家可按任务动态装载 skills，且输出质量不下降。

## Phase 2: 缓存层落地

- L1/L2 缓存接入常用工具:
  - 搜索
  - 技术指标
  - 宏观数据
- L3 前缀缓存接入模型网关调用链。

验收:

- 命中率可观测；重复问题平均时延显著下降。

## Phase 3: 路由优化

- 轻路由模型/规则引擎上线（可开关）。
- 群聊模式改为“按需唤醒专家”，禁止无差别全员并发。

验收:

- 平均参与专家数下降，但结论质量与用户满意度不下降。

## Phase 4: 灰度、回归与压测

- Feature Flag:
  - `skills_enabled`
  - `cache_l1_enabled`
  - `cache_l2_enabled`
  - `router_v2_enabled`
- 按用户/场景分流灰度。
- 回归重点:
  - 鉴权
  - 多模态
  - 会话恢复
  - HITL 注入

验收:

- 所有核心链路无回归，且指标达到目标阈值。

---

## 6. 主要改造点清单

后端（优先）:

- `app/main.py`（路由入口、编排注入）
- `app/core/agent_registry.py`（agent->skills 映射）
- `app/core/roundtable/rewoo_agent.py`（skill 感知执行）
- `app/core/orchestrators/base_orchestrator.py`（上下文编译）
- `app/core/session_store.py`（缓存与事件指标）
- `app/core/model_policy.py`（路由阶段模型策略）

新增模块:

- `app/core/skills/*`
- `app/core/context_compiler.py`
- `app/core/cache/*`
- `app/core/router/*`

前端（次优先）:

- 显示“已命中缓存/已装载能力”的轻提示（不暴露底层模型细节）。
- 流式阶段提示优化，降低等待焦虑。

---

## 7. 风险与应对

- 风险: Skill 卡片过长导致反向膨胀  
  应对: 单卡 token 上限 + 自动 lint 检查。

- 风险: 缓存污染导致错误复用  
  应对: 强作用域键 + TTL + 证据时间戳校验。

- 风险: 轻路由误判导致错分专家  
  应对: 置信度阈值 + 回退到 leader 二次判定。

- 风险: 为了速度牺牲质量  
  应对: 质量门禁（证据不足不下结论）+ 离线回放对比。

---

## 8. 验收标准（DoD）

- 有基线、有优化后数据、有对照说明。
- 平均 token 输入和时延满足目标。
- 失败语义保持严格，不出现 prompt-only 伪答案回退。
- 代码路径可通过 Feature Flag 全量回滚。

---

## 9. 实施日志（持续更新）

> 规则: 每次实现、调试、回滚、决策变更都记录在本节。  
> 字段: 时间 | 阶段 | 操作 | 结果 | 问题 | 下一步。

| 时间 (UTC+8) | 阶段 | 操作 | 结果 | 问题 | 下一步 |
|---|---|---|---|---|---|
| 2026-02-26 | 规划 | 创建本蓝图文档 | 完成 | 无 | 进入 Phase 0 基线测量设计 |
| 2026-02-26 | Phase 0 | 在 `metrics.py` 增加上下文/路由/工具/缓存指标与记录函数 | 完成 | 无 | 扩展到 roundtable 与 expert-chat 全链路 |
| 2026-02-26 | Phase 0 | 在 `main.py`、`search_router.py`、`agent.py` 接入首批埋点 | 完成 | merge 统计变量命名不清晰 | 修复 merge 统计并补齐其余入口 |
| 2026-02-26 | Phase 0 | 补齐 `rewoo_agent.py` 与 `llm_helper.py` 埋点；修复 `main.py` 多图 merge 统计上下文来源 | 完成 | 待验证 Prometheus 指标曲线 | 执行编译与运行验证并沉淀采样脚本 |
| 2026-02-26 | Phase 0 | 新增 `scripts/collect_phase0_baseline.sh` 采样脚本（`magellan_context_*`） | 完成 | 依赖运行中 `/metrics` | 拉起服务后做 3 天窗口基线采样 |
| 2026-02-26 | Phase 1 | 新增 `core/skills` 选择器与 4 份 skills manifest（market/technical/onchain/leader） | 完成 | 目前仅接入 expert-chat prompt 链路 | 下一步接入 roundtable/rewoo 的上下文编译入口 |
| 2026-02-26 | Phase 1 | 修复 `technical_analyst` manifest YAML 解析失败（包含冒号文案未加引号） | 完成 | 无 | 继续扩展更多 agent 的 skills 卡片 |
| 2026-02-26 | Phase 1 | 将 skills_context 注入 `rewoo_agent` 上下文，并按命中情况收缩历史窗口 | 完成 | 仍需做线上效果对比 | 下一步做 A/B 基线对照（有无 skills） |
| 2026-02-26 | Phase 1 | 完成容器内 smoke test：skills 加载、expert-chat prompt 注入、ReWOO skills_context 注入、metrics 基础埋点可用 | 完成 | 无 | 进入 Phase 2 缓存改造 |
| 2026-02-26 | Phase 2 | 在 `technical_tools.py` 新增 OHLCV TTL 缓存（按 symbol/timeframe/limit/market_type），接入命中/失效/淘汰指标 | 完成 | TTL 最小值为 5s（测试需匹配） | 下一步扩展到宏观/链上高频工具缓存 |
| 2026-02-26 | Phase 2 | 完成技术缓存回归：重复请求命中缓存，不同 key 分流，过期后回源 | 完成 | 无 | 做跨场景压测与命中率观测 |
| 2026-02-26 | Phase 0 | 加固 `collect_phase0_baseline.sh`：增加采集超时与重试参数，降低高负载偶发采集失败 | 完成 | 无 | 与 `/metrics` 延迟问题联动观测 |
| 2026-02-26 | Phase 2 | 在 `yahoo_finance_tool.py` 新增 action 级 TTL 缓存（price/history/info/news/valuation/dividends/holders），仅缓存成功结果 | 完成 | 初版分支提前 return 导致未统一缓存 | 已修复并完成缓存回归 |
| 2026-02-26 | Phase 2 | 完成容器内 smoke test：`YAHOO_CACHE_SMOKE_OK`、`TECHNICAL_CACHE_SMOKE_OK`、`METRICS_SMOKE_OK` | 完成 | 无 | 进入跨场景压测与命中率评估 |
| 2026-02-26 | Phase 3 | 在 `main.py` 为 Leader 路由新增短 TTL 决策缓存（key=消息+历史窗口+知识开关），接入缓存指标 | 完成 | 无 | 下一步接入路由降级策略与命中率看板 |
| 2026-02-26 | Phase 3 | 完成容器内路由缓存回归：`LEADER_ROUTE_CACHE_SMOKE_OK`（同问题重复只调用一次路由模型） | 完成 | 无 | 继续做在线压测和阈值调优 |
| 2026-02-26 | Phase 3 | 新增压测脚本 `run_skills_cache_routing_benchmark.py` 与容器执行包装脚本 | 完成 | compose 未挂载 `scripts/` 到容器 | 采用 stdin 注入执行，无需改容器挂载 |
| 2026-02-26 | Phase 3 | 执行 benchmark（模拟上游 200ms）: leader/technical/yahoo 三路 warm 延迟降至约 0.1~0.2ms，提速 99.9%+ | 完成 | 指标 `metrics_before` 在单次短跑下为空 | 后续用基线采样脚本做连续窗口观测 |
| 2026-02-26 | Phase 3 | 新增 `summarize_context_metrics.py`，用于聚合 `magellan_context_*` 并计算 cache hit rate | 完成 | 在线 `/metrics` 在高负载下可能拉取慢 | 可先对采样文件离线汇总 |
| 2026-02-26 | Phase 3 | Expert Chat 默认路由链路优化：Leader 路由失败时自动降级到 Leader 直答；无委派且已有 `leader_reply` 时复用结果避免二次 LLM 调用 | 完成 | 无 | 后续观察线上 `route_fallback` 触发率 |
| 2026-02-26 | Phase 3 | 二次 benchmark 回归通过（路由/缓存优化后性能与行为稳定） | 完成 | 无 | 进入在线基线采样与阈值调参 |
| 2026-02-26 | Phase 4 | 新增 `run_context_baseline_window.sh`，支持按窗口自动采样并输出 `summary.jsonl` 趋势文件 | 完成 | 依赖目标环境可访问 `/metrics` | 下一步采集 30~60 分钟真实数据并设阈值告警 |
| 2026-02-26 | Phase 4 | 执行容器内真实窗口采样（`tmp/phase0_baseline_window_live/summary.jsonl`） | 完成 | 首轮全部为 `delegated:success`，无 `cached` 路由事件 | 增加定向流量样本验证路由缓存命中 |
| 2026-02-26 | Phase 4 | 执行短流量回放 + 窗口采样（`tmp/phase0_baseline_window_live_after_traffic/summary.jsonl`） | 完成 | 流量仍以委派成功为主，阈值评估 `overall=ALERT` | 增加“同问题双会话”路由探针 |
| 2026-02-26 | Phase 4 | 执行路由缓存探针（两次独立会话同问题）并采样（`tmp/phase0_baseline_window_live_route_probe/summary.jsonl`） | 完成 | 已出现 `delegated:cached=1`，`route_cached_ratio_pct=20` 达标 | 进入阈值分层建议（冷启动 vs 稳态） |
| 2026-02-26 | Phase 4 | 形成真实线上窗口阈值建议与告警分级策略 | 完成 | 小样本下命中率波动较大 | 建议加最小样本门槛并延长窗口 |
| 2026-02-26 | Phase 4 | 增强 `evaluate_context_thresholds.py`：支持 `warmup/steady/auto` 档位与最小样本门槛 | 完成 | 仍需在 Prometheus 告警规则层同步 volume gate | 下一步补充线上告警表达式与仪表盘 |

---

## 10. 问题追踪（持续更新）

| ID | 日期 | 场景 | 问题描述 | 影响 | 状态 | 处理人 | 备注 |
|---|---|---|---|---|---|---|---|
| ISSUE-001 | 2026-02-26 | N/A | 初版蓝图待确认指标阈值 | 中 | Open | TBD | 与业务目标对齐后锁定 |
| ISSUE-002 | 2026-02-26 | expert-chat multimodal | 多图 merge 路径统计中错误引用响应对象字段，导致 prompt 来源不准确 | 中 | Closed | Codex | 已改为使用 `merge_request.messages` |
| ISSUE-003 | 2026-02-26 | skills manifest | `technical_analyst.yaml` 因未转义冒号导致加载失败 | 低 | Closed | Codex | 已为文案字段补充引号并验证 |
| ISSUE-004 | 2026-02-26 | observability | 在当前高负载状态下，`/metrics` 在外部采集端偶发超时 | 中 | Open | Codex | 已先加脚本超时重试，后续仍需评估标签基数与采集窗口 |
| ISSUE-005 | 2026-02-26 | yahoo cache | `execute` 初版缓存改造时多数 action 分支提前 `return`，导致缓存未生效 | 中 | Closed | Codex | 已改为统一 result 流程并回归通过 |
| ISSUE-006 | 2026-02-26 | benchmark runtime | `scripts/` 目录未挂载到 `report_orchestrator` 容器，直接容器路径执行脚本失败 | 低 | Closed | Codex | 已提供 `run_skills_cache_routing_benchmark_in_container.sh` 通过 stdin 执行 |
| ISSUE-007 | 2026-02-26 | expert chat routing | 路由阶段异常会直接让本轮消息失败，用户体验中断 | 中 | Closed | Codex | 已增加 route fallback（leader direct）并保留错误可观测 |
| ISSUE-008 | 2026-02-26 | alert calibration | 低流量/短窗口时缓存命中率对样本分布敏感，阈值易误报 | 中 | Open | Codex | 建议引入最小样本门槛（如 route>=20, cache events>=30） |

---

## 11. 下一步（立即执行建议）

1. 连续执行 3 天线上窗口采样（每 30s 抓取，输出 `summary.jsonl`）。
2. 告警判定加入最小样本门槛（route>=20、tool success+error>=30、cache hit+miss+stale>=30）。
3. 将阈值按阶段分层：冷启动/低流量阈值 + 稳态阈值。
4. 每日更新第 9 节实施日志与第 10 节问题追踪。
5. 基于 `tmp/phase0_baseline_window_live_route_probe/summary.jsonl` 继续扩充真实样本。

---

## 12. 真实线上采样结论（2026-02-26）

### 12.1 数据快照

- 采样文件:
  - `tmp/phase0_baseline_window_live/summary.jsonl`
  - `tmp/phase0_baseline_window_live_after_traffic/summary.jsonl`
  - `tmp/phase0_baseline_window_live_route_probe/summary.jsonl`
- 最新窗口（route probe）核心指标:
  - `leader_route` 命中率: `20.0%`
  - `technical_ohlcv` 命中率: `25.0%`
  - `yahoo_finance` 命中率: `20.0%`
  - `route_cached_ratio_pct`: `20.0%`（已达当前建议线）
  - `route_error_ratio_pct`: `0.0%`
  - `tool_error_ratio_pct`: `0.0%`

### 12.2 结论

- 缓存与路由统计链路已在真实流量下可观测，且出现实际 `delegated:cached` 事件。
- 当前主要问题不是错误率，而是低样本阶段命中率不足，阈值评估容易触发误报。

### 12.3 阈值建议（用于后续告警）

- 冷启动/低流量阶段（route<20）:
  - `leader_route_hit_rate_pct >= 15`
  - `technical_ohlcv_hit_rate_pct >= 20`
  - `yahoo_finance_hit_rate_pct >= 15`
- 稳态阶段（route>=20）:
  - `leader_route_hit_rate_pct >= 30`（后续目标提升至 40）
  - `technical_ohlcv_hit_rate_pct >= 40`（后续目标提升至 55）
  - `yahoo_finance_hit_rate_pct >= 25`（后续目标提升至 30）
