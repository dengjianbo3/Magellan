# 🎯 持仓状态感知与智能决策系统 - 设计方案

## 📋 问题分析

### 当前系统的缺陷

**场景1**: 已有多仓（未满仓）→ 新决策：做多
- ❌ 当前：重复开仓（可能失败）
- ✅ 应该：追加持仓

**场景2**: 已有多仓（已满仓）→ 新决策：做多
- ❌ 当前：尝试开仓（失败）
- ✅ 应该：维持持仓，不操作

**场景3**: 已有多仓 → 新决策：观望
- ❌ 当前：不明确
- ✅ 应该：维持持仓，不平仓

**场景4**: 已有多仓 → 新决策：做空
- ❌ 当前：直接尝试开空（失败）
- ✅ 应该：**先平多仓，再开空仓**（反向操作）

**场景5**: 已有多仓（浮盈/浮亏）→ 新决策：平仓
- ❌ 当前：可能平仓
- ✅ 应该：评估是否合理平仓

### 核心问题

1. **Agents讨论时缺少持仓上下文** - 不知道当前有什么仓位
2. **Leader决策时缺少持仓感知** - 无法根据现有仓位做决策
3. **TradeExecutor缺少智能处理** - 无法处理复杂的仓位转换逻辑

---

## 🎯 解决方案设计

### 方案概述

**三层架构**:
```
Layer 1: 持仓上下文传递 (Position Context Propagation)
   ↓
Layer 2: 智能决策生成 (Intelligent Decision Making)
   ↓
Layer 3: 智能执行引擎 (Smart Execution Engine)
```

---

## 📊 详细设计

### Layer 1: 持仓上下文传递

#### 1.1 增强的持仓信息模型

```python
@dataclass
class PositionContext:
    """完整的持仓上下文"""
    
    # 基础信息
    has_position: bool
    current_position: Optional[Dict] = None  # 当前持仓详情
    
    # 持仓详情（如果有持仓）
    direction: Optional[str] = None  # "long" or "short"
    entry_price: float = 0.0
    current_price: float = 0.0
    size: float = 0.0
    leverage: int = 1
    margin_used: float = 0.0
    
    # 盈亏情况
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    
    # 风险指标
    liquidation_price: Optional[float] = None
    distance_to_liquidation_percent: float = 0.0
    
    # 止盈止损
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    distance_to_tp_percent: float = 0.0
    distance_to_sl_percent: float = 0.0
    
    # 账户状态
    available_balance: float = 0.0
    total_equity: float = 0.0
    used_margin: float = 0.0
    
    # 仓位限制
    max_position_percent: float = 1.0  # 最大仓位比例
    current_position_percent: float = 0.0  # 当前仓位占比
    can_add_position: bool = False  # 是否可以追加
    max_additional_amount: float = 0.0  # 最多还能追加多少USDT
    
    # 持仓时长
    opened_at: Optional[datetime] = None
    holding_duration_hours: float = 0.0
```

#### 1.2 在每次会议前收集持仓上下文

```python
# trading_meeting.py
async def run(self, context: str) -> Optional[TradingSignal]:
    """运行交易会议"""
    
    # 🆕 Step 0: 收集完整的持仓上下文
    position_context = await self._get_position_context()
    
    # 🆕 将持仓上下文注入到每个Phase的prompt中
    context_summary = self._format_position_context(position_context)
    
    # Phase 1: Market Analysis (带上持仓上下文)
    await self._run_market_analysis_phase(context, context_summary)
    
    # Phase 2: Signal Generation (带上持仓上下文)
    await self._run_signal_generation_phase(context_summary)
    
    # Phase 3: Risk Assessment (带上持仓上下文)
    await self._run_risk_assessment_phase(context_summary)
    
    # Phase 4: Consensus (Leader综合考虑持仓)
    signal = await self._run_consensus_phase(context_summary, position_context)
    
    # Phase 5: Execution (TradeExecutor根据持仓智能执行)
    result = await self._run_execution_phase(signal, position_context)
    
    return signal
```

---

### Layer 2: 智能决策生成

#### 2.1 增强Agents的Prompt（注入持仓上下文）

