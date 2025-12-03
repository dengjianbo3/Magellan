# Trading Logic 测试方案

## 测试目标

**不依赖真实市场数据**，通过模拟注入测试数据来验证交易逻辑的正确性。

## 测试架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        测试框架                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 模拟 Agent 投票结果 (绕过 LLM 调用)                         │
│     ↓                                                           │
│  2. 注入到 TradingMeeting 的 signal generation 阶段             │
│     ↓                                                           │
│  3. 验证 Leader Agent 的最终决策                                │
│     ↓                                                           │
│  4. 验证交易执行 (Paper Trader)                                 │
│     ↓                                                           │
│  5. 验证余额/仓位/止盈止损逻辑                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 测试场景设计

### 场景1: 开仓逻辑测试

#### 1.1 做多 (LONG)
- **模拟输入**:
  - TechnicalAnalyst: 建议做多, 信心度 85%
  - MacroEconomist: 建议做多, 信心度 75%
  - SentimentAnalyst: 建议做多, 信心度 80%
- **预期输出**:
  - 决策: `open_long`
  - 杠杆: 10-20x (高信心度)
  - 仓位: 20-30% 可用余额
  - 止盈: 5%
  - 止损: 2%

#### 1.2 做空 (SHORT)
- **模拟输入**:
  - TechnicalAnalyst: 建议做空, 信心度 78%
  - MacroEconomist: 建议做空, 信心度 82%
  - SentimentAnalyst: 建议做空, 信心度 75%
- **预期输出**:
  - 决策: `open_short`
  - 杠杆: 10-20x
  - 仓位: 20-30% 可用余额

#### 1.3 观望 (HOLD)
- **模拟输入**:
  - TechnicalAnalyst: 建议观望, 信心度 45%
  - MacroEconomist: 建议做多, 信心度 55%
  - SentimentAnalyst: 建议做空, 信心度 50%
- **预期输出**:
  - 决策: `hold`
  - 原因: 信心度低于阈值 (< 60%) 或意见分歧

#### 1.4 分歧场景
- **模拟输入**:
  - TechnicalAnalyst: 建议做多, 信心度 90%
  - MacroEconomist: 建议做空, 信心度 85%
  - SentimentAnalyst: 建议观望, 信心度 60%
- **预期输出**:
  - 决策: `hold` (意见严重分歧)
  - 或Leader需要更多轮次讨论

### 场景2: 止盈止损测试

#### 2.1 触发止盈
- **初始状态**:
  - 开多仓: 价格 $90,000, 仓位 2000 USDT, 10x杠杆
  - 止盈设置: 5%
- **价格变化**:
  - 价格涨到 $94,500 (+5%)
- **预期行为**:
  - 自动平仓
  - 盈利: ~1000 USDT (5% × 2000 × 10x)
  - 返还保证金: 2000 USDT

#### 2.2 触发止损
- **初始状态**:
  - 开多仓: 价格 $90,000, 仓位 2000 USDT, 10x杠杆
  - 止损设置: 2%
- **价格变化**:
  - 价格跌到 $88,200 (-2%)
- **预期行为**:
  - 自动平仓
  - 亏损: ~400 USDT (2% × 2000 × 10x)
  - 返还保证金: 1600 USDT

#### 2.3 未触发止盈止损
- **初始状态**:
  - 开多仓: 价格 $90,000
  - 止盈: 5%, 止损: 2%
- **价格变化**:
  - 价格在 $88,300 - $94,400 之间波动
- **预期行为**:
  - 持仓不动
  - 更新未实现盈亏
  - 更新 true_available_margin

### 场景3: 余额计算测试

#### 3.1 可用保证金计算
- **初始状态**:
  - 总权益: $10,000
  - 无持仓
- **开仓后**:
  - 开多仓: 2000 USDT保证金
  - 预期:
    - available_balance: $8,000 (现金)
    - used_margin: $2,000
    - true_available_margin: $8,000 (无浮动盈亏时)

#### 3.2 浮动盈亏影响
- **持仓状态**:
  - 入场价: $90,000, 保证金: 2000 USDT, 10x杠杆
  - 当前价: $91,800 (+2%)
- **预期余额**:
  - unrealized_pnl: +$400 (2% × 2000 × 10x)
  - total_equity: $10,400
  - used_margin: $2,000
  - true_available_margin: $8,400 (考虑浮动盈亏)

