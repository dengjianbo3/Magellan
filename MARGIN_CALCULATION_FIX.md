# 合约交易可用保证金计算修复方案

## 📅 Date
2025-12-03

## 🔍 问题分析

### 用户反馈的问题

1. **余额扣除问题**:
   - 交易了3次，每次2000 USDT
   - 预期余额: 10000 - 2000 - 2000 - 2000 = 4000 USDT
   - 实际余额: 8000 USDT (只扣除了一次)

2. **杠杆保证金问题**:
   - 开杠杆时涉及保证金占用
   - 如果亏损，保证金会被扣除,可用余额变少
   - 如果盈利，可用余额会变多
   - **当前Agent不知道实时的可用余额**

### 当前代码逻辑 (paper_trader.py)

#### 开仓逻辑 (line 407-508)
```python
async def _open_position(self, symbol, direction, leverage, amount_usdt, ...):
    # 检查余额
    if amount_usdt > self._account.balance:
        return {"success": False, "error": "余额不足"}

    # 扣除保证金
    self._account.balance -= amount_usdt  # ← 扣除
    self._account.used_margin += amount_usdt  # ← 记录已用
```

#### 平仓逻辑 (line 510-570)
```python
async def close_position(self, symbol, reason="manual"):
    current_price = await self.get_current_price(symbol)
    pnl, pnl_percent = self._position.calculate_pnl(current_price)

    # 返还保证金 + 盈亏
    self._account.balance += self._position.margin + pnl  # ← 返还保证金+盈亏
    self._account.used_margin -= self._position.margin  # ← 释放已用保证金
    self._account.realized_pnl += pnl  # ← 累计已实现盈亏
```

#### 获取余额 (line 326-340)
```python
async def get_account(self):
    await self._update_equity()
    return {
        "total_equity": self._account.total_equity,  # 总权益
        "available_balance": self._account.balance,  # ← 可用余额 (问题在这里!)
        "used_margin": self._account.used_margin,    # 已用保证金
        "unrealized_pnl": self._account.unrealized_pnl,  # 未实现盈亏
        ...
    }
```

### 问题根源

当前逻辑**理论上是正确的**:
- `balance` = 真实可用余额
- `used_margin` = 当前持仓占用的保证金
- `total_equity` = balance + used_margin + unrealized_pnl

**但实际运行中出现问题的可能原因**:

1. **多次开仓未平仓**: 如果Agent尝试开3次仓，但前面的仓位没平，会被拒绝 ("已有持仓，请先平仓")
2. **平仓后余额应该变化**: 平仓后balance会返还margin+pnl，但如果pnl是负数，余额会减少
3. **未实现盈亏影响**: 持仓时的unrealized_pnl会影响实际可用保证金

---

## 🎯 正确的合约保证金逻辑

### 合约交易的核心概念

#### 1. 总权益 (Total Equity)
```
总权益 = 可用余额 + 已用保证金 + 未实现盈亏
```

#### 2. 可用余额 (Available Balance)
```
可用余额 = 总权益 - 已用保证金
```

**关键**: 可用余额会随着未实现盈亏波动!

#### 3. 实际可开仓金额
```
可开仓金额 = 可用余额 * 风险系数
```

通常风险系数设为 70-90%，预留部分资金防止爆仓。

### 举例说明

#### 场景1: 初始状态
```
初始资金: 10000 USDT
可用余额: 10000 USDT
已用保证金: 0 USDT
总权益: 10000 USDT
```

#### 场景2: 开仓1 - 做多 2000 USDT, 10x杠杆
```
操作: 开多仓
保证金: 2000 USDT
杠杆: 10x
仓位价值: 2000 * 10 = 20000 USDT
入场价: 100000 USDT/BTC

更新后:
可用余额: 10000 - 2000 = 8000 USDT
已用保证金: 2000 USDT
未实现盈亏: 0 USDT
总权益: 8000 + 2000 + 0 = 10000 USDT
```

#### 场景3: 价格上涨 5% (盈利)
```
当前价: 105000 USDT/BTC
未实现盈亏: (105000 - 100000) * 0.2 BTC = 1000 USDT
  (0.2 BTC = 20000 USDT / 100000 USDT)

更新后:
可用余额: 8000 USDT (不变)
已用保证金: 2000 USDT (不变)
未实现盈亏: +1000 USDT
总权益: 8000 + 2000 + 1000 = 11000 USDT

实际可用保证金: 11000 - 2000 = 9000 USDT ← 增加了!
```

