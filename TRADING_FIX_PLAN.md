# 自动交易系统修复与优化方案

## 项目诊断总结

经过对整个交易系统代码的深度分析（`trading_system.py`, `trading_routes.py`, `trading_mode.py`, `mode_manager.py`, `executor_agent.py`, `paper_trader.py`, `scheduler.py`, `trigger/lock.py`, `fast_monitor.py`, `AutoTradingView.vue` 等），共发现 **34+ 个问题**，按严重程度分为以下几个层次。

---

## 一、CRITICAL — 半自动模式确认流程断裂

### 问题根因

半自动模式的后端逻辑**已经正确实现**，但前端与后端之间存在**严重的对接断裂**：

### 1.1 前端缺少 `pending_trade_created` WebSocket 事件处理器
- **文件**: `AutoTradingView.vue:1772-1959`
- **问题**: `handleWebSocketMessage()` 中没有 `pending_trade_created` 的 case 分支
- **后果**: 后端正确广播了 `pending_trade_created` 事件，但前端完全忽略了

### 1.2 `signal_generated` 事件不分模式就弹出确认弹窗
- **文件**: `AutoTradingView.vue:1831-1892`
- **问题**: 收到 `signal_generated` 后，无论什么模式都会设置 `showDecisionModal = true`
- **后果**:
  - FULL_AUTO 模式：不应弹窗（已经自动执行了），但弹了
  - SEMI_AUTO 模式：弹窗了但用的是假的 `decision_id: decision-${Date.now()}`，不是后端的真实 `trade_id`
  - MANUAL 模式：不应弹窗，但也弹了

### 1.3 确认按钮调用了错误的 API
- **文件**: `AutoTradingView.vue:1481-1531`
- **问题**: `handleConfirmDecision()` 调用了两个过时的旧 API：
  - `POST /api/trading/decision` — 仅做 RLHF 记录，不执行交易
  - `POST /api/trading/execute` — 绕过了 mode_manager，直接用 30% 余额开仓
- **应该调用**: `POST /api/trading/pending/{trade_id}/confirm`（在 `trading_routes.py:218` 或 `trading_mode.py:361` 中定义）

### 1.4 路由冲突：两套 pending trade API 共存
- **文件1**: `trading_routes.py:195-317` — `/api/trading/pending/*`
- **文件2**: `trading_mode.py:296-440` — `/api/trading/pending/*`, `/api/trading/confirm/*`, `/api/trading/reject/*`
- **问题**: 两个 router 都注册了 `/api/trading/pending` 路由，FastAPI 会按注册顺序匹配第一个，导致行为不确定
- **main.py:166-167**: `trading_router` 先注册，`trading_mode_router` 后注册

### 1.5 fetchPendingTrades 解析字段不匹配
- **文件**: `AutoTradingView.vue:1272-1282`
- **问题**: `if (data.trades)` 但后端 `trading_routes.py:201` 返回 `pending_trades` 字段，而 `trading_mode.py:327` 返回 `trades` 字段
- **后果**: 取决于哪个路由被匹配到，可能解析失败

---

## 二、HIGH — 全自动模式执行链路问题

### 2.1 FULL_AUTO 模式也会弹出确认弹窗
- **文件**: `AutoTradingView.vue:1871-1884`
- **问题**: 收到 `signal_generated` 后无条件弹窗，但 FULL_AUTO 的交易已经在后端自动执行了
- **后果**: 用户看到弹窗以为需要确认，但交易实际已经完成

### 2.2 TriggerLock 无超时机制（死锁风险）
- **文件**: `trigger/lock.py:77-89`
- **问题**: `acquire_check()` 将状态设为 "checking"，但如果检查操作挂起，锁永远不会释放
- **后果**: 系统可能永久卡在 "checking" 状态，阻塞所有后续触发

### 2.3 Scheduler 超时后状态不重置
- **文件**: `scheduler.py:200-208`
- **问题**: `asyncio.wait_for()` 超时后，捕获了异常但没有重置调度器状态，状态保持在 "ANALYZING"
- **后果**: 调度器死锁，无法进行新的分析周期