**示例：TechnicalAnalyst的增强Prompt**

```python
prompt = f"""
你是技术分析专家 (TechnicalAnalyst)。

## 📊 当前市场状况
{market_data}

## 💼 当前持仓状况 ⚠️ 重要！
{position_context_summary}

**当前持仓**: {"有持仓" if has_position else "无持仓"}
{f'''
- 方向: {direction} ({leverage}x杠杆)
- 入场价: ${entry_price:.2f}
- 当前价: ${current_price:.2f}
- 浮动盈亏: ${unrealized_pnl:.2f} ({unrealized_pnl_percent:+.2f}%)
- 止盈价: ${tp_price:.2f} (距离: {distance_to_tp:.2f}%)
- 止损价: ${sl_price:.2f} (距离: {distance_to_sl:.2f}%)
- 持仓时长: {holding_hours:.1f}小时
- 仓位占比: {position_percent:.1f}% / {max_position_percent:.1f}%
- {'✅ 可追加' if can_add else '❌ 已满仓'}
''' if has_position else '无持仓，可自由开仓'}

## 🎯 你的任务
基于技术指标和**当前持仓情况**，给出建议：

### 决策选项（根据持仓情况选择）：

**如果无持仓**：
- `做多` - 开多仓
- `做空` - 开空仓  
- `观望` - 等待更好时机

**如果有持仓（{direction if has_position else 'N/A'}）**：
- `维持` - 继续持有，不操作
- `追加` - 追加同方向仓位（如果可追加）
- `减仓` - 部分平仓
- `平仓` - 全部平仓
- `反向` - 平掉当前仓位，开反向仓

### 决策考虑因素：
1. **技术信号** vs **当前持仓方向**是否一致？
2. **止盈止损距离** - 是否接近触发？
3. **持仓时长** - 是否该获利了结？
4. **浮动盈亏** - 是否该止盈/止损？
5. **仓位占比** - 是否还能追加？

请给出你的分析和建议！
"""
```

#### 2.2 Leader的增强决策逻辑

**Leader需要综合考虑**：
1. 各专家的建议
2. 当前持仓状态
3. 持仓与新建议的关系

**决策矩阵**：

| 当前持仓 | 专家建议 | Leader决策 | 理由 |
|---------|---------|-----------|------|
| 无持仓 | 做多 | `open_long` | 开新仓 |
| 无持仓 | 做空 | `open_short` | 开新仓 |
| 无持仓 | 观望 | `hold` | 等待 |
| **多仓(未满)** | 做多 | `add_long` | 追加多仓 |
| **多仓(已满)** | 做多 | `hold` | 维持，不操作 |
| **多仓** | 观望 | `hold` | 维持持仓 |
| **多仓** | 做空 | `reverse_to_short` | 平多+开空 |
| **多仓** | 平仓 | `close_long` | 平仓 |
| **空仓(未满)** | 做空 | `add_short` | 追加空仓 |
| **空仓(已满)** | 做空 | `hold` | 维持，不操作 |
| **空仓** | 观望 | `hold` | 维持持仓 |
| **空仓** | 做多 | `reverse_to_long` | 平空+开多 |
| **空仓** | 平仓 | `close_short` | 平仓 |

#### 2.3 新的决策类型

扩展 `TradingSignal` 支持更多操作类型：

```python
class TradingSignal(BaseModel):
    """扩展的交易信号"""
    
    # 新增决策类型
    direction: Literal[
        "long",           # 开多（无持仓时）
        "short",          # 开空（无持仓时）
        "hold",           # 观望/维持
        "close",          # 平仓
        "add_long",       # 追加多仓
        "add_short",      # 追加空仓
        "reverse_to_long",  # 反向：平空→开多
        "reverse_to_short", # 反向：平多→开空
        "reduce_long",    # 减仓（多）
        "reduce_short"    # 减仓（空）
    ]
    
    # 新增字段
    action_reason: str  # 为什么选择这个操作
    position_aware: bool = True  # 是否考虑了持仓
    
    # 对于追加/减仓操作
    adjust_amount_percent: Optional[float] = None  # 追加/减少的比例
```

---

### Layer 3: 智能执行引擎