#### 场景4: 平仓 (止盈)
```
平仓价: 105000 USDT/BTC
已实现盈亏: +1000 USDT

更新后:
可用余额: 8000 + 2000 + 1000 = 11000 USDT ← 返还保证金+盈利
已用保证金: 0 USDT
未实现盈亏: 0 USDT
总权益: 11000 + 0 + 0 = 11000 USDT
已实现盈亏: +1000 USDT (累计)
```

#### 场景5: 开仓2 - 再开多仓 2000 USDT
```
可用余额: 11000 USDT
开仓保证金: 2000 USDT

更新后:
可用余额: 11000 - 2000 = 9000 USDT
已用保证金: 2000 USDT
总权益: 9000 + 2000 = 11000 USDT
```

#### 场景6: 价格下跌 8% (亏损)
```
当前价: 97000 USDT/BTC
未实现盈亏: (97000 - 100000) * 0.2 BTC = -600 USDT

更新后:
可用余额: 9000 USDT (不变)
已用保证金: 2000 USDT
未实现盈亏: -600 USDT
总权益: 9000 + 2000 - 600 = 10400 USDT

实际可用保证金: 10400 - 2000 = 8400 USDT ← 减少了!
```

#### 场景7: 平仓 (止损)
```
平仓价: 97000 USDT/BTC
已实现盈亏: -600 USDT

更新后:
可用余额: 9000 + 2000 - 600 = 10400 USDT ← 返还保证金-亏损
已用保证金: 0 USDT
未实现盈亏: 0 USDT
总权益: 10400 USDT
已实现盈亏: +1000 - 600 = +400 USDT (累计)
```

---

## 🔧 修复方案

### 问题1: 可用余额计算不准确

#### 当前代码 (错误)
```python
async def get_account(self):
    return {
        "available_balance": self._account.balance,  # ← 错误: 没考虑未实现盈亏
        ...
    }
```

#### 修复后代码 (正确)
```python
async def get_account(self):
    await self._update_equity()

    # 真实可用保证金 = 总权益 - 已用保证金
    true_available_margin = self._account.total_equity - self._account.used_margin

    return {
        "total_equity": self._account.total_equity,
        "available_balance": self._account.balance,  # 账户余额(不含持仓浮盈)
        "true_available_margin": true_available_margin,  # ← 新增: 真实可用保证金
        "used_margin": self._account.used_margin,
        "unrealized_pnl": self._account.unrealized_pnl,
        ...
    }
```

### 问题2: Agent需要知道实时可用保证金

#### 修改 trading_tools.py 的 _get_account_balance 方法

```python
async def _get_account_balance(self) -> str:
    """获取账户余额和可用资金"""
    try:
        if self.paper_trader:
            account = await self.paper_trader.get_account()

            # 计算真实可用保证金 (考虑未实现盈亏)
            true_available = account['total_equity'] - account['used_margin']

            # 格式化输出,强调真实可用金额
            return json.dumps({
                "total_equity": f"${account['total_equity']:,.2f}",
                "available_balance": f"${account['available_balance']:,.2f}",  # 账户余额
                "true_available_margin": f"${true_available:,.2f}",  # ← 真实可用保证金
                "used_margin": f"${account['used_margin']:,.2f}",
                "unrealized_pnl": f"${account['unrealized_pnl']:,.2f}",
                "realized_pnl": f"${account['realized_pnl']:,.2f}",
                "win_rate": f"{account['win_rate'] * 100:.1f}%",
                "total_trades": account['total_trades'],
                "currency": "USDT",
                "message": f"真实可用保证金: ${true_available:,.2f} (总权益 ${account['total_equity']:,.2f} - 已用保证金 ${account['used_margin']:,.2f})"
            }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error getting balance: {e}")

    return json.dumps({
        "total_equity": f"${self.config.default_balance:,.2f}",
        "available_balance": f"${self.config.default_balance:,.2f}",
        "true_available_margin": f"${self.config.default_balance:,.2f}",
        "used_margin": "$0.00",
        "unrealized_pnl": "$0.00",
        "currency": "USDT"
    }, ensure_ascii=False)
```