### 2.4 PaperTrader TP/SL 回退计算逻辑错误
- **文件**: `paper_trader.py:503-527`
- **问题**: 无效 TP/SL 时使用 `default_tp_percent / leverage` 重新计算，这个除法是错的
- **示例**: `tp_percent=5%, leverage=5x` → 计算出 `1%` 价格变动，但实际应该是 `5%`

### 2.5 信号执行结果判断不准确
- **文件**: `trading_system.py:396-411`
- **问题**:
  - 用 `order_id` 判断是否成功只适用于 OKX，PaperTrader 的成功判断逻辑不同
  - `failed_actions` 列表中的 `insufficient_margin` 是 `action_taken` 字段，不是 `action` 字段
  - `signal.reasoning` 被错误地替换标签

---

## 三、MEDIUM — 状态管理与数据一致性

### 3.1 交易历史仅存在内存中
- **文件**: `trading_system.py:72`
- **问题**: `_trade_history` 是内存列表，服务重启后丢失
- **改进**: 已有部分 Redis 持久化（decision_store），但回退逻辑不完善

### 3.2 Pending Trade Redis 不清理
- **文件**: `mode_manager.py:325-338`
- **问题**: `trading:pending_list` 会无限增长，过期的 trade_id 不会从列表中移除
- **后果**: Redis 内存泄漏

### 3.3 通知服务不存在
- **文件**: `mode_manager.py:247-255`
- **问题**: 尝试导入 `get_notification_service()` 但模块不存在，静默失败
- **后果**: 用户不会收到任何 pending trade 通知（除了 WebSocket，而 WebSocket 又没处理）

### 3.4 WebSocket 重连时不恢复模式状态
- **文件**: `AutoTradingView.vue:1759-1770`
- **问题**: WebSocket 断开重连后，不会重新获取当前模式和 pending trades
- **后果**: 前端模式状态可能与后端不一致

### 3.5 Cooldown 不随胜利交易重置
- **文件**: `scheduler.py:291-309`
- **问题**: 赢了交易只重置连续亏损计数，不重置冷却计时器
- **后果**: 用户可能在冷却中赢了一笔，但仍然被锁定

---

## 四、修复实施方案

### Phase 1: 半自动模式核心修复（最高优先级）

#### Step 1.1: 统一后端 API，消除路由冲突
**目标**: 删除 `trading_routes.py` 中重复的 pending trade 路由，统一使用 `trading_mode.py` 中的实现

```
操作:
1. 从 trading_routes.py 删除:
   - GET /api/trading/pending (line 195-204)
   - GET /api/trading/pending/{trade_id} (line 207-215)
   - POST /api/trading/pending/{trade_id}/confirm (line 218-279)
   - POST /api/trading/pending/{trade_id}/reject (line 282-317)

2. 在 trading_mode.py 中确保路由路径与前端一致:
   - GET /api/trading/mode ✅ (已存在)
   - POST /api/trading/mode ✅ (已存在)
   - GET /api/trading/pending ✅ (已存在)
   - POST /api/trading/confirm/{trade_id} → 改为 POST /api/trading/pending/{trade_id}/confirm
   - POST /api/trading/reject/{trade_id} → 改为 POST /api/trading/pending/{trade_id}/reject
```

#### Step 1.2: 修复前端 WebSocket 事件处理
**目标**: 正确处理 `pending_trade_created` 事件，按模式区分弹窗行为

```
操作:
1. 在 handleWebSocketMessage() 中添加 'pending_trade_created' case:
   - 使用后端返回的真实 trade_id
   - 弹出确认弹窗
   - 添加到 pendingTrades 列表

2. 修改 'signal_generated' case:
   - 添加模式判断: if (msg.mode === 'semi_auto') break; // 等 pending_trade_created
   - FULL_AUTO 模式不弹窗
   - MANUAL 模式不弹窗

3. 添加 'trade_confirmed' 和 'trade_rejected' case:
   - 关闭弹窗
   - 刷新数据
```

#### Step 1.3: 修复确认/拒绝按钮 API 调用
**目标**: `handleConfirmDecision()` 和 `handleDeferDecision()` 使用正确的 API