#### 3.3 连续交易余额扣除
- **场景**: 3笔连续交易，每笔2000 USDT
- **预期**:
  - 第1笔后: available_balance = $8,000
  - 第2笔后: available_balance = $6,000
  - 第3笔后: available_balance = $4,000

### 场景4: 风险控制测试

#### 4.1 杠杆限制
- **配置**: MAX_LEVERAGE = 20
- **测试**:
  - Agent建议25x杠杆
  - 预期: 系统限制为20x

#### 4.2 仓位限制
- **配置**:
  - MAX_POSITION_PERCENT = 30%
  - MIN_POSITION_PERCENT = 10%
- **测试**:
  - Agent建议开仓40%余额
  - 预期: 系统限制为30%
  - Agent建议开仓5%余额
  - 预期: 系统调整为10%

#### 4.3 余额不足拒绝开仓
- **场景**:
  - 可用余额: $1,000
  - Agent建议开仓: $2,000保证金
- **预期**:
  - 拒绝开仓
  - 错误信息: "Insufficient balance"

#### 4.4 已有持仓时拒绝开仓
- **场景**:
  - 已有持仓 (做多)
  - Agent建议开新仓 (做空)
- **预期**:
  - 拒绝开仓
  - 提示: "Close existing position first"

### 场景5: 信心度与杠杆映射

#### 5.1 高信心度 (>80%)
- **建议信心度**: 85%
- **预期杠杆范围**: 10-20x

#### 5.2 中信心度 (60-80%)
- **建议信心度**: 70%
- **预期杠杆范围**: 5-10x

#### 5.3 低信心度 (<60%)
- **建议信心度**: 55%
- **预期决策**: `hold` (低于最小信心度阈值60%)

## 测试工具设计

### test_trading_logic.py

```python
# 主测试脚本
- MockAgentVotes: 模拟 Agent 投票结果
- inject_mock_votes(): 注入到 TradingMeeting
- verify_decision(): 验证决策正确性
- verify_execution(): 验证执行正确性
- verify_balance(): 验证余额计算
```

### test_scenarios.json

```json
{
  "scenario_1_long": {
    "votes": [...],
    "expected_decision": "open_long",
    "expected_leverage": [10, 20],
    ...
  },
  ...
}
```

## 验证指标

### 1. 决策正确性
- [ ] Agent建议做多 → 系统执行做多
- [ ] Agent建议做空 → 系统执行做空
- [ ] Agent信心度低 → 系统观望

### 2. 执行正确性
- [ ] 杠杆在允许范围内
- [ ] 仓位在允许范围内
- [ ] 止盈止损正确设置

### 3. 余额正确性
- [ ] available_balance 正确扣除
- [ ] true_available_margin 考虑浮动盈亏
- [ ] used_margin 正确累加

### 4. 止盈止损正确性
- [ ] 价格达到止盈 → 自动平仓盈利
- [ ] 价格达到止损 → 自动平仓止损
- [ ] 价格未达到 → 持仓不动

### 5. 风险控制正确性
- [ ] 杠杆不超过 MAX_LEVERAGE
- [ ] 仓位在 MIN_POSITION_PERCENT - MAX_POSITION_PERCENT 范围内
- [ ] 余额不足时拒绝开仓
- [ ] 已有持仓时拒绝开新仓

## 实施步骤

1. ✅ 创建测试方案文档 (本文档)
2. ⏳ 创建测试脚本 `test_trading_logic.py`
3. ⏳ 创建测试场景配置 `test_scenarios.json`
4. ⏳ 运行所有测试场景
5. ⏳ 生成测试报告
6. ⏳ 修复发现的问题

## 测试执行

```bash
# 运行所有测试
python3 test_trading_logic.py

# 运行特定场景
python3 test_trading_logic.py --scenario long_position

# 生成详细报告
python3 test_trading_logic.py --verbose --report
```

## 预期输出

```
=== Trading Logic Test Report ===

Scenario 1: Open Long Position
  ✅ Decision: open_long
  ✅ Leverage: 15x (within range 10-20)
  ✅ Position: 20% of balance
  ✅ TP/SL: 5% / 2%

Scenario 2: Stop Loss Trigger
  ✅ Auto close at -2%
  ✅ Loss: -400 USDT
  ✅ Balance updated correctly

...

Total: 15/15 tests passed ✅
```

---

**创建日期**: 2025-12-03
**状态**: 测试方案设计完成，待实施