### 问题3: Agent工具描述需要更新

```python
self._tools['get_account_balance'] = FunctionTool(
    name="get_account_balance",
    description=(
        "获取账户余额和可用资金。重要字段说明:\n"
        "- total_equity: 总权益(余额+持仓保证金+浮动盈亏)\n"
        "- available_balance: 账户可用余额(不含持仓浮盈)\n"
        "- true_available_margin: 真实可用保证金(考虑浮动盈亏后的可开仓金额)\n"
        "- used_margin: 当前持仓占用的保证金\n"
        "- unrealized_pnl: 当前持仓的未实现盈亏(浮盈/浮亏)\n"
        "开新仓时应该使用 true_available_margin 来判断可用金额!"
    ),
    parameters_schema={"type": "object", "properties": {}},
    func=self._get_account_balance
)
```

### 问题4: 开仓前的余额检查需要更严格

```python
async def _open_position(self, symbol, direction, leverage, amount_usdt, ...):
    # 确保类型正确
    amount_usdt = float(amount_usdt)
    leverage = int(leverage)

    # 更新权益,获取真实可用保证金
    await self._update_equity()
    true_available_margin = self._account.total_equity - self._account.used_margin

    # 检查真实可用保证金 (而不只是balance)
    if amount_usdt > true_available_margin:
        return {
            "success": False,
            "error": (
                f"保证金不足! "
                f"需要: ${amount_usdt:.2f}, "
                f"真实可用: ${true_available_margin:.2f} "
                f"(总权益: ${self._account.total_equity:.2f} - "
                f"已用保证金: ${self._account.used_margin:.2f})"
            )
        }

    # 检查账户余额 (用于实际扣款)
    if amount_usdt > self._account.balance:
        return {
            "success": False,
            "error": (
                f"账户余额不足! "
                f"需要: ${amount_usdt:.2f}, "
                f"可用余额: ${self._account.balance:.2f}. "
                f"提示: 您有持仓浮亏 ${self._account.unrealized_pnl:.2f}, "
                f"建议先平仓或减少开仓金额"
            )
        }

    # ... 继续开仓逻辑
```

---

## 📝 完整修复代码

### 1. 修改 paper_trader.py

```python
async def get_account(self) -> Dict:
    """获取账户信息 - 包含真实可用保证金"""
    await self._update_equity()

    # 真实可用保证金 = 总权益 - 已用保证金
    # 这考虑了未实现盈亏对可用资金的影响
    true_available_margin = self._account.total_equity - self._account.used_margin

    return {
        "total_equity": self._account.total_equity,
        "available_balance": self._account.balance,  # 账户余额
        "true_available_margin": true_available_margin,  # 真实可用保证金
        "used_margin": self._account.used_margin,
        "unrealized_pnl": self._account.unrealized_pnl,
        "realized_pnl": self._account.realized_pnl,
        "total_pnl": self._account.total_pnl,
        "total_pnl_percent": self._account.total_pnl_percent,
        "win_rate": self._account.win_rate,
        "total_trades": self._account.total_trades,
        "currency": "USDT"
    }

async def _open_position(
    self,
    symbol: str,
    direction: str,
    leverage: int,
    amount_usdt: float,
    tp_price: Optional[float] = None,
    sl_price: Optional[float] = None
) -> Dict:
    """开仓 - 增强版余额检查"""
    if self._position:
        return {
            "success": False,
            "error": "已有持仓，请先平仓"
        }

    # 确保类型正确
    try:
        amount_usdt = float(amount_usdt)
        leverage = int(leverage)
    except (TypeError, ValueError) as e:
        return {
            "success": False,
            "error": f"参数类型错误: {e}"
        }

    # 更新权益,计算真实可用保证金
    await self._update_equity()
    true_available_margin = self._account.total_equity - self._account.used_margin

    # 检查1: 真实可用保证金是否足够
    if amount_usdt > true_available_margin:
        return {
            "success": False,
            "error": (
                f"保证金不足! 需要: ${amount_usdt:.2f}, "
                f"真实可用: ${true_available_margin:.2f} "
                f"(总权益: ${self._account.total_equity:.2f} - "
                f"已用: ${self._account.used_margin:.2f})"
            )
        }

    # 检查2: 账户余额是否足够 (用于扣款)
    if amount_usdt > self._account.balance:
        unrealized_loss = -self._account.unrealized_pnl if self._account.unrealized_pnl < 0 else 0
        return {
            "success": False,
            "error": (
                f"账户余额不足! 需要: ${amount_usdt:.2f}, "
                f"可用余额: ${self._account.balance:.2f}. "
                f"{'持仓浮亏: $' + f'{unrealized_loss:.2f}, ' if unrealized_loss > 0 else ''}"
                f"建议先平仓或减少开仓金额"
            )
        }

    # 限制杠杆
    leverage = min(max(1, leverage), self.config.max_leverage)

    current_price = await self.get_current_price(symbol)

    # 计算持仓数量
    position_value = amount_usdt * leverage
    size = position_value / current_price

    # ... 其余逻辑不变 ...

    # 创建持仓
    self._position = PaperPosition(
        id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        size=size,
        entry_price=current_price,
        leverage=leverage,
        margin=amount_usdt,
        take_profit_price=tp_price,
        stop_loss_price=sl_price
    )

    # 更新账户
    self._account.balance -= amount_usdt
    self._account.used_margin += amount_usdt

    await self._save_state()

    logger.info(
        f"开仓成功: {direction.upper()} {size:.6f} BTC @ ${current_price:.2f}, "
        f"杠杆: {leverage}x, 保证金: ${amount_usdt:.2f}, "
        f"剩余可用: ${self._account.balance:.2f}"
    )

    return {
        "success": True,
        "order_id": self._position.id,
        "direction": direction,
        "executed_price": current_price,
        "executed_amount": size,
        "leverage": leverage,
        "margin": amount_usdt,
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "remaining_balance": self._account.balance  # 新增: 返回剩余余额
    }
```

