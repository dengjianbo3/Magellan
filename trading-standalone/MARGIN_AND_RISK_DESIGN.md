# 保证金与风险管理系统设计

## 核心概念

### 1. 保证金类型

```
初始余额 (initial_balance) = $10,000
    │
    ├── 可用余额 (balance) = 未被占用的现金
    │       = initial_balance - used_margin + realized_pnl
    │
    ├── 已用保证金 (used_margin) = 当前持仓占用的保证金
    │
    ├── 未实现盈亏 (unrealized_pnl) = 持仓浮盈/浮亏
    │       = (current_price - entry_price) × size  (做多)
    │       = (entry_price - current_price) × size  (做空)
    │
    ├── 总权益 (total_equity) = balance + unrealized_pnl
    │
    └── 真实可用保证金 (true_available_margin)
            = total_equity - used_margin
            = balance + unrealized_pnl - used_margin
```

### 2. 关键公式

```python
# 真实可用保证金（考虑浮盈亏）
true_available_margin = total_equity - used_margin

# 示例1: 开仓后浮亏
initial_balance = $10,000
开仓使用 $5,000 保证金
balance = $5,000 (未占用)
used_margin = $5,000 (占用)
unrealized_pnl = -$500 (浮亏)
total_equity = $5,000 + (-$500) = $4,500
true_available_margin = $4,500 - $0 = $4,500 ❌ 错误!

# 正确计算:
total_equity = balance + unrealized_pnl = $5,000 + (-$500) = $4,500
# 但 used_margin 已经从 balance 扣除了
true_available_margin = total_equity - used_margin 这个公式需要验证

# 实际情况:
# balance = initial - used = $10,000 - $5,000 = $5,000
# unrealized_pnl = -$500
# total_equity = balance + used_margin + unrealized_pnl = $10,000 - $500 = $9,500
# true_available_margin = total_equity - used_margin = $9,500 - $5,000 = $4,500
```

### 3. 强平价格计算

```python
# 强平条件: 当亏损达到保证金的 80% 时强平
liquidation_loss = margin × 0.8

# 做多强平价:
liquidation_price_long = entry_price - (liquidation_loss / size)

# 做空强平价:
liquidation_price_short = entry_price + (liquidation_loss / size)

# 示例: 
# 入场价 $92,000, 保证金 $5,000, 杠杆 10x, size = $50,000 / $92,000 = 0.543 BTC
# liquidation_loss = $5,000 × 0.8 = $4,000
# 做多强平价 = $92,000 - ($4,000 / 0.543) = $92,000 - $7,366 = $84,634
```

### 4. 止损价格验证

**关键规则**: 止损价格必须在强平价格之前触发！

```python
# 做多:
# 止损价 > 强平价 ✅ (先止损，不会被强平)
# 止损价 < 强平价 ❌ (会先被强平！)

# 做空:
# 止损价 < 强平价 ✅ (先止损，不会被强平)
# 止损价 > 强平价 ❌ (会先被强平！)
```

---

## 决策矩阵（考虑保证金）

### 追加仓位条件

```python
MIN_ADD_AMOUNT = $10

# 可追加条件:
can_add = (
    true_available_margin >= MIN_ADD_AMOUNT AND
    current_margin_ratio < max_margin_ratio  # 可选：限制总仓位占比
)

# 追加金额计算:
add_amount = min(
    true_available_margin × amount_percent,  # 按比例
    true_available_margin - MIN_BUFFER       # 保留缓冲
)
```

### 完整场景矩阵

| # | 当前仓位 | 浮盈亏 | 真实可用 | 新信号 | 操作 |
|---|----------|--------|----------|--------|------|
| 1 | 无 | - | $10,000 | 做多 | 正常开多 |
| 2 | 多仓 | 浮盈$500 | $5,500 | 做多 | **可追加** |
| 3 | 多仓 | 浮亏$500 | $4,500 | 做多 | 可追加(金额受限) |
| 4 | 多仓 | 浮亏$4,900 | $100 | 做多 | ❌ 不可追加(接近强平) |
| 5 | 多仓 | 任意 | 任意 | 做空 | 平多→开空 |
| 6 | 空仓 | 浮盈$500 | $5,500 | 做空 | **可追加** |
| 7 | 空仓 | 浮亏$500 | $4,500 | 做空 | 可追加(金额受限) |
| 8 | 空仓 | 任意 | 任意 | 做多 | 平空→开多 |

---

## 风险控制

### 1. 开仓前检查

```python
async def pre_trade_check(direction, amount_usdt, leverage, tp_price, sl_price):
    """开仓前风险检查"""
    
    # 1. 检查真实可用保证金
    if amount_usdt > true_available_margin:
        return Error("保证金不足")
    
    # 2. 计算强平价格
    current_price = await get_current_price()
    size = (amount_usdt * leverage) / current_price
    liquidation_loss = amount_usdt * 0.8
    
    if direction == "long":
        liquidation_price = current_price - (liquidation_loss / size)
        # 3. 验证止损价 > 强平价
        if sl_price <= liquidation_price:
            return Error(f"止损价${sl_price}低于强平价${liquidation_price}，有爆仓风险！")
    else:
        liquidation_price = current_price + (liquidation_loss / size)
        if sl_price >= liquidation_price:
            return Error(f"止损价${sl_price}高于强平价${liquidation_price}，有爆仓风险！")
    
    return OK
```

### 2. 止损价格自动调整

```python
def calculate_safe_stop_loss(direction, entry_price, leverage, margin):
    """计算安全的止损价格（确保在强平之前触发）"""
    
    size = (margin * leverage) / entry_price
    liquidation_loss = margin * 0.8
    
    if direction == "long":
        liquidation_price = entry_price - (liquidation_loss / size)
        # 止损价 = 强平价 + 安全缓冲（5%）
        safe_sl = liquidation_price * 1.05
        # 确保止损不超过入场价的合理范围
        max_sl = entry_price * 0.97  # 最大3%止损
        return max(safe_sl, max_sl)
    else:
        liquidation_price = entry_price + (liquidation_loss / size)
        safe_sl = liquidation_price * 0.95
        min_sl = entry_price * 1.03
        return min(safe_sl, min_sl)
```

### 3. 杠杆与止损的关系

| 杠杆 | 最大亏损%(80%保证金) | 价格波动 | 建议止损% |
|------|---------------------|----------|-----------|
| 1x   | 80%                 | 80%      | 10-20%    |
| 5x   | 80%                 | 16%      | 5-10%     |
| 10x  | 80%                 | 8%       | 3-5%      |
| 20x  | 80%                 | 4%       | 2-3%      |

---

## 实现要点

1. **使用 `true_available_margin` 而非 `available_balance`**
2. **开仓前验证止损价 vs 强平价**
3. **追加仓位时考虑浮盈亏影响**
4. **保留安全缓冲，不要满仓**
5. **高杠杆时自动收紧止损**