#### 3.1 TradeExecutor的增强逻辑

```python
class TradeExecutor:
    """智能交易执行引擎"""
    
    async def execute_signal(
        self, 
        signal: TradingSignal,
        position_context: PositionContext
    ) -> Dict[str, Any]:
        """
        智能执行交易信号
        
        根据signal.direction和position_context，智能选择执行策略：
        - open_long/short: 直接开仓（确保无持仓）
        - add_long/short: 追加持仓（确保同向且可追加）
        - reverse_to_long/short: 先平仓，再开反向仓
        - close: 平仓（确保有持仓）
        - hold: 不操作
        - reduce_long/short: 部分平仓
        """
        
        # Step 1: 验证信号与持仓的一致性
        consistency_check = self._check_signal_consistency(signal, position_context)
        if not consistency_check['ok']:
            return self._reject(consistency_check['reason'])
        
        # Step 2: 根据signal.direction路由到具体的执行策略
        if signal.direction == "hold":
            return self._execute_hold(signal, position_context)
        
        elif signal.direction in ["long", "short"]:
            return await self._execute_open(signal, position_context)
        
        elif signal.direction in ["add_long", "add_short"]:
            return await self._execute_add(signal, position_context)
        
        elif signal.direction in ["reverse_to_long", "reverse_to_short"]:
            return await self._execute_reverse(signal, position_context)
        
        elif signal.direction == "close":
            return await self._execute_close(signal, position_context)
        
        elif signal.direction in ["reduce_long", "reduce_short"]:
            return await self._execute_reduce(signal, position_context)
        
        else:
            return self._reject(f"未知的操作类型: {signal.direction}")
    
    def _check_signal_consistency(
        self, 
        signal: TradingSignal, 
        position_context: PositionContext
    ) -> Dict[str, Any]:
        """
        检查信号与持仓的一致性
        
        例如：
        - 如果要add_long，必须当前有long持仓
        - 如果要reverse_to_short，必须当前有long持仓
        - 如果要open_long，必须当前无持仓
        """
        has_position = position_context.has_position
        current_direction = position_context.direction
        
        if signal.direction in ["long", "short"]:
            if has_position:
                return {
                    "ok": False,
                    "reason": f"已有{current_direction}持仓，不能直接开{signal.direction}仓。建议使用add_或reverse_操作。"
                }
        
        elif signal.direction == "add_long":
            if not has_position:
                return {"ok": False, "reason": "无持仓，不能追加多仓"}
            if current_direction != "long":
                return {"ok": False, "reason": f"当前是{current_direction}仓，不能追加多仓"}
            if not position_context.can_add_position:
                return {"ok": False, "reason": "已达仓位上限，不能追加"}
        
        elif signal.direction == "add_short":
            if not has_position:
                return {"ok": False, "reason": "无持仓，不能追加空仓"}
            if current_direction != "short":
                return {"ok": False, "reason": f"当前是{current_direction}仓，不能追加空仓"}
            if not position_context.can_add_position:
                return {"ok": False, "reason": "已达仓位上限，不能追加"}
        
        elif signal.direction == "reverse_to_long":
            if not has_position:
                return {"ok": False, "reason": "无持仓，不能执行反向操作"}
            if current_direction != "short":
                return {"ok": False, "reason": f"当前是{current_direction}仓，不能反向到long"}
        
        elif signal.direction == "reverse_to_short":
            if not has_position:
                return {"ok": False, "reason": "无持仓，不能执行反向操作"}
            if current_direction != "long":
                return {"ok": False, "reason": f"当前是{current_direction}仓，不能反向到short"}
        
        elif signal.direction == "close":
            if not has_position:
                return {"ok": False, "reason": "无持仓，不能平仓"}
        
        return {"ok": True, "reason": ""}
    
    async def _execute_reverse(
        self, 
        signal: TradingSignal, 
        position_context: PositionContext
    ) -> Dict[str, Any]:
        """
        执行反向操作：先平仓，再开反向仓
        
        例如：
        - reverse_to_long: 平空仓 → 开多仓
        - reverse_to_short: 平多仓 → 开空仓
        """
        logger.info(f"[{self.name}] 🔄 执行反向操作: {signal.direction}")
        
        # Step 1: 平掉当前持仓
        logger.info(f"[{self.name}] Step 1/2: 平掉当前{position_context.direction}仓")
        close_result = await self.paper_trader.close_position(
            reason=f"反向操作第一步: 平{position_context.direction}仓"
        )
        
        if not close_result.get('success'):
            return {
                "status": "error",
                "action": "reverse_close_failed",
                "reason": f"平仓失败: {close_result.get('error')}",
                "details": close_result
            }
        
        logger.info(f"[{self.name}] ✅ 平仓成功，PnL: ${close_result.get('pnl', 0):.2f}")
        
        # Step 2: 开反向仓
        new_direction = "long" if "long" in signal.direction else "short"
        logger.info(f"[{self.name}] Step 2/2: 开{new_direction}仓")
        
        # 重新获取账户余额
        account = await self.paper_trader.get_account()
        available_balance = account.get('available_balance', 0)
        amount_usdt = available_balance * signal.amount_percent
        
        logger.info(f"[{self.name}] 可用余额: {available_balance:.2f} USDT")
        logger.info(f"[{self.name}] 开仓金额: {amount_usdt:.2f} USDT")
        
        params = {
            "symbol": signal.symbol,
            "leverage": signal.leverage,
            "amount_usdt": amount_usdt,
            "tp_price": signal.take_profit_price,
            "sl_price": signal.stop_loss_price
        }
        
        if new_direction == "long":
            open_result = await self.paper_trader.open_long(**params)
        else:
            open_result = await self.paper_trader.open_short(**params)
        
        if not open_result.get('success'):
            return {
                "status": "error",
                "action": "reverse_open_failed",
                "reason": f"开{new_direction}仓失败: {open_result.get('error')}",
                "details": {
                    "close_result": close_result,
                    "open_result": open_result
                }
            }
        
        logger.info(f"[{self.name}] ✅ 反向操作成功!")
        
        return {
            "status": "success",
            "action": f"reversed_to_{new_direction}",
            "reason": f"成功反向: 平{position_context.direction} → 开{new_direction}",
            "details": {
                "close_result": close_result,
                "open_result": open_result,
                "close_pnl": close_result.get('pnl', 0)
            }
        }
```