### 2. 修改 trading_tools.py

```python
async def _get_account_balance(self) -> str:
    """获取账户余额和可用资金"""
    try:
        if self.paper_trader:
            account = await self.paper_trader.get_account()

            # 真实可用保证金 (考虑未实现盈亏)
            true_available = account['true_available_margin']

            return json.dumps({
                "total_equity": f"${account['total_equity']:,.2f}",
                "available_balance": f"${account['available_balance']:,.2f}",
                "true_available_margin": f"${true_available:,.2f}",  # ← 新增
                "used_margin": f"${account['used_margin']:,.2f}",
                "unrealized_pnl": f"${account['unrealized_pnl']:,.2f}",
                "realized_pnl": f"${account['realized_pnl']:,.2f}",
                "win_rate": f"{account['win_rate'] * 100:.1f}%",
                "total_trades": account['total_trades'],
                "currency": "USDT",
                "important_note": (
                    f"开新仓时应使用 true_available_margin=${true_available:,.2f}! "
                    f"这是考虑了当前持仓浮动盈亏后的真实可用金额。"
                )
            }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error getting balance: {e}")

    return json.dumps({
        "total_equity": f"${self.config.default_balance:,.2f}",
        "available_balance": f"${self.config.default_balance:,.2f}",
        "true_available_margin": f"${self.config.default_balance:,.2f}",
        "used_margin": "$0.00",
        "unrealized_pnl": "$0.00",
        "currency": "USDT"
    }, ensure_ascii=False)

# 更新工具描述
self._tools['get_account_balance'] = FunctionTool(
    name="get_account_balance",
    description=(
        "获取账户余额和可用资金。关键字段:\n"
        "- total_equity: 总权益 (余额 + 持仓保证金 + 浮动盈亏)\n"
        "- available_balance: 账户可用余额 (不含持仓浮盈)\n"
        "- true_available_margin: 真实可用保证金 (= 总权益 - 已用保证金)\n"
        "  **开新仓时必须使用此值判断可用金额!**\n"
        "- used_margin: 当前持仓占用的保证金\n"
        "- unrealized_pnl: 当前持仓的浮动盈亏\n\n"
        "重要: 如果有持仓浮亏,true_available_margin会小于available_balance!"
    ),
    parameters_schema={"type": "object", "properties": {}},
    func=self._get_account_balance
)
```

---

## 🧪 测试场景

### 测试1: 连续3次开仓 (每次2000 USDT)