```
操作:
1. handleConfirmDecision():
   - 调用 POST /api/trading/pending/{trade_id}/confirm
   - 传递正确的参数: user_id, leverage (如修改)
   - 移除对 /api/trading/decision 和 /api/trading/execute 的调用

2. handleDeferDecision():
   - 调用 POST /api/trading/pending/{trade_id}/reject
   - 传递 reason 参数
```

#### Step 1.4: 修复 fetchPendingTrades 字段映射
**目标**: 确保前端正确解析 pending trades 响应

```
操作:
1. 统一使用 trading_mode.py 的响应格式 (trades 字段)
2. 解析 pending trade 对象的字段名保持一致
```

### Phase 2: 全自动模式稳定性修复

#### Step 2.1: TriggerLock 添加超时机制
```
操作:
1. acquire_check() 添加 timeout 参数 (默认 300秒)
2. 超时自动释放锁，状态回退到 "idle"
3. 添加守护任务定期检查锁状态
```

#### Step 2.2: Scheduler 超时状态重置
```
操作:
1. asyncio.wait_for() 超时后:
   - 设置 state = "idle"
   - 释放 TriggerLock
   - 广播 analysis_error 事件
2. 添加 _reset_state() 辅助方法
```

#### Step 2.3: 修复 PaperTrader TP/SL 计算
```
操作:
1. 移除错误的 / leverage 除法
2. TP/SL 百分比应该是相对于价格的变动百分比，与杠杆无关
3. 杠杆影响的是保证金需求，不是价格目标
```

#### Step 2.4: 修复信号执行结果判断
```
操作:
1. 统一 PaperTrader 和 OKX 的返回格式
2. 用 success 字段作为主要判断依据
3. 移除对 order_id 的特殊依赖
```

### Phase 3: 状态持久化与清理

#### Step 3.1: Pending Trade Redis 清理
```
操作:
1. get_pending_trades() 中清理过期的 trade_id from pending_list
2. 或添加后台定时清理任务 (每 5 分钟)
```

#### Step 3.2: WebSocket 重连恢复
```
操作:
1. ws.onopen 中:
   - 重新 fetchTradingMode()
   - 如果是 semi_auto, fetchPendingTrades()
   - fetchStatus(), fetchPosition()
```

#### Step 3.3: Cooldown 逻辑修正
```
操作:
1. record_trade_result() 中:
   - 赢了交易时同时重置冷却计时器
   - 或至少减少剩余冷却时间的 50%
```

### Phase 4: 代码清理（可选但推荐）

#### Step 4.1: 移除 trading_routes.py 中的重复路由
- 已在 Phase 1 Step 1.1 中覆盖

#### Step 4.2: 移除 /api/trading/execute 过时端点
- 前端不再调用此端点后可以标记为 deprecated 或删除

#### Step 4.3: 移除 /api/trading/decision RLHF 旧端点
- 如果不再需要旧的 RLHF 数据收集，可以移除
- 或保留但标记为内部使用

---

## 五、实施优先级排序

| 优先级 | Phase | 预计范围 | 影响 |
|--------|-------|----------|------|
| P0 | Phase 1.1-1.4 | 半自动模式核心修复 | 解决用户报告的确认弹窗问题 |
| P1 | Phase 2.1-2.2 | TriggerLock + Scheduler | 防止系统死锁 |
| P2 | Phase 2.3-2.4 | TP/SL + 执行判断 | 交易逻辑正确性 |
| P3 | Phase 3.1-3.3 | 状态管理 | 系统可靠性 |
| P4 | Phase 4.1-4.3 | 代码清理 | 维护性 |

---

## 六、文件变更清单

| 文件 | 变更类型 | Phase |
|------|----------|-------|
| `frontend/src/views/AutoTradingView.vue` | 修改 WebSocket handler, 确认/拒绝逻辑 | P0 |
| `backend/.../api/trading_routes.py` | 删除重复路由 | P0 |
| `backend/.../api/routers/trading_mode.py` | 统一路由路径 | P0 |
| `backend/.../trigger/lock.py` | 添加超时机制 | P1 |
| `backend/.../scheduler.py` | 超时状态重置 | P1 |
| `backend/.../paper_trader.py` | 修复 TP/SL 计算 | P2 |
| `backend/.../services/trading_system.py` | 修复执行判断逻辑 | P2 |
| `backend/.../mode_manager.py` | Redis 清理 | P3 |