---

## 🧪 测试计划

### 测试策略概述

**测试金字塔**:
```
        /\
       /  \
      / E2E \       ← End-to-End Tests (5个场景)
     /______\
    /        \
   / Integration \  ← Integration Tests (10个场景)
  /______________\
 /                \
/ Unit Tests       \ ← Unit Tests (30个测试用例)
/____________________\
```

### Phase 1: 单元测试 (Unit Tests)

#### 测试文件: `tests/unit/test_position_context.py`

```python
class TestPositionContext:
    """测试持仓上下文的构建和计算"""
    
    async def test_empty_position_context(self):
        """测试无持仓时的上下文"""
        context = await build_position_context(has_position=False)
        assert context.has_position == False
        assert context.can_add_position == False
        assert context.current_position_percent == 0
    
    async def test_long_position_context(self):
        """测试多仓上下文"""
        context = await build_position_context(
            has_position=True,
            direction="long",
            entry_price=90000,
            current_price=95000,
            margin_used=5000,
            total_equity=10000
        )
        assert context.has_position == True
        assert context.direction == "long"
        assert context.unrealized_pnl > 0  # 盈利
        assert context.current_position_percent == 0.5  # 50%仓位
    
    async def test_can_add_position_logic(self):
        """测试是否可追加的逻辑"""
        # 未满仓，可追加
        context1 = await build_position_context(
            margin_used=5000, total_equity=10000, max_position_percent=1.0
        )
        assert context1.can_add_position == True
        assert context1.max_additional_amount == 5000
        
        # 已满仓，不可追加
        context2 = await build_position_context(
            margin_used=10000, total_equity=10000, max_position_percent=1.0
        )
        assert context2.can_add_position == False
        assert context2.max_additional_amount == 0
```

#### 测试文件: `tests/unit/test_signal_consistency.py`

