# OKX 模拟盘集成分析

## 核心优势

使用 OKX 模拟盘后，以下逻辑**不需要本地实现**：

| 功能 | 本地 PaperTrader | OKX 模拟盘 | 备注 |
|------|-----------------|-----------|------|
| 保证金计算 | `margin = amount_usdt` | `pos.margin` | 交易所精确计算 |
| 强平价格 | `calculate_liquidation_price()` | `pos.liqPx` | 交易所考虑所有因素 |
| 未实现盈亏 | `(price - entry) * size` | `pos.upl` | 交易所实时计算 |
| 可用保证金 | `total_equity - used_margin` | `availBal` | 交易所精确值 |
| 止盈止损 | 本地轮询 `check_tp_sl()` | **服务端自动** | 无需本地监控 |
| 资金费率 | ❌ 不支持 | ✅ 自动扣除 | 更真实 |
| 强制平仓 | 本地模拟 | **服务端自动** | 更真实 |

---

## 现有实现分析

### OKXClient (`okx_client.py`) - ✅ 基本完善

```python
# 获取账户余额
async def get_account_balance() -> AccountBalance:
    # 返回: total_equity, available_balance, used_margin, unrealized_pnl

# 获取持仓 - 交易所返回所有关键数据
async def get_current_position() -> Position:
    # 返回: direction, size, entry_price, leverage, margin, liqPx, upl

# 开仓
async def open_long/open_short(...):
    # 先设置杠杆，再下单，再设置TP/SL

# 平仓
async def close_position():
    # 调用 close-position API
```

### OKXTrader (`okx_trader.py`) - ⚠️ 需要完善

**缺失字段**:
1. `get_account()` 缺少 `true_available_margin`
2. `get_position()` 缺少 `liquidation_price`
3. `get_position()` 缺少 `position_percent`
4. 没有 `open_long()` / `open_short()` 分开的方法（只有 `open_position()`）

---

## 改进计划

### 1. 完善 OKXTrader.get_account()

```python
async def get_account(self) -> Dict:
    balance = await self._okx_client.get_account_balance()
    
    return {
        'total_equity': balance.total_equity,
        'available_balance': balance.available_balance,
        'true_available_margin': balance.available_balance,  # ← 新增：OKX直接返回可用保证金
        'used_margin': balance.used_margin,
        'unrealized_pnl': balance.unrealized_pnl,
        'realized_pnl': 0.0,  # 可从API获取
        'currency': 'USDT'
    }
```

### 2. 完善 OKXTrader.get_position()

```python
async def get_position(self, symbol: str = "BTC-USDT-SWAP") -> Optional[Dict]:
    pos = await self._okx_client.get_current_position(symbol)
    
    if not pos:
        return {'has_position': False}
    
    return {
        'has_position': True,
        'symbol': pos.symbol,
        'direction': pos.direction,
        'size': pos.size,
        'entry_price': pos.entry_price,
        'current_price': pos.current_price,
        'leverage': pos.leverage,
        'margin': pos.margin,
        'position_percent': (pos.margin / self.initial_balance * 100),  # ← 新增
        'unrealized_pnl': pos.unrealized_pnl,
        'unrealized_pnl_percent': pos.unrealized_pnl_percent,
        'take_profit_price': pos.take_profit_price,
        'stop_loss_price': pos.stop_loss_price,
        'liquidation_price': pos.liquidation_price,  # ← 新增：直接从交易所获取
        'opened_at': pos.opened_at.isoformat()
    }
```

### 3. 添加 open_long() / open_short() 方法

```python
async def open_long(self, symbol: str, leverage: int, amount_usdt: float,
                   tp_price: float = None, sl_price: float = None) -> Dict:
    """与 PaperTrader.open_long() 签名一致"""
    return await self.open_position(
        direction="long",
        symbol=symbol,
        leverage=leverage,
        amount_usdt=amount_usdt,
        tp_price=tp_price,
        sl_price=sl_price
    )

async def open_short(self, symbol: str, leverage: int, amount_usdt: float,
                    tp_price: float = None, sl_price: float = None) -> Dict:
    """与 PaperTrader.open_short() 签名一致"""
    return await self.open_position(
        direction="short",
        ...
    )
```

### 4. 简化 check_tp_sl()

```python
async def check_tp_sl(self) -> Optional[str]:
    """
    OKX 服务端会自动执行 TP/SL，本地只需同步状态
    """
    # 同步持仓状态
    await self._sync_position()
    
    # 如果持仓消失了，说明被 TP/SL 或强平
    if self._had_position and not self._position:
        # 查询最近交易确定原因
        trades = await self._okx_client.get_trade_history(limit=1)
        if trades:
            return "tp_or_sl"  # 无法精确区分
    
    return None
```

---

## OKX API 关键字段映射

### /api/v5/account/balance

| OKX 字段 | 含义 | 对应本地字段 |
|----------|------|-------------|
| `totalEq` | 总权益 | `total_equity` |
| `details[].availBal` | 可用余额 | `available_balance` / `true_available_margin` |
| `details[].frozenBal` | 冻结余额 | `used_margin` |

### /api/v5/account/positions

| OKX 字段 | 含义 | 对应本地字段 |
|----------|------|-------------|
| `pos` | 持仓数量 (正=多, 负=空) | `size` + `direction` |
| `avgPx` | 开仓均价 | `entry_price` |
| `markPx` | 标记价格 | `current_price` |
| `lever` | 杠杆 | `leverage` |
| `margin` | 保证金 | `margin` |
| `liqPx` | 强平价格 | `liquidation_price` |
| `upl` | 未实现盈亏 | `unrealized_pnl` |
| `uplRatio` | 未实现盈亏率 | `unrealized_pnl_percent` |

---

## 代码改动清单

1. **`okx_client.py`**
   - `get_current_position()` 添加 `liquidation_price` 到返回的 Position
   - `get_account_balance()` 获取 `frozenBal` 作为 `used_margin`

2. **`okx_trader.py`**
   - `get_account()` 添加 `true_available_margin`
   - `get_position()` 添加 `liquidation_price`, `position_percent`
   - 添加 `open_long()`, `open_short()` 方法（调用 `open_position`）
   - 简化 `check_tp_sl()` 逻辑

3. **`trading_meeting.py`**
   - `open_long_tool()`, `open_short_tool()` 不再需要本地计算强平价格
   - 简化 `validate_stop_loss()` - 可以使用交易所返回的 `liqPx`

---

## 切换使用 OKX 模拟盘

在 `.env` 中设置：

```bash
USE_OKX_TRADING=true
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase
OKX_DEMO_MODE=true  # 模拟盘
```

系统会自动切换到 OKXTrader：

```python
# trading_routes.py
def _use_okx_trading() -> bool:
    use_okx = os.getenv("USE_OKX_TRADING", "false").lower() == "true"
    return bool(okx_key and okx_secret and okx_pass and use_okx)
```
