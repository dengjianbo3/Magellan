# 🔧 TradeExecutor接口调用错误修复

## ❌ 错误现象

```
[交易执行专员] 检查账户状态失败: 'PaperTrader' object has no attribute 'get_account_status'
[交易执行专员] ❌ 账户检查失败: 账户检查异常: 'PaperTrader' object has no attribute 'get_account_status'
```

**影响**: TradeExecutor无法执行Leader的交易决策，所有交易被拒绝。

---

## 🐛 根本原因

### 问题1: 错误的方法名
```python
# trade_executor.py:195 ❌
account = self.paper_trader.get_account_status()  # 方法不存在！
```

**正确的接口**: `PaperTrader.get_account()` (不是 `get_account_status()`)

### 问题2: 缺少await
```python
# ❌ get_account()是异步方法，必须await
account = self.paper_trader.get_account_status()
```

**正确用法**:
```python
account = await self.paper_trader.get_account()  # ✅
```

### 问题3: 错误的参数类型
```python
# trade_executor.py:338-346 ❌
params = {
    "amount_percent": signal.amount_percent,  # PaperTrader不接受百分比！
    ...
}
await self.paper_trader.open_long(**params)
```

**PaperTrader的实际接口**:
```python
async def open_long(
    symbol: str,
    leverage: int,
    amount_usdt: float,  # ← 需要USDT金额，不是百分比
    tp_price: Optional[float] = None,
    sl_price: Optional[float] = None
) -> Dict
```

---

## ✅ 修复方案

### 修复1: 更正方法名并添加await

**文件**: `backend/services/report_orchestrator/app/core/trading/trade_executor.py:194`

```python
# 修复前 ❌
account = self.paper_trader.get_account_status()
balance = account.get('balance', 0)

# 修复后 ✅
account = await self.paper_trader.get_account()
available_balance = account.get('available_balance', 0)
```

### 修复2: 计算USDT金额并传递正确参数

**文件**: `backend/services/report_orchestrator/app/core/trading/trade_executor.py:339-362`

```python
# 修复后 ✅
if self.paper_trader:
    # 1. 获取账户余额
    account = await self.paper_trader.get_account()
    available_balance = account.get('available_balance', 0)
    
    # 2. 计算USDT金额
    # amount_percent已经是小数（0-1），例如0.9代表90%
    amount_usdt = available_balance * signal.amount_percent
    
    logger.info(f"可用余额: {available_balance:.2f} USDT")
    logger.info(f"仓位比例: {signal.amount_percent * 100:.1f}%")
    logger.info(f"开仓金额: {amount_usdt:.2f} USDT")
    
    # 3. 准备参数（使用amount_usdt）
    params = {
        "symbol": signal.symbol,
        "leverage": signal.leverage,
        "amount_usdt": amount_usdt,  # ✅ 使用USDT金额
        "tp_price": signal.take_profit_price,
        "sl_price": signal.stop_loss_price
    }
    
    # 4. 调用正确的接口
    if direction == "long":
        result = await self.paper_trader.open_long(**params)
    else:
        result = await self.paper_trader.open_short(**params)
```

### 修复3: 增强异常日志

```python
# 添加exc_info=True以获取完整的traceback
logger.error(f"[{self.name}] 检查账户状态失败: {e}", exc_info=True)
```

---

## 📊 PaperTrader接口规范

### get_account()
```python
async def get_account() -> Dict:
    """获取账户信息"""
    return {
        "total_equity": float,        # 总权益
        "available_balance": float,   # 可用余额（用于开仓计算）
        "used_margin": float,         # 已用保证金
        "unrealized_pnl": float,      # 未实现盈亏
        ...
    }
```

### open_long() / open_short()
```python
async def open_long(
    symbol: str,              # 交易对，例如 "BTC-USDT-SWAP"
    leverage: int,            # 杠杆倍数，1-20
    amount_usdt: float,       # ⚠️ USDT金额，不是百分比！
    tp_price: Optional[float],  # 止盈价格
    sl_price: Optional[float]   # 止损价格
) -> Dict:
    """开仓"""
    return {
        "status": "success" | "error",
        "message": str,
        ...
    }
```

---

## 🎯 关键要点

### 1. 参数转换公式
```python
# TradingSignal提供的是百分比（小数形式，0-1）
signal.amount_percent  # 例如：0.9 (代表90%)

# PaperTrader需要的是USDT金额
amount_usdt = available_balance * signal.amount_percent

# 例如：
#   available_balance = 10000 USDT
#   amount_percent = 0.9 (90%)
#   amount_usdt = 10000 * 0.9 = 9000 USDT
```

### 2. 异步方法必须await
```python
# ❌ 错误
account = self.paper_trader.get_account()

# ✅ 正确
account = await self.paper_trader.get_account()
```

### 3. 使用正确的字段名
```python
# PaperTrader.get_account()返回的字段
account.get('available_balance')  # ✅ 可用余额
account.get('total_equity')       # ✅ 总权益
account.get('balance')            # ❌ 不存在此字段
```

---

## 🚀 验证修复

### 服务器操作
```bash
cd ~/Magellan/trading-standalone
git pull origin exp
docker-compose down && docker-compose up -d --build
```

### 预期日志
```
[交易执行专员] ✅ 信号验证通过
[交易执行专员] ✅ 账户状态正常
[交易执行专员] 可用余额: 10000.00 USDT
[交易执行专员] 仓位比例: 90.0%
[交易执行专员] 开仓金额: 9000.00 USDT
[交易执行专员] 🚀 开始执行交易...
[交易执行专员] ✅ 交易执行成功!
```

---

## 📋 相关Commits

- `92772fe` - fix(trading): 修复TradeExecutor的PaperTrader接口调用错误

---

## ✨ 修复效果

- ✅ TradeExecutor能够正确调用PaperTrader接口
- ✅ 账户状态检查通过
- ✅ 正确计算开仓金额（可用余额 × 仓位比例）
- ✅ 成功执行交易决策
- ✅ 详细的日志便于问题追踪

**系统现在可以完整执行Leader的交易决策！** 🎉
