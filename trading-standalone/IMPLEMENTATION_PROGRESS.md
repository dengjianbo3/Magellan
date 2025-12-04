# 持仓状态感知系统 - 实施进度

## ✅ Day 1 完成 (2025-12-04)

### 1. PositionContext数据模型 ✅
**文件**: `position_context.py`

**实现内容**:
- [x] 定义完整的PositionContext数据类（20+字段）
- [x] 实现 `to_summary()` 方法（生成人类可读摘要）
- [x] 实现 `to_dict()` 方法（序列化）
- [x] 计算衍生指标（距离TP/SL/强平的百分比）
- [x] 风险等级显示（🟢安全/🟡警戒/🔴危险）
- [x] Emoji标识（📈盈利/📉亏损，✅可追加/❌满仓）

**关键字段**:
```python
@dataclass
class PositionContext:
    # 基础: has_position, direction, entry_price, size, leverage
    # 盈亏: unrealized_pnl, unrealized_pnl_percent
    # 风险: liquidation_price, distance_to_liquidation_percent
    # 止盈止损: tp/sl_price, distance_to_tp/sl_percent
    # 账户: available_balance, total_equity, used_margin
    # 仓位: current/max_position_percent, can_add, max_additional
    # 时长: opened_at, holding_duration_hours
```

### 2. 数据收集方法 ✅
**文件**: `trading_meeting.py`

**实现内容**:
- [x] `_get_position_context()` 方法
- [x] 从PaperTrader获取position和account
- [x] 计算所有衍生指标
- [x] 无持仓时返回简化context
- [x] 有持仓时返回完整的20+字段

**计算逻辑**:
```python
# 距离止盈止损
distance_to_tp% = (tp_price - current_price) / current_price * 100

# 距离强平
多仓: (current_price - liq_price) / current_price * 100
空仓: (liq_price - current_price) / current_price * 100

# 仓位占比
current_position% = margin_used / total_equity

# 是否可追加
can_add = (margin_used < max_margin) AND (available_balance >= 10)

# 最多可追加
max_additional = min(max_margin - margin_used, available_balance)
```

### 3. 持仓上下文传递 ✅ (部分完成)
**文件**: `trading_meeting.py`

**实现内容**:
- [x] 在 `run()` 方法开始时调用 `_get_position_context()`
- [x] 将position_context传递给 `_build_agenda()`
- [x] 在议程中显示持仓状况
- [x] 将position_context参数添加到各phase方法签名
- [ ] 更新各phase的具体实现（下一步）

---

## 🚧 进行中: Day 2

### 任务: 将PositionContext注入到Agents的Prompt

#### 需要更新的Phase方法:

1. **`_run_market_analysis_phase(position_context)`** - 🔄 进行中
   - 更新TechnicalAnalyst的prompt
   - 更新MacroEconomist的prompt
   - 更新SentimentAnalyst的prompt
   - 加入"当前持仓"部分

2. **`_run_signal_generation_phase(position_context)`** - ⏳ 待完成
   - 更新所有分析师的prompt
   - 根据持仓给出不同的决策选项
   - 无持仓: 做多/做空/观望
   - 有持仓: 维持/追加/减仓/平仓/反向

3. **`_run_risk_assessment_phase(position_context)`** - ⏳ 待完成
   - 更新RiskAssessor的prompt
   - 考虑当前持仓的风险
   - 评估追加/反向操作的风险

4. **`_run_consensus_phase(position_context)`** - ⏳ 待完成
   - 更新Leader的prompt（最重要！）
   - 添加决策矩阵逻辑
   - 根据持仓智能选择direction类型

5. **`_run_execution_phase(signal, position_context)`** - ✅ 已完成
   - 已传递position_context给TradeExecutor

---

## 📝 下一步计划

### Day 2 (剩余任务)

#### 1. 更新Phase 1: Market Analysis
**文件**: `trading_meeting.py` 第223行

```python
async def _run_market_analysis_phase(self, position_context: PositionContext):
    # 在每个分析师的prompt中添加：
    ## 💼 当前持仓状况
    {position_context.to_summary()}
```