```python
class TestSignalConsistency:
    """测试信号与持仓的一致性检查"""
    
    async def test_open_with_existing_position_rejected(self):
        """测试：有持仓时不能直接开仓"""
        signal = create_signal(direction="long")
        context = create_position_context(has_position=True, direction="long")
        
        executor = TradeExecutor(...)
        check = executor._check_signal_consistency(signal, context)
        
        assert check['ok'] == False
        assert "已有" in check['reason']
    
    async def test_add_without_position_rejected(self):
        """测试：无持仓时不能追加"""
        signal = create_signal(direction="add_long")
        context = create_position_context(has_position=False)
        
        executor = TradeExecutor(...)
        check = executor._check_signal_consistency(signal, context)
        
        assert check['ok'] == False
        assert "无持仓" in check['reason']
    
    async def test_add_opposite_direction_rejected(self):
        """测试：不能追加反方向的仓"""
        signal = create_signal(direction="add_long")
        context = create_position_context(has_position=True, direction="short")
        
        executor = TradeExecutor(...)
        check = executor._check_signal_consistency(signal, context)
        
        assert check['ok'] == False
        assert "不能追加多仓" in check['reason']
```

#### 测试文件: `tests/unit/test_smart_executor.py`

```python
class TestSmartExecutor:
    """测试TradeExecutor的智能执行逻辑"""
    
    async def test_execute_hold_with_position(self):
        """测试：有持仓时的观望"""
        signal = create_signal(direction="hold")
        context = create_position_context(has_position=True)
        
        result = await executor.execute_signal(signal, context)
        
        assert result['status'] == 'success'
        assert result['action'] == 'hold'
        assert "维持" in result['reason']
    
    async def test_execute_add_long(self):
        """测试：追加多仓"""
        signal = create_signal(direction="add_long", amount_percent=0.3)
        context = create_position_context(
            has_position=True, 
            direction="long",
            can_add=True
        )
        
        result = await executor.execute_signal(signal, context)
        
        assert result['status'] == 'success'
        assert result['action'] == 'added_long'
    
    async def test_execute_reverse_to_short(self):
        """测试：反向操作（平多→开空）"""
        signal = create_signal(direction="reverse_to_short")
        context = create_position_context(has_position=True, direction="long")
        
        result = await executor.execute_signal(signal, context)
        
        assert result['status'] == 'success'
        assert result['action'] == 'reversed_to_short'
        assert 'close_result' in result['details']
        assert 'open_result' in result['details']
```

### Phase 2: 集成测试 (Integration Tests)

#### 测试文件: `tests/integration/test_position_aware_trading.py`

