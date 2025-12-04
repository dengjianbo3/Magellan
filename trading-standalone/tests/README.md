# Trading System Test Suite

本测试套件用于在本地环境下测试交易系统，无需依赖真实的LLM调用和新闻搜索API。

## 目录结构

```
tests/
├── unit/                    # 单元测试
│   ├── test_paper_trader.py         # Paper Trader核心逻辑测试
│   ├── test_trading_meeting.py      # Trading Meeting逻辑测试
│   ├── test_position_context.py     # 持仓上下文测试
│   └── test_trade_lock.py           # 交易锁测试
├── integration/             # 集成测试
│   ├── test_full_cycle.py           # 完整交易周期测试
│   ├── test_scenarios.py            # 多场景测试
│   └── test_tp_sl_trigger.py        # 止盈止损触发测试
├── fixtures/                # 测试数据
│   ├── market_data.py               # 模拟市场数据
│   ├── agent_responses.py           # 模拟Agent响应
│   └── price_scenarios.py           # 价格场景数据
├── mocks/                   # Mock对象
│   ├── mock_llm.py                  # Mock LLM服务
│   ├── mock_price_service.py        # Mock价格服务
│   └── mock_web_search.py           # Mock网络搜索
├── conftest.py              # Pytest配置
├── run_tests.sh             # 测试运行脚本
└── README.md                # 本文件
```

## 测试策略

### 1. Mock外部依赖
- **LLM调用**: 使用预定义的Agent响应，只在Leader最终决策时使用真实LLM（可配置）
- **价格服务**: 使用固定价格或价格序列
- **新闻搜索**: 返回预定义的新闻数据
- **时间控制**: 使用freezegun控制时间流动

### 2. 测试覆盖场景

#### 核心功能测试
- ✅ 交易锁防止重复开仓
- ✅ 持仓上下文正确传递
- ✅ 参数类型自动转换
- ✅ 止盈止损自动触发
- ✅ 账户余额正确计算
- ✅ 杠杆限制正确应用

#### 场景测试
1. **无持仓场景**
   - 首次分析 → 开多仓
   - 首次分析 → 开空仓
   - 首次分析 → 观望

2. **有持仓场景**
   - 有多仓 + 继续看多 → 追加
   - 有多仓 + 继续看多 → 持有
   - 有多仓 + 转看空 → 平仓
   - 有空仓 + 继续看空 → 追加
   - 有空仓 + 转看多 → 平仓

3. **风险控制场景**
   - 余额不足 → 拒绝开仓
   - 达到仓位上限 → 拒绝追加
   - 连续止损 → 触发冷却期

4. **止盈止损场景**
   - 多仓价格上涨到TP → 自动平仓止盈
   - 多仓价格下跌到SL → 自动平仓止损
   - 空仓价格下跌到TP → 自动平仓止盈
   - 空仓价格上涨到SL → 自动平仓止损

5. **异常场景**
   - LLM调用失败 → Fallback响应
   - 价格服务失败 → 错误处理
   - Redis连接失败 → 内存模式降级

## 运行测试

### 快速运行
```bash
# 运行所有测试
./run_tests.sh

# 运行特定类别
./run_tests.sh unit
./run_tests.sh integration

# 运行特定文件
./run_tests.sh unit/test_paper_trader.py

# 生成覆盖率报告
./run_tests.sh --coverage
```

### 详细运行
```bash
# 安装依赖
pip install pytest pytest-asyncio pytest-mock pytest-cov freezegun

# 运行测试（详细输出）
pytest -v

# 运行测试（显示print输出）
pytest -v -s

# 运行测试（生成HTML覆盖率报告）
pytest --cov=../backend/services/report_orchestrator/app/core/trading --cov-report=html

# 运行特定标记的测试
pytest -v -m "not slow"  # 跳过慢速测试
pytest -v -m "critical"  # 只运行关键测试
```

## 测试配置

### 环境变量
```bash
# 控制是否使用真实LLM（默认false）
export USE_REAL_LLM=false

# 控制是否使用真实价格API（默认false）
export USE_REAL_PRICE=false

# 测试超时设置（秒）
export TEST_TIMEOUT=30
```

### conftest.py配置
- 自动清理Redis测试数据
- 自动Mock外部服务
- 提供常用fixtures

## 示例输出

```
tests/unit/test_paper_trader.py::test_open_long_success PASSED
tests/unit/test_paper_trader.py::test_duplicate_trade_blocked PASSED
tests/unit/test_trading_meeting.py::test_position_context_no_position PASSED
tests/integration/test_scenarios.py::test_scenario_追加多仓 PASSED
tests/integration/test_tp_sl_trigger.py::test_long_take_profit PASSED

==================== 45 passed in 12.34s ====================
Coverage: 87%
```

## 持续集成

测试可以集成到CI/CD流程：
```yaml
# .github/workflows/test.yml
- name: Run Trading Tests
  run: |
    cd trading-standalone/tests
    pip install -r requirements.txt
    ./run_tests.sh --coverage
```

## 贡献指南

添加新测试时：
1. 在适当的目录创建测试文件（`test_*.py`）
2. 使用fixtures和mocks避免外部依赖
3. 添加清晰的文档字符串说明测试目的
4. 使用pytest标记分类测试（@pytest.mark.xxx）
5. 确保测试可独立运行和重复运行

## 调试技巧

```bash
# 进入pdb调试器
pytest --pdb

# 在第一个失败时停止
pytest -x

# 运行上次失败的测试
pytest --lf

# 详细输出所有print和log
pytest -v -s --log-cli-level=DEBUG
```

## 性能基准

预期测试运行时间：
- 单元测试: ~5秒（45个测试）
- 集成测试: ~15秒（20个测试）
- 全部测试: ~20秒

## 问题排查

### 测试失败常见原因
1. **Redis连接失败**: 确保Redis在运行或使用fake-redis
2. **端口占用**: 检查8000端口是否被占用
3. **依赖缺失**: 运行`pip install -r requirements.txt`
4. **路径问题**: 确保在tests目录下运行

### 获取帮助
查看测试日志：
```bash
pytest -v -s --log-cli-level=DEBUG > test_output.log 2>&1
```