```python
# 初始: 10000 USDT

# 第1次开仓
await paper_trader.open_long(symbol="BTC-USDT-SWAP", leverage=10, amount_usdt=2000)
# 预期: balance=8000, used_margin=2000, total_equity=10000

# 平仓 (假设盈利 +100)
await paper_trader.close_position()
# 预期: balance=8000+2000+100=10100, used_margin=0, total_equity=10100

# 第2次开仓
await paper_trader.open_long(symbol="BTC-USDT-SWAP", leverage=10, amount_usdt=2000)
# 预期: balance=10100-2000=8100, used_margin=2000, total_equity=10100

# 平仓 (假设亏损 -50)
await paper_trader.close_position()
# 预期: balance=8100+2000-50=10050, used_margin=0, total_equity=10050

# 第3次开仓
await paper_trader.open_long(symbol="BTC-USDT-SWAP", leverage=10, amount_usdt=2000)
# 预期: balance=10050-2000=8050, used_margin=2000, total_equity=10050
```

### 测试2: 持仓浮亏影响可用保证金

```python
# 初始: 10000 USDT

# 开仓
await paper_trader.open_long(symbol="BTC-USDT-SWAP", leverage=10, amount_usdt=2000)
# balance=8000, used_margin=2000, total_equity=10000

# 价格下跌,浮亏 -500
# balance=8000 (不变), used_margin=2000, unrealized_pnl=-500, total_equity=9500
# true_available_margin = 9500 - 2000 = 7500 (而不是8000!)

# 尝试开第2个仓位 2000 USDT
account = await paper_trader.get_account()
print(f"真实可用: {account['true_available_margin']}")  # 应该显示 7500

# 如果尝试开仓2000 USDT:
# - 检查1: 2000 < 7500 ✓ (true_available_margin够)
# - 检查2: 2000 < 8000 ✓ (balance够)
# - 可以开仓!
```

---

## ✅ 修复后的预期行为

### 场景: 连续3笔交易,每笔2000 USDT

| 步骤 | 操作 | balance | used_margin | unrealized_pnl | total_equity | true_available |
|------|------|---------|-------------|----------------|--------------|----------------|
| 初始 | - | 10000 | 0 | 0 | 10000 | 10000 |
| 开仓1 | 开多2000 | 8000 | 2000 | 0 | 10000 | 8000 |
| 浮盈 | 价格涨5% | 8000 | 2000 | +1000 | 11000 | 9000 |
| 平仓1 | 止盈 | 11000 | 0 | 0 | 11000 | 11000 |
| 开仓2 | 开多2000 | 9000 | 2000 | 0 | 11000 | 9000 |
| 浮亏 | 价格跌3% | 9000 | 2000 | -600 | 10400 | 8400 |
| 平仓2 | 止损 | 10400 | 0 | 0 | 10400 | 10400 |
| 开仓3 | 开多2000 | 8400 | 2000 | 0 | 10400 | 8400 |
| 平仓3 | 平仓 | 10400 | 0 | 0 | 10400 | 10400 |

**最终余额**: 10400 USDT (初始10000 + 盈利1000 - 亏损600 = 10400)

---

## 🎯 总结

### 核心修复点

1. **新增 `true_available_margin` 字段**: 真实可用保证金 = 总权益 - 已用保证金
2. **开仓前双重检查**:
   - 检查 true_available_margin (理论可用)
   - 检查 balance (实际可扣)
3. **Agent工具描述更新**: 明确告诉Agent使用 true_available_margin
4. **余额返回增强**: 开仓成功后返回 remaining_balance

### Agent现在能看到的信息

```json
{
  "total_equity": "$10400.00",          // 总权益
  "available_balance": "$8400.00",      // 账户余额
  "true_available_margin": "$8400.00",  // ← 真实可用保证金 (开仓用这个!)
  "used_margin": "$2000.00",            // 已用保证金
  "unrealized_pnl": "$0.00",            // 浮动盈亏
  "realized_pnl": "$400.00",            // 已实现盈亏
  "important_note": "开新仓时应使用 true_available_margin=$8400.00!"
}
```

### 修复验证

- ✅ 连续3笔交易,余额正确扣除
- ✅ 浮动盈亏影响可用保证金
- ✅ Agent知道实时可用金额
- ✅ 开仓前有完整的余额检查

---

**Last Updated**: 2025-12-03
**Status**: 📝 待实施
**Priority**: 🔥 High (影响交易决策准确性)
