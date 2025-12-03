# 交易风格设置 - 实现方案

**日期**: 2025-12-03
**需求**: 添加激进/保守交易风格设置,通过调整Agent Prompt来影响交易决策倾向

---

## 概述

通过环境变量`TRADING_STYLE`控制Agent的决策风格:
- `conservative` (默认): 保守模式 - 倾向于观望,只在高确定性机会时交易
- `aggressive`: 激进模式 - 更倾向于交易,愿意承担适度风险

---

## 实现方案

### 1. 环境变量配置

在 `.env` 或 `docker-compose.yml` 中添加:

```bash
# Trading Style Configuration
# Options: conservative | aggressive
# Default: conservative
TRADING_STYLE=conservative
```

**说明**:
- `conservative`: 保守风格,默认值
  - 要求更高的信号确定性
  - 倾向于等待明确的入场机会
  - 强调风险控制和资金保护
  - 对hold信号更宽容

- `aggressive`: 激进风格
  - 容忍较低的信号确定性
  - 更倾向于捕捉短期波动
  - 愿意承担适度风险以获取收益
  - 倾向于long/short而不是hold

---

### 2. Trading Meeting Config 修改

**文件**: `trading_meeting.py`

```python
@dataclass
class TradingMeetingConfig:
    # ... 现有字段 ...

    # 交易风格配置
    trading_style: str = field(
        default_factory=lambda: os.getenv("TRADING_STYLE", "conservative")
    )

    def __post_init__(self):
        """Validate configuration"""
        # 验证trading_style
        if self.trading_style not in ["conservative", "aggressive"]:
            logger.warning(f"Invalid TRADING_STYLE={self.trading_style}, defaulting to conservative")
            self.trading_style = "conservative"

        logger.info(f"TradingMeetingConfig initialized: style={self.trading_style}, "
                   f"max_leverage={self.max_leverage}, ...")
```

---

### 3. Agent Prompt 修改策略

#### 方式1: 在Agent Registry加载时注入风格指令 (推荐)

**文件**: `trading_agents.py`

