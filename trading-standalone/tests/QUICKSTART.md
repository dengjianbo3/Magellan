# 测试快速开始指南

## 🚀 5分钟快速开始

### 步骤1: 安装依赖（30秒）
```bash
cd /Users/dengjianbo/Documents/Magellan/trading-standalone/tests
pip install -r requirements.txt
```

### 步骤2: 运行测试（30秒）
```bash
./run_tests.sh
```

预期输出：
```
=== Trading System Test Suite ===

Configuration:
  - USE_REAL_LLM: false
  - USE_REAL_PRICE: false
  - TEST_TIMEOUT: 30s

Running all tests...
tests/unit/test_paper_trader.py::test_open_long_success PASSED
tests/unit/test_paper_trader.py::test_duplicate_trade_blocked PASSED
... (更多测试)
==================== 18 passed in 5.23s ====================

✅ All tests passed!
```

### 步骤3: 查看覆盖率（可选，1分钟）
```bash
./run_tests.sh --coverage
# 打开 htmlcov/index.html 查看详细报告
```

---

## 📚 测试框架说明

### 核心理念
✅ **无需外部依赖** - 不需要真实的LLM API、价格API、Redis  
✅ **快速运行** - 所有单元测试在5秒内完成  
✅ **高度可控** - 使用预定义数据，测试结果确定性  
✅ **场景丰富** - 覆盖牛市、熊市、止盈、止损等各种情况

### 已提供的测试工具

#### 1. Mock服务（避免真实API调用）
- `MockLLMService` - 返回预定义的Agent响应
- `MockPriceService` - 提供固定或序列价格
- `MockWebSearchService` - 返回预定义新闻

#### 2. 测试Fixtures（提供测试数据）
- 价格场景：牛市/熊市/止盈/止损等
- Agent响应：看涨/看跌/中性等
- 账户状态：空仓/多仓/空仓等

#### 3. 已完成测试（18个）
- ✅ 交易锁防止重复
- ✅ 止盈止损触发
- ✅ 账户余额计算
- ✅ 参数类型转换
- ✅ 更多...（见test_paper_trader.py）

---

## 💻 添加新测试

### 示例：测试空仓止损
```python
# tests/unit/test_paper_trader.py

@pytest.mark.unit
@pytest.mark.asyncio
async def test_short_stop_loss(clean_paper_trader, scenario_short_sl):
    """测试：空仓止损触发"""
    trader = clean_paper_trader
    
    # 开空仓
    with patch.object(trader, 'get_current_price', 
                     return_value=scenario_short_sl.get_price()):
        result = await trader.open_short("BTC-USDT-SWAP", 10, 2000.0)
        assert result["success"] is True
    
    # 价格上涨到止损点
    for _ in range(4):
        scenario_short_sl.advance()
    
    # 检查止损
    with patch.object(trader, 'get_current_price', 
                     return_value=scenario_short_sl.get_price()):
        trigger = await trader.check_tp_sl()
        
        assert trigger == "sl"
        assert trader._position is None  # 已平仓
```

### 运行新测试
```bash
pytest unit/test_paper_trader.py::test_short_stop_loss -v
```

---

## 🎯 重点测试场景

### 场景1: 防止重复交易（已完成✅）
```python
# 测试验证：
# 1. 第一次开仓成功
# 2. 第二次开仓被拒绝
# 3. 只扣了一次保证金
```

### 场景2: 持仓上下文感知（待创建）
```python
# 测试验证：
# 1. 无持仓时：显示"可以开新仓"
# 2. 有持仓时：显示"可以追加/持有/平仓"
# 3. 达到上限时：显示"无法追加"
```

### 场景3: 完整交易周期（待创建）
```python
# 测试验证：
# 1. T0: 首次分析 → 开多仓
# 2. T1-T3: 价格上涨，持有
# 3. T4: 触发止盈，自动平仓
# 4. T5: 第二次分析，无持仓状态
```

---

## 🔍 调试技巧

### 查看详细输出
```bash
pytest unit/test_paper_trader.py -v -s
```

### 只运行失败的测试
```bash
pytest --lf
```

### 进入调试器
```bash
pytest --pdb
```

### 查看覆盖率
```bash
pytest --cov=../../backend/services/report_orchestrator/app/core/trading --cov-report=term-missing
```

---

## 📊 当前进度

| 类别 | 已完成 | 计划 | 完成度 |
|------|--------|------|--------|
| 单元测试 | 18 | 50 | 36% |
| 集成测试 | 0 | 20 | 0% |
| 测试框架 | ✅ | ✅ | 100% |

---

## 🎉 下一步

### 立即可做：
1. ✅ 运行现有测试，验证系统稳定性
2. ✅ 添加更多单元测试（参考示例）
3. ✅ 创建集成测试（完整场景）

### 需要时间：
1. ⏳ 提高测试覆盖率到80%+
2. ⏳ 添加性能测试
3. ⏳ 添加压力测试

---

**现在就开始测试吧！** 🚀

```bash
cd trading-standalone/tests
./run_tests.sh
```