```python
class TestPositionAwareTrading:
    """测试完整的持仓感知交易流程"""
    
    async def test_scenario_1_no_position_to_long(self):
        """
        场景1: 无持仓 → 做多
        
        初始: 无持仓, 余额10000
        决策: 做多, 90%仓位
        预期: 开多仓成功
        """
        # Setup
        trader = await setup_paper_trader(balance=10000)
        
        # 模拟会议决策: 做多
        signal = create_signal(direction="long", amount_percent=0.9)
        position_context = await get_position_context(trader)
        
        # 执行
        executor = TradeExecutor(paper_trader=trader)
        result = await executor.execute_signal(signal, position_context)
        
        # 验证
        assert result['status'] == 'success'
        assert result['action'] == 'opened_long'
        
        # 验证持仓
        position = await trader.get_position()
        assert position['has_position'] == True
        assert position['direction'] == 'long'
    
    async def test_scenario_2_long_position_to_add_long(self):
        """
        场景2: 多仓(50%) → 追加做多
        
        初始: 多仓50%, 余额5000
        决策: 追加做多, 30%仓位
        预期: 追加成功, 总仓位80%
        """
        # Setup: 先开50%多仓
        trader = await setup_paper_trader(balance=10000)
        await trader.open_long(symbol="BTC", leverage=10, amount_usdt=5000)
        
        # 模拟会议决策: 追加做多
        signal = create_signal(direction="add_long", amount_percent=0.3)
        position_context = await get_position_context(trader)
        
        assert position_context.can_add_position == True
        
        # 执行
        executor = TradeExecutor(paper_trader=trader)
        result = await executor.execute_signal(signal, position_context)
        
        # 验证
        assert result['status'] == 'success'
        assert result['action'] == 'added_long'
    
    async def test_scenario_3_long_position_full_to_hold(self):
        """
        场景3: 多仓(100%满仓) → 继续看多 → 观望
        
        初始: 多仓100%
        决策: 继续看多（但Leader应判断为hold）
        预期: 维持持仓，不操作
        """
        # Setup: 满仓
        trader = await setup_paper_trader(balance=10000)
        await trader.open_long(symbol="BTC", leverage=10, amount_usdt=10000)
        
        # 模拟Leader决策: 检测到满仓，输出hold
        signal = create_signal(direction="hold")
        position_context = await get_position_context(trader)
        
        assert position_context.can_add_position == False
        
        # 执行
        executor = TradeExecutor(paper_trader=trader)
        result = await executor.execute_signal(signal, position_context)
        
        # 验证
        assert result['status'] == 'success'
        assert result['action'] == 'hold'
    
    async def test_scenario_4_long_position_to_reverse_short(self):
        """
        场景4: 多仓 → 做空信号 → 反向操作
        
        初始: 多仓
        决策: 做空（Leader应判断为reverse_to_short）
        预期: 先平多仓，再开空仓
        """
        # Setup: 多仓
        trader = await setup_paper_trader(balance=10000)
        await trader.open_long(
            symbol="BTC", 
            leverage=10, 
            amount_usdt=9000,
            tp_price=100000,
            sl_price=85000
        )
        
        # 模拟价格变化：涨了10%
        await trader._update_price(99000)
        
        # 模拟Leader决策: 反向做空
        signal = create_signal(
            direction="reverse_to_short",
            amount_percent=0.9,
            leverage=10
        )
        position_context = await get_position_context(trader)
        
        # 执行
        executor = TradeExecutor(paper_trader=trader)
        result = await executor.execute_signal(signal, position_context)
        
        # 验证
        assert result['status'] == 'success'
        assert result['action'] == 'reversed_to_short'
        assert 'close_pnl' in result['details']
        
        # 验证新持仓
        position = await trader.get_position()
        assert position['direction'] == 'short'
    
    async def test_scenario_5_long_position_to_hold_on_neutral(self):
        """
        场景5: 多仓 → 观望信号 → 维持持仓
        
        初始: 多仓
        决策: 观望（市场不明朗）
        预期: 维持持仓，不平仓
        """
        # Setup: 多仓
        trader = await setup_paper_trader(balance=10000)
        await trader.open_long(symbol="BTC", leverage=10, amount_usdt=9000)
        
        # 模拟Leader决策: 观望
        signal = create_signal(direction="hold")
        position_context = await get_position_context(trader)
        
        # 执行
        executor = TradeExecutor(paper_trader=trader)
        result = await executor.execute_signal(signal, position_context)
        
        # 验证
        assert result['status'] == 'success'
        assert result['action'] == 'hold'
        
        # 验证持仓未变
        position = await trader.get_position()
        assert position['has_position'] == True
        assert position['direction'] == 'long'
```

### Phase 3: 端到端测试 (E2E Tests)

#### 测试文件: `tests/e2e/test_full_trading_cycle.py`

```python
class TestFullTradingCycle:
    """测试完整的交易周期"""
    
    async def test_complete_lifecycle(self):
        """
        测试完整的生命周期：
        无持仓 → 开多 → 追加 → 反向 → 平仓
        """
        # Phase 1: 无持仓，开多
        result1 = await run_trading_meeting(
            market_sentiment="bullish",
            agents_mock_responses={
                "TechnicalAnalyst": "做多",
                "MacroEconomist": "做多",
                ...
            }
        )
        assert result1.direction == "long"
        
        # Phase 2: 价格上涨，追加多仓
        await simulate_price_change(+5%)
        result2 = await run_trading_meeting(
            market_sentiment="very_bullish",
            agents_mock_responses={...}
        )
        assert result2.direction == "add_long"
        
        # Phase 3: 市场反转，反向做空
        await simulate_price_change(-10%)
        result3 = await run_trading_meeting(
            market_sentiment="bearish",
            agents_mock_responses={...}
        )
        assert result3.direction == "reverse_to_short"
        
        # Phase 4: 获利平仓
        await simulate_price_change(-8%)
        result4 = await run_trading_meeting(
            market_sentiment="neutral",
            agents_mock_responses={...}
        )
        assert result4.direction == "close"
```