```python
def create_trading_agents(toolkit=None, trading_style="conservative") -> List[Any]:
    """
    Create trading agents with specified trading style.

    Args:
        toolkit: TradingToolkit instance
        trading_style: "conservative" or "aggressive"
    """
    registry = get_registry()
    agents = []

    # 根据风格生成通用指令
    style_instruction = _get_style_instruction(trading_style)

    analysis_agent_ids = [
        "technical_analyst",
        "macro_economist",
        "sentiment_analyst",
        "risk_assessor",
        "quant_strategist",
    ]

    for agent_id in analysis_agent_ids:
        try:
            agent = registry.create_agent(agent_id, language='zh')

            # 为每个Agent添加风格化的系统指令
            _inject_style_prompt(agent, trading_style, style_instruction)

            agents.append(agent)
        except Exception as e:
            logger.error(f"Failed to load agent '{agent_id}': {e}")
            continue

    # Leader也需要风格指令
    try:
        leader = create_leader(language='zh')
        _inject_leader_style_prompt(leader, trading_style, style_instruction)
        agents.append(leader)
    except Exception as e:
        logger.error(f"Failed to create Leader: {e}")

    # ... 注册工具 ...

    return agents


def _get_style_instruction(trading_style: str) -> Dict[str, str]:
    """
    获取不同风格的指导原则

    Returns:
        Dict with 'general', 'conservative_bias', 'aggressive_bias' keys
    """
    if trading_style == "aggressive":
        return {
            "general": """
你是一位**激进型**交易分析师。你的投资哲学是:
- ✅ **积极捕捉机会**: 市场中存在许多可交易的机会,不应过度保守
- ✅ **适度风险容忍**: 愿意承担合理风险以获取收益,风险是回报的来源
- ✅ **行动导向**: 在信号出现时果断行动,而不是过度等待
- ⚠️ **风险管理**: 虽然激进,但仍需设置合理的止损和仓位控制
            """,
            "vote_bias": """
投票倾向指引:
- 当技术指标显示中性或轻微趋势时 → **倾向于 long/short** (捕捉早期信号)
- 当存在矛盾信号但主趋势清晰时 → **倾向于 long/short** (跟随主趋势)
- 只有在明确的震荡整理或极度不确定时 → 才选择 hold
- 信心度要求: 50%-60%即可考虑交易 (不需要80%+)
            """,
            "reasoning": """
分析时请强调:
- 机会成本: 观望也有成本,错过上涨/下跌也是损失
- 趋势延续: 趋势一旦形成,通常会持续一段时间
- 概率思维: 即使60%的胜率,通过风控也能获利
            """
        }
    else:  # conservative (default)
        return {
            "general": """
你是一位**保守型**交易分析师。你的投资哲学是:
- ✅ **资金安全第一**: 保护本金比获取收益更重要
- ✅ **高确定性机会**: 只在信号明确、风险可控时交易
- ✅ **耐心等待**: 宁可错过机会,也不做低质量交易
- ⚠️ **风险厌恶**: 当存在不确定性时,优先选择观望 (hold)
            """,
            "vote_bias": """
投票倾向指引:
- 当技术指标混杂或趋势不明确时 → **倾向于 hold** (等待更清晰信号)
- 当存在明显风险因素时 → **倾向于 hold** (优先规避风险)
- 只有在多个指标共振、确定性很高时 → 才选择 long/short
- 信心度要求: 75%+才考虑交易 (需要高确定性)
            """,
            "reasoning": """
分析时请强调:
- 风险因素: 详细列举可能的风险和不利情况
- 确定性评估: 当前信号的可靠性如何?
- 等待成本: 观望虽然错过收益,但避免了潜在损失
            """
        }


def _inject_style_prompt(agent: Agent, trading_style: str, instructions: Dict[str, str]):
    """
    为分析Agent注入风格化的系统指令

    修改Agent的system_prompt或添加额外的context
    """
    style_prompt = f"""
## 交易风格设定: {trading_style.upper()}

{instructions['general']}

{instructions['vote_bias']}

{instructions['reasoning']}

**重要**: 请在给出最终建议时,明确体现以上交易风格的特征。
"""

    # 如果Agent有system_prompt属性,追加风格指令
    if hasattr(agent, 'system_prompt'):
        agent.system_prompt = f"{agent.system_prompt}\n\n{style_prompt}"
    elif hasattr(agent, 'instructions'):
        agent.instructions = f"{agent.instructions}\n\n{style_prompt}"
    else:
        # 作为额外属性存储,在运行时注入
        agent._trading_style_prompt = style_prompt
        logger.info(f"Injected {trading_style} style prompt to {agent.name}")


def _inject_leader_style_prompt(leader: Agent, trading_style: str, instructions: Dict[str, str]):
    """
    为Leader注入决策风格指令

    Leader的指令需要更明确,因为它做最终决策
    """
    if trading_style == "aggressive":
        leader_specific = """
## Leader决策风格: 激进

作为最终决策者,你需要:
1. **积极解读信号**: 当专家意见分歧时,倾向于支持交易派(long/short)
2. **把握机会**: 3票long vs 1票hold → 果断选择long (多数服从)
3. **风险可承受**: 使用止损来控制风险,而不是放弃机会
4. **信心阈值**: 50-60%信心度即可执行交易

**决策优先级**:
1. 如果>=50%专家支持交易 → 选择交易方向 (long/short)
2. 只有在专家高度分歧或全部观望时 → 才选择hold
"""
    else:  # conservative
        leader_specific = """
## Leader决策风格: 保守

作为最终决策者,你需要:
1. **审慎评估**: 当专家意见分歧时,倾向于支持观望派(hold)
2. **等待共识**: 需要明确的多数支持(>=75%)才执行交易
3. **风险优先**: 有疑虑时,选择hold而不是冒险
4. **信心阈值**: 需要75%+信心度才执行交易

**决策优先级**:
1. 如果存在明显风险或意见分歧 → 选择hold
2. 只有在专家高度一致且信号清晰时 → 才选择交易 (long/short)
"""

    full_prompt = f"""
{instructions['general']}

{leader_specific}

**最终提醒**: 你的决策将直接执行,请确保符合{trading_style}风格的特征。
"""

    if hasattr(leader, 'system_prompt'):
        leader.system_prompt = f"{leader.system_prompt}\n\n{full_prompt}"
    elif hasattr(leader, 'instructions'):
        leader.instructions = f"{leader.instructions}\n\n{full_prompt}"
    else:
        leader._trading_style_prompt = full_prompt
        logger.info(f"Injected {trading_style} leader style prompt")
```

---

### 4. Trading Service 集成

**文件**: `trading_service.py` (或创建trading的入口)

```python
class TradingService:
    def __init__(self):
        self.config = TradingMeetingConfig()
        self.trading_style = self.config.trading_style

        # 创建带风格的agents
        self.agents = create_trading_agents(
            toolkit=self.toolkit,
            trading_style=self.trading_style
        )

        logger.info(f"TradingService initialized with style={self.trading_style}")
```