#### 2. 更新Phase 2: Signal Generation
**文件**: `trading_meeting.py` 第265行

```python
async def _run_signal_generation_phase(self, position_context: PositionContext):
    # 根据持仓给出不同的决策选项
    if position_context.has_position:
        options = """
        **决策选项（有持仓）**:
        - 维持: 继续持有当前{direction}仓
        - 追加: 追加同方向仓位（可追加: {can_add}）
        - 减仓: 部分平仓
        - 平仓: 全部平仓
        - 反向: 平掉当前仓位，开反向仓
        """
    else:
        options = """
        **决策选项（无持仓）**:
        - 做多: 开多仓
        - 做空: 开空仓
        - 观望: 等待更好时机
        """
```

#### 3. 更新Phase 3: Risk Assessment
**文件**: `trading_meeting.py` 第357行

```python
async def _run_risk_assessment_phase(self, position_context: PositionContext):
    # 添加持仓风险评估
    if position_context.has_position:
        risk_context = f"""
        **当前持仓风险**:
        - 距离强平: {distance_to_liquidation}%
        - 距离止损: {distance_to_sl}%
        - 浮动盈亏: {unrealized_pnl}%
        """
```

#### 4. 更新Phase 4: Consensus (Leader)
**文件**: `trading_meeting.py` 第405行

这是**最重要的**部分，需要：
- 添加决策矩阵逻辑
- 根据持仓智能选择direction类型
- 生成正确的TradingSignal

```python
async def _run_consensus_phase(self, position_context: PositionContext):
    # Leader根据持仓和专家意见做决策
    # 使用决策矩阵：
    # - 无持仓 + 做多 → "long"
    # - 多仓(未满) + 做多 → "add_long"
    # - 多仓(已满) + 做多 → "hold"
    # - 多仓 + 做空 → "reverse_to_short"
    # ... 等等
```

---

## 🎯 Commit记录

### Commit 1: Day 1 完成 (8a7ded8)
```
feat(trading): Day 1 - 实现PositionContext模型和数据收集

- 新增position_context.py（PositionContext数据模型）
- 实现_get_position_context()方法
- 添加to_summary()生成人类可读摘要
- 实现20+字段的完整持仓上下文
- 自动计算衍生指标（距离TP/SL/强平）
```

### Commit 2: Day 2 开始 (当前)
```
feat(trading): Day 2 - 持仓上下文注入到议程

- 更新run()方法，在开始时收集position_context
- 更新_build_agenda()，在议程中显示持仓状况
- 将position_context参数添加到所有phase方法
- 下一步: 更新各phase的prompt实现
```

---

## 📊 整体进度

### Week 1: 基础架构 (5天)
- ✅ Day 1: PositionContext模型
- 🔄 Day 2: 持仓上下文传递 (50%完成)
- ⏳ Day 3: 完成所有Phase的prompt更新
- ⏳ Day 4-5: Agents prompt增强完成

### Week 2: Leader决策逻辑 (4天)
- ⏳ Day 6-7: Leader决策矩阵
- ⏳ Day 8-9: TradingSignal扩展

### Week 3: TradeExecutor增强 (5天)
- ⏳ Day 10-11: 信号一致性检查
- ⏳ Day 12-13: 智能执行策略
- ⏳ Day 14: 集成测试

### Week 4: 测试与优化 (4天)
- ⏳ Day 15-16: E2E测试
- ⏳ Day 17: 本地测试
- ⏳ Day 18: 服务器部署

---

## 🚀 快速继续指南

当你准备继续时，从以下任务开始：

1. **更新 `_run_market_analysis_phase()`** - 添加持仓上下文到prompt
2. **更新 `_run_signal_generation_phase()`** - 根据持仓给出不同选项
3. **更新 `_run_risk_assessment_phase()`** - 评估持仓风险
4. **更新 `_run_consensus_phase()`** - Leader决策矩阵（最关键）

每个phase的更新都需要：
- 修改prompt，加入 `position_context.to_summary()`
- 根据持仓调整决策指导
- 测试新的prompt

---

**当前状态**: Day 2 进行中 (50%完成)
**下一步**: 完成所有Phase的prompt更新