---

## 📅 实施计划

### Week 1: 基础架构 (5天)

**Day 1-2: PositionContext模型**
- [ ] 定义 `PositionContext` 数据类
- [ ] 实现 `_get_position_context()` 方法
- [ ] 单元测试 (test_position_context.py)

**Day 3: 持仓上下文传递**
- [ ] 修改 `TradingMeeting.run()` 注入position_context
- [ ] 格式化 `_format_position_context()` 方法
- [ ] 测试上下文传递

**Day 4-5: Agents Prompt增强**
- [ ] 更新所有Agent的prompt模板
- [ ] 添加持仓感知的决策指导
- [ ] 测试Agents是否正确理解持仓

### Week 2: Leader决策逻辑 (4天)

**Day 6-7: Leader决策矩阵**
- [ ] 实现决策矩阵逻辑
- [ ] Leader根据持仓智能选择direction类型
- [ ] 单元测试决策矩阵

**Day 8-9: TradingSignal扩展**
- [ ] 扩展direction类型（add_/reverse_/reduce_）
- [ ] 更新相关的验证逻辑
- [ ] 测试新的signal类型

### Week 3: TradeExecutor增强 (5天)

**Day 10-11: 信号一致性检查**
- [ ] 实现 `_check_signal_consistency()`
- [ ] 单元测试 (test_signal_consistency.py)

**Day 12-13: 智能执行策略**
- [ ] 实现 `_execute_add()`
- [ ] 实现 `_execute_reverse()`
- [ ] 实现 `_execute_reduce()`
- [ ] 单元测试 (test_smart_executor.py)

**Day 14: 集成测试**
- [ ] 编写集成测试 (test_position_aware_trading.py)
- [ ] 测试5个核心场景

### Week 4: 测试与优化 (4天)

**Day 15-16: E2E测试**
- [ ] 编写端到端测试
- [ ] 测试完整生命周期

**Day 17: 本地测试**
- [ ] Mock LLM responses运行完整测试
- [ ] 修复发现的bug

**Day 18: 服务器部署与验证**
- [ ] 部署到服务器
- [ ] 真实环境测试
- [ ] 监控和调优

---

## 📊 验收标准

### 功能验收

- [ ] **无持仓 → 做多** - 正确开多仓
- [ ] **多仓(50%) → 做多** - 追加多仓
- [ ] **多仓(100%) → 做多** - 维持，不操作
- [ ] **多仓 → 观望** - 维持持仓
- [ ] **多仓 → 做空** - 先平多，再开空
- [ ] **多仓 → 平仓** - 平掉多仓
- [ ] **空仓(50%) → 做空** - 追加空仓
- [ ] **空仓 → 做多** - 先平空，再开多

### 性能验收

- [ ] Agents讨论时能正确引用持仓状态
- [ ] Leader决策准确率 > 95%
- [ ] TradeExecutor无误执行率 = 100%
- [ ] 无重复交易bug
- [ ] 所有单元测试通过率 = 100%
- [ ] 集成测试通过率 = 100%

---

## 🎯 总结

这个设计方案实现了：

1. **三层架构**：
   - Layer 1: 持仓上下文传递
   - Layer 2: 智能决策生成
   - Layer 3: 智能执行引擎

2. **完整的测试金字塔**：
   - 30+ 单元测试
   - 10+ 集成测试
   - 5+ E2E测试

3. **18天实施计划**：
   - Week 1: 基础架构
   - Week 2: Leader决策
   - Week 3: 执行引擎
   - Week 4: 测试验证

**预期收益**：
- ✅ 彻底解决重复交易问题
- ✅ 支持追加/减仓/反向等复杂操作
- ✅ Agents决策更智能（基于持仓）
- ✅ 系统更稳定（100%测试覆盖）