---

### 5. Docker Compose 配置示例

**文件**: `docker-compose.yml`

```yaml
services:
  trading-service:
    environment:
      # Trading Style: conservative (default) | aggressive
      - TRADING_STYLE=conservative

      # 当使用aggressive风格时,可以降低最小信心度
      - MIN_CONFIDENCE=50  # aggressive: 50, conservative: 75

      # 其他配置...
      - MAX_LEVERAGE=20
      - DEFAULT_POSITION_PERCENT=20
```

---

## 测试计划

### 1. 单元测试

```python
def test_conservative_style_prompt_injection():
    """测试保守风格的Prompt注入"""
    agents = create_trading_agents(trading_style="conservative")

    for agent in agents:
        if agent.name != "Leader":
            assert hasattr(agent, 'system_prompt') or hasattr(agent, '_trading_style_prompt')
            prompt = getattr(agent, 'system_prompt', '') or getattr(agent, '_trading_style_prompt', '')
            assert "保守型" in prompt or "资金安全第一" in prompt


def test_aggressive_style_prompt_injection():
    """测试激进风格的Prompt注入"""
    agents = create_trading_agents(trading_style="aggressive")

    leader = [a for a in agents if a.name == "Leader"][0]
    prompt = getattr(leader, 'system_prompt', '') or getattr(leader, '_trading_style_prompt', '')
    assert "激进" in prompt or "积极捕捉机会" in prompt
```

### 2. 集成测试

对比相同市场条件下,两种风格的决策差异:

| 场景 | Conservative | Aggressive |
|------|--------------|------------|
| RSI=55, 趋势不明 | hold (等待确认) | long/short (捕捉早期信号) |
| 3票long, 1票hold | 可能hold (意见分歧) | long (多数服从) |
| 信心度60% | hold (低于75%阈值) | long/short (符合50%阈值) |
| 市场震荡 | hold (风险规避) | short-term trades (波段操作) |

---

## 部署步骤

1. **修改代码** (按上述方案)
   - `trading_meeting.py` - 添加 trading_style 配置
   - `trading_agents.py` - 添加风格Prompt注入逻辑
   - `docker-compose.yml` - 添加 TRADING_STYLE 环境变量

2. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加交易风格设置(激进/保守模式)

   - 添加TRADING_STYLE环境变量 (conservative/aggressive)
   - 为所有Agent注入风格化Prompt
   - 调整Leader决策逻辑以符合风格
   - 更新docker-compose配置

   Conservative模式(默认):
   - 资金安全第一,高确定性交易
   - 信心度阈值75%+
   - 倾向hold,只在明确信号时交易

   Aggressive模式:
   - 积极捕捉机会,适度风险容忍
   - 信心度阈值50-60%
   - 倾向long/short,减少hold频率"

   git push origin exp
   ```

3. **远端部署**
   ```bash
   ssh root@45.76.159.149
   cd /root/trading-standalone
   git pull origin exp

   # 编辑.env设置风格
   nano .env  # 添加 TRADING_STYLE=aggressive

   # 重新构建和启动
   docker-compose build trading-service
   docker-compose up -d trading-service

   # 查看日志验证
   docker-compose logs -f trading-service | grep "style="
   ```

4. **验证风格生效**
   - 触发一次分析: `curl -X POST http://localhost:8000/api/trading/trigger`
   - 查看Agent日志,确认风格Prompt被使用
   - 对比多次决策,验证aggressive模式是否减少hold频率

---

## 监控指标

建议添加以下指标来评估风格效果:

```python
# Trading metrics by style
{
    "trading_style": "aggressive",
    "total_signals": 100,
    "signal_distribution": {
        "long": 45,
        "short": 35,
        "hold": 20  # aggressive应该更低
    },
    "avg_confidence": 62,  # aggressive通常更低
    "trade_frequency": 0.80,  # 80% signals are trades
}
```

---

## 注意事项

1. **风格不应改变风险管理**:
   - 无论什么风格,止损/止盈都必须设置
   - 最大仓位/杠杆限制仍然生效
   - 激进≠鲁莽,仍需风控

2. **风格是倾向性,不是绝对规则**:
   - Agent仍有判断自主权
   - 只是在模糊情况下影响决策倾向
   - 不会强制改变明确的信号

3. **需要回测验证**:
   - 收集足够数据后,对比两种风格的实际表现
   - 根据回测结果调整风格参数
   - 考虑在不同市场环境下动态切换风格

---

**实现完成**: 待开发
**预计工时**: 4-6小时
**优先级**: MEDIUM
**依赖**: 无

