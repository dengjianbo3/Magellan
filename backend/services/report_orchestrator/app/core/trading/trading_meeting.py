"""
Trading Meeting

Specialized roundtable meeting for trading decisions.
Extends the base Meeting class with trading-specific phases and signal generation.
"""

import asyncio
import logging
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

from app.core.roundtable.meeting import Meeting


def _get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


from app.core.roundtable.agent import Agent
from app.models.trading_models import TradingSignal, AgentVote
from app.core.trading.retry_handler import (
    RetryHandler, RetryConfig, CircuitBreaker,
    CircuitBreakerOpenError, get_llm_retry_handler
)
from app.core.trading.agent_memory import (
    get_memory_store, AgentMemoryStore,
    record_agent_predictions, generate_trade_reflections
)
from app.core.trading.price_service import get_current_btc_price
from app.core.trading.position_context import PositionContext
# 🔧 TradeExecutorAgent已内联到TradeExecutorAgentWithTools，不再需要导入

logger = logging.getLogger(__name__)


def calculate_confidence_from_votes(votes: Dict[str, str], direction: str = None) -> int:
    """
    基于专家投票动态计算置信度

    计算规则:
    - 5票一致: 90%
    - 4票一致: 80%
    - 3票一致: 65%
    - 2票一致: 50%
    - 1票或更少: 30%

    Args:
        votes: 专家投票字典 {"agent_name": "long/short/hold"}
        direction: 目标方向，如果为None则使用多数方向

    Returns:
        int: 置信度 0-100
    """
    if not votes:
        logger.warning("[Confidence] 没有投票数据，使用最低置信度 30%")
        return 30

    # 🔧 FIX: 确保 votes 是字典类型
    if isinstance(votes, list):
        logger.warning(f"[Confidence] votes 是列表类型，转换为字典")
        # 尝试转换列表为字典（假设是 AgentVote 对象列表）
        try:
            votes = {v.agent_name: v.direction for v in votes if hasattr(v, 'agent_name') and hasattr(v, 'direction')}
        except Exception as e:
            logger.error(f"[Confidence] 无法转换 votes: {e}")
            return 30

    # 统计各方向票数
    long_count = sum(1 for v in votes.values() if v == 'long')
    short_count = sum(1 for v in votes.values() if v == 'short')
    hold_count = sum(1 for v in votes.values() if v == 'hold')
    total = len(votes)

    # 确定目标方向和票数
    if direction:
        if direction == 'long':
            target_count = long_count
        elif direction == 'short':
            target_count = short_count
        else:
            target_count = hold_count
    else:
        # 使用多数方向
        target_count = max(long_count, short_count, hold_count)

    # 基于票数计算置信度
    if target_count >= 5:
        confidence = 90
    elif target_count == 4:
        confidence = 80
    elif target_count == 3:
        confidence = 65
    elif target_count == 2:
        confidence = 50
    else:
        confidence = 30

    logger.info(f"[Confidence] 投票统计: {long_count}多/{short_count}空/{hold_count}观望, "
                f"目标方向={direction or '多数'}, 票数={target_count}, 置信度={confidence}%")

    return confidence


def calculate_leverage_from_confidence(confidence: int, max_leverage: int = 20) -> int:
    """
    基于置信度计算合理杠杆

    规则:
    - confidence >= 85: 10x (高信心)
    - confidence >= 75: 8x
    - confidence >= 65: 6x
    - confidence >= 55: 5x
    - confidence >= 45: 3x
    - confidence < 45: 2x (低信心)

    Args:
        confidence: 置信度 0-100
        max_leverage: 最大允许杠杆

    Returns:
        int: 推荐杠杆倍数
    """
    if confidence >= 85:
        leverage = 10
    elif confidence >= 75:
        leverage = 8
    elif confidence >= 65:
        leverage = 6
    elif confidence >= 55:
        leverage = 5
    elif confidence >= 45:
        leverage = 3
    else:
        leverage = 2

    # 限制在最大杠杆范围内
    leverage = min(leverage, max_leverage)

    logger.info(f"[Leverage] 置信度={confidence}% -> 推荐杠杆={leverage}x (上限={max_leverage}x)")

    return leverage


def calculate_amount_from_confidence(confidence: int) -> float:
    """
    基于置信度计算合理仓位比例

    规则:
    - confidence >= 85: 60% (高信心)
    - confidence >= 75: 50%
    - confidence >= 65: 40%
    - confidence >= 55: 30%
    - confidence < 55: 20% (低信心)

    Args:
        confidence: 置信度 0-100

    Returns:
        float: 仓位比例 0.0-1.0
    """
    if confidence >= 85:
        amount = 0.6
    elif confidence >= 75:
        amount = 0.5
    elif confidence >= 65:
        amount = 0.4
    elif confidence >= 55:
        amount = 0.3
    else:
        amount = 0.2

    logger.info(f"[Amount] 置信度={confidence}% -> 推荐仓位={amount*100:.0f}%")

    return amount


@dataclass
class TradingMeetingConfig:
    """Configuration for trading meeting - reads from environment variables"""
    symbol: str = field(default_factory=lambda: os.getenv("TRADING_SYMBOL", "BTC-USDT-SWAP"))
    max_leverage: int = field(default_factory=lambda: _get_env_int("MAX_LEVERAGE", 20))
    max_position_percent: float = field(default_factory=lambda: _get_env_float("MAX_POSITION_PERCENT", 30) / 100)  # Convert from % to decimal
    min_position_percent: float = field(default_factory=lambda: _get_env_float("MIN_POSITION_PERCENT", 10) / 100)  # Convert from % to decimal
    default_position_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_POSITION_PERCENT", 20) / 100)  # Convert from % to decimal
    min_confidence: int = field(default_factory=lambda: _get_env_int("MIN_CONFIDENCE", 60))
    max_rounds: int = 3
    require_risk_manager_approval: bool = True
    # 默认止盈止损百分比
    default_tp_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_TP_PERCENT", 5.0))
    default_sl_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_SL_PERCENT", 2.0))
    # 默认余额（用于计算，如果无法获取实际余额）
    default_balance: float = 10000.0
    # 回退价格（仅在无法获取实时价格时使用）
    fallback_price: float = 95000.0

    def __post_init__(self):
        """Log the configuration after initialization"""
        logger.info(f"TradingMeetingConfig initialized: max_leverage={self.max_leverage}, "
                   f"position_range={self.min_position_percent*100:.0f}%-{self.max_position_percent*100:.0f}%, "
                   f"min_confidence={self.min_confidence}%, tp/sl={self.default_tp_percent}%/{self.default_sl_percent}%")


class TradingMeeting(Meeting):
    """
    Specialized meeting for trading decisions.

    Phases:
    1. Market Analysis - Agents gather and analyze market data
    2. Signal Generation - Each agent provides their recommendation
    3. Risk Assessment - Risk manager evaluates proposed trade
    4. Consensus Building - Leader synthesizes opinions
    5. Execution Decision - Final decision and execution

    The meeting produces a TradingSignal that can be executed.
    """

    def __init__(
        self,
        agents: List[Agent],
        llm_service=None,
        config: Optional[TradingMeetingConfig] = None,
        on_message: Optional[Callable] = None,
        on_signal: Optional[Callable] = None,
        retry_handler: Optional[RetryHandler] = None,
        toolkit=None  # 🔧 NEW: Accept toolkit for TradeExecutor
    ):
        super().__init__(
            agents=agents,
            llm_service=llm_service,
            on_message=on_message
        )

        self.config = config or TradingMeetingConfig()
        self.on_message = on_message  # Store locally for easy access
        self.on_signal = on_signal
        self.retry_handler = retry_handler or get_llm_retry_handler()
        self.toolkit = toolkit  # 🔧 NEW: Store toolkit for TradeExecutor

        self._agent_votes: List[AgentVote] = []
        self._final_signal: Optional[TradingSignal] = None
        self._execution_result: Optional[Dict] = None
        self._memory_store: Optional[AgentMemoryStore] = None
        # Track executed tool calls (tool_name, params, result)
        self._last_executed_tools: List[Dict[str, Any]] = []

        # 🆕 记录 Agent 预测（用于平仓后反思）
        self._current_predictions: Dict[str, Dict[str, Any]] = {}
        self._current_trade_id: Optional[str] = None

        # 🆕 注册平仓回调（用于触发 Agent 反思）
        self._register_position_closed_callback()

    def _register_position_closed_callback(self):
        """注册平仓回调，用于触发 Agent 反思生成"""
        if not self.toolkit:
            logger.debug("No toolkit available, skipping position closed callback registration")
            return

        paper_trader = getattr(self.toolkit, 'paper_trader', None)
        if not paper_trader:
            logger.debug("No paper_trader in toolkit, skipping callback registration")
            return

        # 保存原有回调（如果有的话）
        original_callback = getattr(paper_trader, 'on_position_closed', None)

        async def on_position_closed_with_reflection(position, pnl, reason="manual"):
            """平仓回调：触发 Agent 反思生成"""
            logger.info(f"🔄 Position closed callback triggered: PnL=${pnl:.2f}, reason={reason}")

            try:
                # 获取交易 ID
                trade_id = getattr(position, 'id', None) or self._current_trade_id
                if not trade_id:
                    logger.warning("No trade_id available for reflection generation")
                    return

                # 计算持仓时长
                holding_hours = 0
                opened_at = getattr(position, 'opened_at', None)
                if opened_at:
                    if isinstance(opened_at, str):
                        opened_at = datetime.fromisoformat(opened_at)
                    holding_hours = (datetime.now() - opened_at).total_seconds() / 3600

                # 构建交易结果
                trade_result = {
                    'entry_price': getattr(position, 'entry_price', 0),
                    'exit_price': getattr(position, 'current_price', 0),
                    'pnl': pnl,
                    'direction': getattr(position, 'direction', 'long'),
                    'reason': reason,
                    'holding_hours': holding_hours
                }

                # 生成 Agent 反思
                logger.info(f"📝 Generating agent reflections for trade {trade_id}...")

                # 获取一个可用的 agent 作为 LLM 客户端（用于生成反思）
                llm_client = None
                if self.agents:
                    llm_client = self.agents[0]

                reflections = await generate_trade_reflections(
                    trade_id=trade_id,
                    trade_result=trade_result,
                    llm_client=llm_client
                )

                if reflections:
                    logger.info(f"✅ Generated {len(reflections)} agent reflections")
                    for r in reflections:
                        status = "正确" if r.prediction_was_correct else "错误"
                        logger.info(f"  - {r.agent_name}: 预测{status}, 教训: {r.lessons_learned[0] if r.lessons_learned else '无'}")
                else:
                    logger.warning(f"No reflections generated for trade {trade_id}")

            except Exception as e:
                logger.error(f"Error in position closed callback: {e}", exc_info=True)

            # 调用原有回调（如果有的话）
            if original_callback:
                try:
                    await original_callback(position, pnl, reason)
                except Exception as e:
                    logger.error(f"Error in original position closed callback: {e}")

        # 注册回调
        paper_trader.on_position_closed = on_position_closed_with_reflection
        logger.info("✅ Registered position closed callback for agent reflection")

    async def _record_agent_predictions_for_trade(self, market_price: float = 0.0):
        """
        记录所有 Agent 的预测（用于平仓后反思）

        在开仓成功后调用，将当前会议中所有 Agent 的投票记录到预测存储中。
        """
        try:
            # 获取当前持仓 ID 作为 trade_id
            trade_id = None
            if self.toolkit and hasattr(self.toolkit, 'paper_trader'):
                position = await self.toolkit.paper_trader.get_position()
                if position:
                    trade_id = getattr(position, 'id', None)

            if not trade_id:
                # 如果没有仓位 ID，使用时间戳生成一个
                trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.warning(f"No position ID found, using generated trade_id: {trade_id}")

            # 保存 trade_id 用于平仓时查找
            self._current_trade_id = trade_id

            # 从 _agent_votes 收集预测
            votes_dict = {}
            for vote in self._agent_votes:
                votes_dict[vote.agent_name] = {
                    'direction': vote.direction,
                    'confidence': vote.confidence,
                    'reasoning': vote.reasoning,
                    'key_factors': [],  # 可以从 reasoning 中提取
                    'market_snapshot': {}
                }

            if votes_dict:
                await record_agent_predictions(
                    trade_id=trade_id,
                    votes=votes_dict,
                    market_price=market_price
                )
                logger.info(f"📝 Recorded {len(votes_dict)} agent predictions for trade {trade_id}")
            else:
                logger.warning("No agent votes to record as predictions")

        except Exception as e:
            logger.error(f"Error recording agent predictions: {e}", exc_info=True)

    @property
    def final_signal(self) -> Optional[TradingSignal]:
        return self._final_signal

    @property
    def agent_votes(self) -> List[AgentVote]:
        return self._agent_votes

    async def run(self, context: Optional[str] = None) -> Optional[TradingSignal]:
        """
        Run the trading meeting.

        Args:
            context: Additional context for the meeting (e.g., trigger reason)

        Returns:
            TradingSignal if a trade decision is made, None otherwise
        """
        logger.info(f"Starting trading meeting for {self.config.symbol}")

        # 🆕 Step 0: 收集持仓上下文
        logger.info("[PositionContext] Collecting position context...")
        position_context = await self._get_position_context()
        logger.info(f"[PositionContext] Has position: {position_context.has_position}")
        if position_context.has_position and position_context.direction:
            logger.info(f"[PositionContext] Direction: {position_context.direction}, "
                       f"PnL: ${position_context.unrealized_pnl:.2f} ({position_context.unrealized_pnl_percent:+.2f}%), "
                       f"Can add: {position_context.can_add_position}")

        # Build the meeting agenda (with position context)
        agenda = self._build_agenda(context, position_context)

        # Add agenda as initial message
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content=agenda,
            message_type="agenda"
        )

        try:
            # Phase 1: Market Analysis (with position context)
            await self._run_market_analysis_phase(position_context)

            # Phase 2: Signal Generation (collect votes, with position context)
            await self._run_signal_generation_phase(position_context)

            # Phase 3: Risk Assessment (with position context)
            await self._run_risk_assessment_phase(position_context)

            # Phase 4: Consensus Building (Leader总结会议)
            _temp_signal = await self._run_consensus_phase(position_context)
            # 注：Phase 4不再产生最终signal，只是Leader的总结

            # Phase 5: Trade Execution (TradeExecutor分析并决策)
            # 🆕 NEW: TradeExecutor会分析Leader的总结并做出决策
            # 不管Leader说了什么，TradeExecutor都会运行
            await self._run_execution_phase(_temp_signal, position_context)
            
            # 最终signal来自TradeExecutor
            if self._final_signal:
                # Notify callback
                if self.on_signal:
                    await self.on_signal(self._final_signal)

            return self._final_signal

        except Exception as e:
            logger.error(f"Error in trading meeting: {e}")
            self._add_message(
                agent_id="system",
                agent_name="System",
                content=f"Meeting error occurred: {str(e)}",
                message_type="error"
            )
            return None

    def _build_agenda(self, context: Optional[str] = None, position_context: Optional[PositionContext] = None) -> str:
        """Build the meeting agenda with position context"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        reason = context or "定时分析"

        # 🆕 添加持仓状况到议程中
        position_summary = ""
        if position_context:
            if position_context.has_position and position_context.direction:
                pnl_emoji = "📈" if position_context.unrealized_pnl >= 0 else "📉"
                position_summary = f"""
## 💼 当前持仓状况 ⚠️ 重要！

- **持仓**: {position_context.direction.upper()} ({position_context.leverage}x 杠杆)
- **入场价**: ${position_context.entry_price:.2f}
- **当前价**: ${position_context.current_price:.2f}
- {pnl_emoji} **浮动盈亏**: ${position_context.unrealized_pnl:.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- **仓位占比**: {position_context.current_position_percent*100:.1f}% / {position_context.max_position_percent*100:.1f}%
- **状态**: {'✅ 可追加' if position_context.can_add_position else '❌ 已满仓'}
- **持仓时长**: {position_context.holding_duration_hours:.1f} 小时

⚠️ **请所有专家在分析时考虑当前持仓情况！**
"""
            else:
                position_summary = f"""
## 💼 当前持仓状况

- **持仓**: 无持仓
- **可用余额**: ${position_context.available_balance:.2f} USDT
- **总权益**: ${position_context.total_equity:.2f} USDT
- **状态**: ✅ 可自由开仓
"""

        return f"""# 交易分析会议

**时间**: {now}
**标的**: {self.config.symbol}
**触发原因**: {reason}
{position_summary}
## 会议议程

1. **市场分析阶段**: 各位专家获取并分析市场数据
2. **信号生成阶段**: 每位专家提出交易建议
3. **风险评估阶段**: 风险管理师评估交易风险
4. **共识形成阶段**: 主持人综合意见形成决策
5. **执行阶段**: 根据决策执行交易

## 交易参数限制
- 最大杠杆: {self.config.max_leverage}倍 (可选: 1,2,3,...,{self.config.max_leverage})
- 最大仓位: {self.config.max_position_percent*100:.0f}%资金
- 最低信心度要求: {self.config.min_confidence}%

## 杠杆选择参考
- 高信心度(>80%): {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}倍
- 中信心度(60-80%): {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}倍
- 低信心度(<60%): 1-{int(self.config.max_leverage * 0.25)}倍或观望

请各位专家开始分析。
"""

    async def _run_market_analysis_phase(self, position_context: PositionContext):
        """Phase 1: Market Analysis"""
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 1: Market Analysis\n\nTechnical Analyst, Macro Economist, and Sentiment Analyst, please begin your market analysis.",
            message_type="phase"
        )

        # Run analysis agents (using agent names from ReWOO agents)
        analysis_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst"]

        # Position context for all analysts
        position_hint = position_context.to_summary()

        # Neutral analysis prompt to avoid confirmation bias
        position_analysis_prompt = self._get_neutral_position_analysis_prompt(position_context)

        agent_prompts = {
            "TechnicalAnalyst": f"""Analyze the current technical situation for {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: You MUST use tools to get real-time data. Do NOT make up data!

**Tool Call Format** (must follow strictly):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

Execute the following steps:
1. [USE_TOOL: get_market_price(symbol="{self.config.symbol}")]
2. [USE_TOOL: get_klines(symbol="{self.config.symbol}", timeframe="4h", limit="100")]
3. [USE_TOOL: calculate_technical_indicators(symbol="{self.config.symbol}", timeframe="4h")]

Based on real data, provide **objective analysis**:
- Current price and 24h change
- Technical indicators: RSI, MACD, Bollinger Bands
- Trend analysis and key support/resistance levels
- Technical support for **LONG** position (strong/medium/weak/against)
- Technical support for **SHORT** position (strong/medium/weak/against)
- Your technical score and **independent** trading recommendation (unbiased by current position)""",

            "MacroEconomist": f"""Analyze the current macro-economic environment affecting {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: You MUST search for latest information. Do NOT rely solely on existing knowledge!

**Tool Call Format** (must follow strictly):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

Execute the following steps:
1. [USE_TOOL: tavily_search(query="Bitcoin BTC market news today price analysis")]
2. [USE_TOOL: tavily_search(query="cryptocurrency institutional investment outlook")]

Based on search results, provide **objective analysis**:
- Current market liquidity conditions
- Institutional investor movements
- USD index correlation with cryptocurrency
- Macro support for **LONG** position (strong/medium/weak/against)
- Macro support for **SHORT** position (strong/medium/weak/against)
- Your macro score and **independent** directional judgment (unbiased by current position)

**Note**: Focus on market data and investment analysis. Avoid sensitive topics.""",

            "SentimentAnalyst": f"""Analyze the current market sentiment for {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: You MUST fetch real-time data and search for latest information!

**Tool Call Format** (must follow strictly):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

Execute the following steps:
1. [USE_TOOL: get_fear_greed_index()]
2. [USE_TOOL: get_funding_rate(symbol="{self.config.symbol}")]
3. [USE_TOOL: tavily_search(query="Bitcoin BTC market sentiment social media")]

Based on real data, provide **objective analysis**:
- Fear & Greed Index value and interpretation
- Funding rate and long/short ratio
- Social media and news sentiment
- Sentiment support for **LONG** position (strong/medium/weak/against)
- Sentiment support for **SHORT** position (strong/medium/weak/against)
- Your sentiment score and **independent** directional judgment (unbiased by current position)""",

            "QuantStrategist": f"""Analyze quantitative data and statistical signals for {self.config.symbol}.

{position_hint}

{position_analysis_prompt}

**IMPORTANT**: You MUST use tools to get real-time data for quantitative analysis!

**Tool Call Format** (must follow strictly):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

Execute the following steps:
1. [USE_TOOL: get_market_price(symbol="{self.config.symbol}")]
2. [USE_TOOL: get_klines(symbol="{self.config.symbol}", timeframe="1h", limit="200")]
3. [USE_TOOL: calculate_technical_indicators(symbol="{self.config.symbol}", timeframe="1h")]

Based on real data, provide **objective** quantitative analysis:
- Price volatility and volume analysis
- Multi-timeframe trend consistency
- Momentum and trend indicator signals
- Quantitative support for **LONG** position (strong/medium/weak/against)
- Quantitative support for **SHORT** position (strong/medium/weak/against)
- Your quantitative score and **independent** directional judgment (unbiased by current position)"""
        }

        # Default prompt also requires tool usage
        default_prompt = f"""Analyze the current market situation for {self.config.symbol}.

{position_hint}

**IMPORTANT**: You MUST use tools to get real-time data. Do NOT make up data!

Use one of the following tools:
- `get_market_price` to get current price
- `tavily_search` to search for relevant news

Provide your analysis and views based on real data."""

        for agent_id in analysis_agents:
            agent = self._get_agent_by_id(agent_id)
            if agent:
                prompt = agent_prompts.get(agent_id, default_prompt)
                await self._run_agent_turn(agent, prompt)

    async def _run_signal_generation_phase(self, position_context: PositionContext):
        """
        Phase 2: Signal Generation

        🔧 重构: 使用结构化 JSON 输出，避免字符串匹配错误
        """
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 2: Signal Generation\n\nExperts, please provide your trading recommendations (long/short/hold).",
            message_type="phase"
        )

        # Generate decision options based on position status
        decision_options = self._get_decision_options_for_analysts(position_context)

        # JSON structured output prompt
        vote_prompt = f"""Based on the above analysis and real-time data you've collected, please provide your trading recommendation.

{position_context.to_summary()}

{decision_options}

**Note**: If you did not use tools to fetch data in the previous phase, please use relevant tools NOW to get the latest information before making your judgment!

⚠️ **IMPORTANT - Do NOT call decision tools**:
- You are in the "Signal Generation Phase" - only provide **text recommendations**
- **Do NOT** call any decision tools (open_long/open_short/hold/close_position)
- Only the TradeExecutor can execute trades in Phase 5

---

## 📋 Output Requirements

First explain your analysis reasoning, then output a JSON trading signal at the **END** of your response.

**JSON must be valid format, placed in a ```json code block:**

```json
{{
  "direction": "long",
  "confidence": 75,
  "leverage": 6,
  "take_profit_percent": 5.0,
  "stop_loss_percent": 2.0,
  "reasoning": "Brief reasoning with specific data references"
}}
```

**direction field options**:
- `"long"`: Go long / Buy
- `"short"`: Go short / Sell
- `"hold"`: Wait / No action
- `"add_long"`: Add to long position (when already long)
- `"add_short"`: Add to short position (when already short)
- `"close"`: Close position
- `"reverse"`: Reverse (close and open opposite)

**confidence and leverage correlation rules**:
- confidence >= 80: leverage should be in range {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}
- confidence 60-79: leverage should be in range {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}
- confidence < 60: leverage should be in range 1-{int(self.config.max_leverage * 0.25)}, or choose hold

**Important**: JSON must be at the END of your response and properly formatted!
"""

        vote_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst", "QuantStrategist"]
        for agent_id in vote_agents:
            agent = self._get_agent_by_id(agent_id)
            if agent:
                response = await self._run_agent_turn(agent, vote_prompt)
                vote = self._parse_vote_json(agent_id, agent.name, response)
                if vote:
                    self._agent_votes.append(vote)
                else:
                    # Fallback when JSON parsing fails
                    logger.warning(f"[{agent.name}] JSON parsing failed, attempting text parsing fallback")
                    vote = self._parse_vote_fallback(agent_id, agent.name, response)
                    if vote:
                        self._agent_votes.append(vote)

    async def _run_risk_assessment_phase(self, position_context: PositionContext):
        """Phase 3: Risk Assessment"""
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 3: Risk Assessment\n\nRisk Manager, please evaluate the trading risks.",
            message_type="phase"
        )

        # Summarize votes for risk manager
        votes_summary = self._summarize_votes()

        # Generate position risk assessment prompt
        risk_context = self._generate_risk_context(position_context)

        risk_agent = self._get_agent_by_id("RiskAssessor")
        if risk_agent:
            prompt = f"""Here are the expert voting results:

{votes_summary}

{position_context.to_summary()}

{risk_context}

Please evaluate the risk of this trade and decide whether to approve.
If approved, provide final position recommendations and TP/SL settings.
If not approved, explain your reasons.

⚠️ **IMPORTANT**:
- You only need to provide **text recommendations** for risk assessment
- **Do NOT** call any decision tools (open_long/open_short/hold/close_position)
- Only the TradeExecutor can execute trades in Phase 5
- Your responsibility is to assess risk, NOT to execute trades
"""
            await self._run_agent_turn(risk_agent, prompt)
    
    def _generate_risk_context(self, position_context: PositionContext) -> str:
        """
        Generate risk assessment context

        Help RiskAssessor evaluate current position risks
        """
        if not position_context.has_position:
            return """
## 🛡️ Risk Assessment Focus (No Position)

**Key Evaluation Points**:
1. Is the entry direction well-justified?
2. Does the leverage match the confidence level?
3. Are TP/SL settings reasonable?
4. Does the position size comply with risk management principles?
5. Is current market volatility suitable for opening a position?
"""

        # Has position
        direction = position_context.direction or "unknown"
        pnl = position_context.unrealized_pnl
        pnl_percent = position_context.unrealized_pnl_percent

        # Risk level
        if position_context.distance_to_liquidation_percent > 50:
            risk_level = "🟢 Safe"
        elif position_context.distance_to_liquidation_percent > 20:
            risk_level = "🟡 Warning"
        else:
            risk_level = "🔴 Danger"

        # TP/SL proximity warnings
        warnings = []
        if abs(position_context.distance_to_tp_percent) < 5:
            warnings.append(f"⚠️ Near Take Profit (only {abs(position_context.distance_to_tp_percent):.1f}%)")
        if abs(position_context.distance_to_sl_percent) < 5:
            warnings.append(f"🚨 Near Stop Loss (only {abs(position_context.distance_to_sl_percent):.1f}%)")

        warnings_text = "\n".join(warnings) if warnings else "No special warnings"

        return f"""
## 🛡️ Risk Assessment Focus (Has {direction.upper()} Position)

**Current Position Risk**:
- Risk Level: {risk_level}
- Distance to Liquidation: {position_context.distance_to_liquidation_percent:.1f}%
- Unrealized P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)
- Position Ratio: {position_context.current_position_percent*100:.1f}%

**Risk Warnings**:
{warnings_text}

**Evaluation Points** (based on expert recommendation type):

### If experts recommend "Continue {direction}/Add"
1. What is the P&L status of the current {direction} position? Is it healthy?
2. Will the total position exceed risk limits after adding?
3. Is there over-concentration in a single direction?
4. Has the holding duration been too long (currently {position_context.holding_duration_hours:.1f} hours)?

### If experts recommend "Close Position"
1. Is the closing rationale sufficient?
2. Is current P&L status suitable for closing?
3. Is this the right time to take profit/stop loss?

### If experts recommend "Reverse"
1. Is the reversal signal strong enough?
2. Is the current position profitable? What are the closing costs?
3. What is the risk of the new reversed position?
4. Is it worth bearing double transaction costs?

### If experts recommend "Hold"
1. What is the risk of continuing to hold the current position?
2. Should we actively close rather than passively wait?

Please provide comprehensive risk assessment and recommendations!
"""

    async def _run_consensus_phase(self, position_context: PositionContext) -> Optional[TradingSignal]:
        """
        Phase 4: Consensus Building - Leader Meeting Summary

        NEW ARCHITECTURE:
        - Leader only summarizes meeting discussions and expert opinions
        - No longer outputs structured trading decisions
        - Decisions made by TradeExecutor in Phase 5
        """
        self._add_message(
            agent_id="system",
            agent_name="System",
            content="## Phase 4: Consensus Building\n\nModerator, please summarize expert opinions and provide meeting conclusions.",
            message_type="phase"
        )

        # Use Leader for meeting summary
        leader = self._get_agent_by_id("Leader")
        if not leader:
            logger.error("Leader not found")
            return None

        # Generate position-aware decision guidance
        decision_guidance = self._generate_decision_guidance(position_context)

        # Leader as meeting moderator summary prompt
        prompt = f"""As the roundtable moderator, please comprehensively summarize the meeting discussions and expert opinions.

{position_context.to_summary()}

{decision_guidance}

## Expert Opinion Summary
You have heard analysis from the following experts:
- Technical Analyst (TechnicalAnalyst): Candlestick patterns, technical indicators analysis
- Macro Economist (MacroEconomist): Macro economy, monetary policy analysis
- Sentiment Analyst (SentimentAnalyst): Market sentiment, capital flow analysis
- Quant Strategist (QuantStrategist): Quantitative indicators, statistical analysis
- Risk Assessor (RiskAssessor): Risk assessment and recommendations

## Your Task

As moderator, please:

1. **Summarize Expert Consensus**:
   - How many experts are bullish? Bearish? Neutral?
   - What are the core reasons for each expert's opinion?
   - What are the agreements and disagreements among experts?

2. **Comprehensive Market Judgment**:
   - Based on all discussions, your overall view of the current market
   - Comprehensive evaluation of technical, fundamental, and sentiment aspects
   - Factors to consider given the current position status

3. **Risk and Opportunity Assessment**:
   - What are the main risks currently?
   - Where are the potential trading opportunities?
   - Recommendations for current position (if any)

4. **Provide Meeting Conclusions**:
   - Based on all analysis, what strategy should be adopted?
   - Recommended risk level and position size
   - How confident are you?

## 📋 Output Format

Please express your summary and recommendations freely, **no strict format required**.

You can express naturally, for example:

"Based on all expert opinions, I believe...
- TechnicalAnalyst and SentimentAnalyst are bullish because...
- However, MacroEconomist advises caution due to...
- Considering the current {('no position' if not position_context.has_position else f'{position_context.direction} position')} status...
I recommend... strategy because...
Suggested leverage is..., position size is..., my confidence is approximately...%"

⚠️ **Important Reminders**:
- ✅ Express your summary and recommendations in natural language
- ✅ Include expert opinions, your judgment, recommended strategy
- ✅ No need for markers like "【Final Decision】"
- ✅ Your summary will be passed to the Trade Executor, who will make the final decision based on your recommendations

Please begin your summary!
"""

        response = await self._run_agent_turn(leader, prompt)

        # Log meeting summary for monitoring
        vote_summary = self._get_vote_summary()
        logger.info(f"[Meeting Summary] Votes: {len(self._agent_votes)} collected, "
                   f"Vote breakdown: {vote_summary}")
        logger.info(f"[Leader Summary] {response[:200]}...")

        # 🆕 NEW: 不再在这里提取signal
        # Phase 5的TradeExecutor会根据这个总结做决策
        # 这里返回一个临时signal只是为了保持接口兼容
        return TradingSignal(
            direction="hold",  # 🔧 FIX: 使用有效值而不是"pending"
            symbol=self.config.symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=0.0,
            take_profit_price=0.0,
            stop_loss_price=0.0,
            confidence=0,
            reasoning=response[:500],
            agents_consensus=self._get_agents_consensus(),  # 🔧 FIX: 使用方法而不是属性
            timestamp=datetime.now()
        )
    
    def _generate_decision_guidance(self, position_context: PositionContext) -> str:
        """
        Generate decision guidance based on position status

        FIX: Use neutral decision guidance to avoid holding bias
        - Don't put "hold" as first option
        - Decision matrix treats all options equally
        - Emphasize decisions based on expert opinions, not position bias
        """
        if not position_context.has_position:
            # No position
            return """
## 💡 Decision Guidance (No Position)

**Decision Principle**: Based entirely on expert voting consensus, no preset directional bias.

**Decision Logic**:

| Expert Consensus | Recommended Action | Reason |
|-----------------|-------------------|--------|
| Majority bullish (≥3 votes) | Go Long | Upward market trend, expert consensus formed |
| Majority bearish (≥3 votes) | Go Short | Downward market trend, expert consensus formed |
| Split opinions | Hold | Direction unclear, wait for clearer signals |
| Unanimous hold | Hold | Timing not right |

**Auto-calculated Parameters**:
- Leverage/position determined by voting consensus strength (stronger consensus = higher leverage)
- TP/SL automatically adjusted based on leverage
"""

        # Has position
        direction = position_context.direction or "unknown"
        opposite = "short" if direction == "long" else "long"
        pnl = position_context.unrealized_pnl
        pnl_percent = position_context.unrealized_pnl_percent
        can_add = position_context.can_add_position

        # P&L status
        pnl_status = "profit" if pnl >= 0 else "loss"
        pnl_emoji = "📈" if pnl >= 0 else "📉"

        # Check if near TP/SL
        near_tp = abs(position_context.distance_to_tp_percent) < 5
        near_sl = abs(position_context.distance_to_sl_percent) < 5

        guidance = f"""
## 💡 Decision Guidance (Has {direction.upper()} Position)

**Current Position Status**: {pnl_emoji} {pnl_status} ${abs(pnl):.2f} ({pnl_percent:+.2f}%)
"""

        if near_tp:
            guidance += f"""
⚠️ **Near Take Profit**: Only {abs(position_context.distance_to_tp_percent):.1f}% from TP price
"""

        if near_sl:
            guidance += f"""
🚨 **Near Stop Loss**: Only {abs(position_context.distance_to_sl_percent):.1f}% from SL price
"""

        guidance += f"""
**Decision Principle**: Decide based on expert voting consensus, **do NOT favor any option due to existing position**.

**Decision Logic** (based on expert consensus, regardless of position P&L):

| Expert Consensus | Relation to Current {direction} | Recommended Action | Reason |
|-----------------|-------------------------------|-------------------|--------|
| Majority {opposite} | 🔴 Opposite | **Close or Reverse** | Experts see reversal, respect market signals |
| Majority {direction} | 🟢 Same | Maintain{' or Add' if can_add else ' (Max position)'} | Experts see same direction, trend may continue |
| Split opinions | ⚪ Unclear | Consider closing or hold | Direction unclear, reduce risk exposure |
| Unanimous hold | ⚪ Neutral | Hold but set tighter stop loss | Market may reverse |

⚠️ **Special Reminders**:
- If expert consensus is opposite to current {direction} position, **MUST consider closing or reversing**
- Do not avoid making changes just because currently in {pnl_status}
- Holding duration of {position_context.holding_duration_hours:.1f} hours should NOT become "sunk cost" affecting decisions

**Prohibited Behaviors**:
- ❌ Do not force-find reasons to hold just because already in {direction} position
- ❌ Do not ignore majority expert's reversal recommendations
"""

        return guidance

    def _get_neutral_position_analysis_prompt(self, position_context: PositionContext) -> str:
        """
        Generate neutral position analysis prompt

        Avoid confirmation bias: Don't ask "whether to support current position", but require objective market analysis
        """
        if not position_context.has_position:
            return """
⚠️ **Analysis Requirements**: Please provide objective analysis based on market data, without preset positions.
- Evaluate both long and short reasons simultaneously
- If market direction is unclear, honestly express uncertainty
- Your analysis should be independent of any preset preferences
"""

        direction = position_context.direction or "unknown"
        opposite = "short" if direction == "long" else "long"
        pnl_status = "profit" if position_context.unrealized_pnl >= 0 else "loss"

        return f"""
⚠️ **Objective Analysis Requirements** (Avoid Confirmation Bias):

Currently has {direction.upper()} position (in {pnl_status}), but please **do NOT** favor any direction because of this.

**Your analysis MUST answer these questions**:
1. Objectively, is the market trend **bullish**, **bearish**, or **ranging**?
2. If you had **NO position** right now, would you recommend long, short, or hold?
3. Does the current market condition contradict the existing {direction} position? If so, honestly point it out.
4. What signals support **reversing** (close {direction} and open {opposite})?

**Prohibited**:
- ❌ Do not lean towards {direction} just because already in {direction} position
- ❌ Do not avoid recommending close or reverse
- ❌ Do not use "can continue holding" to avoid giving clear judgment

**Encouraged**:
- ✅ If you see reversal signals, say it directly
- ✅ If market direction contradicts position, clearly recommend close/reverse
- ✅ Give clear directional judgment, don't be ambiguous
"""

    def _get_decision_options_for_analysts(self, position_context: PositionContext) -> str:
        """
        Generate decision options prompt for analysts

        FIX: Use neutral option list to avoid anchoring effect
        - Don't put "hold" as first option
        - Present all options equally
        - Emphasize decisions based on market analysis, not position status
        """
        if not position_context.has_position:
            return """
## 💡 Decision Options (No Position)

Based on **your professional analysis**, choose recommended direction (no preset preferences):

| Option | Applicable Situation |
|--------|---------------------|
| **Long** | Clear upward market trend with sufficient bullish signals |
| **Short** | Clear downward market trend with sufficient bearish signals |
| **Hold** | Market direction unclear, or risk/reward ratio unfavorable |

⚠️ **Make independent judgment**, do not change your analysis conclusion due to other experts' opinions.
"""

        # Has position
        direction = position_context.direction or "unknown"
        opposite = "short" if direction == "long" else "long"
        can_add_text = "Can add" if position_context.can_add_position else "Max position"

        return f"""
## 💡 Decision Options (Has {direction.upper()} Position)

Based on **your professional analysis**, choose recommended action (**do NOT favor any option due to existing position**):

| Option | Applicable Situation | Current Status |
|--------|---------------------|----------------|
| **Close** | Market shows reversal signals, or reached TP/SL | Execute immediately |
| **Reverse** | Clear market reversal, should close {direction} and open {opposite} | Execute immediately |
| **Maintain** | Market trend continues, keep current position | No action |
| **Add** | Market trend strengthens, can increase position | {can_add_text} |

**Current Position Status** (for reference only, should NOT affect your independent judgment):
- Direction: {direction.upper()} | P&L: ${position_context.unrealized_pnl:.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- Position: {position_context.current_position_percent*100:.1f}% | Duration: {position_context.holding_duration_hours:.1f} hours

⚠️ **Important**: If market analysis contradicts current position direction, **prioritize recommending close or reverse**, do not avoid giving reversal recommendations due to existing position!
"""

    def _get_vote_summary(self) -> str:
        """Get vote summary for logging"""
        if not self._agent_votes:
            return "no votes"
        directions = [v.direction for v in self._agent_votes]
        long_count = directions.count("long")
        short_count = directions.count("short")
        hold_count = directions.count("hold")
        return f"{long_count}L/{short_count}S/{hold_count}H"
    
    def _get_agents_consensus(self) -> Dict[str, str]:
        """
        从_agent_votes构建agents_consensus字典
        
        Returns:
            Dict[str, str]: {agent_name: direction}
        """
        consensus = {}
        for vote in self._agent_votes:
            consensus[vote.agent_name] = vote.direction
        return consensus

    async def _extract_signal_from_executed_tools(self, response: str) -> Optional[TradingSignal]:
        """
        Extract trading signal ONLY from actually executed tool calls.
        This prevents the bug where text mentions of 'open_long' would be mistaken for actual decisions.
        """
        try:

            # Check if any decision tools were actually executed
            decision_tools = ['open_long', 'open_short', 'hold']
            executed_decision = None
            executed_params = {}

            for tool_exec in self._last_executed_tools:
                tool_name = tool_exec.get('tool_name', '')
                if tool_name in decision_tools:
                    executed_decision = tool_name
                    executed_params = tool_exec.get('params', {})
                    logger.info(f"Found executed decision tool: {tool_name} with params: {executed_params}")
                    break

            # If no decision tool was executed, return None (no signal)
            if not executed_decision:
                logger.warning("No decision tool (open_long/open_short/hold) was executed by Leader")
                # Return a hold signal by default when no tool is called
                return await self._create_hold_signal(response, "Leader did not call any decision tool")

            # Map tool name to direction
            if executed_decision == 'open_long':
                direction = 'long'
            elif executed_decision == 'open_short':
                direction = 'short'
            else:  # 'hold'
                direction = 'hold'

            logger.info(f"Extracted direction from executed tool: {direction}")

            # Extract parameters from executed tool call
            leverage = 1
            amount_percent = self.config.default_position_percent
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent
            confidence = self.config.min_confidence

            # Parse leverage from params
            if 'leverage' in executed_params:
                try:
                    leverage = min(int(executed_params['leverage']), self.config.max_leverage)
                except (ValueError, TypeError):
                    pass

            # Parse amount from params
            if 'amount_usdt' in executed_params:
                try:
                    amount_usdt = float(executed_params['amount_usdt'])
                    # Clamp amount_percent between min and max
                    raw_percent = amount_usdt / self.config.default_balance
                    amount_percent = max(self.config.min_position_percent, min(raw_percent, self.config.max_position_percent))
                    logger.info(f"Position percent: {raw_percent*100:.1f}% -> clamped to {amount_percent*100:.1f}% (min={self.config.min_position_percent*100:.0f}%, max={self.config.max_position_percent*100:.0f}%)")
                except (ValueError, TypeError):
                    pass

            # Get current price for TP/SL calculation (now using await since method is async)
            try:
                current_price = await get_current_btc_price()
                logger.info(f"Got real-time BTC price: ${current_price:,.2f}")
            except Exception as e:
                logger.warning(f"Failed to get real-time price: {e}, using fallback")
                current_price = self.config.fallback_price

            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            elif direction == "short":
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            else:  # hold
                tp_price = current_price
                sl_price = current_price
                amount_percent = 0  # Hold means no position, so amount_percent must be 0

            consensus = {v.agent_name: v.direction for v in self._agent_votes}

            return TradingSignal(
                direction=direction,
                symbol=self.config.symbol,
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=current_price,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                confidence=confidence,
                reasoning=response[:500],
                agents_consensus=consensus
            )
        except Exception as e:
            logger.error(f"Error extracting signal from executed tools: {e}")
            return None

    async def _create_hold_signal(self, response: str, reason: str) -> TradingSignal:
        """Create a hold signal when Leader doesn't call any decision tool"""
        try:
            current_price = await get_current_btc_price()
            logger.info(f"Got real-time BTC price for hold signal: ${current_price:,.2f}")
        except Exception as e:
            logger.warning(f"Failed to get real-time price for hold signal: {e}, using fallback")
            current_price = self.config.fallback_price

        consensus = {v.agent_name: v.direction for v in self._agent_votes}

        return TradingSignal(
            direction="hold",
            symbol=self.config.symbol,
            leverage=1,
            amount_percent=0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=0,
            reasoning=f"{reason}. Response: {response[:300]}",
            agents_consensus=consensus
        )

    async def _extract_signal_from_text(self, response: str) -> Optional[TradingSignal]:
        """
        🔧 NEW: Extract trading signal from Leader's structured text output.
        
        Leader no longer calls tools, but outputs a structured decision in text format:
        
        【最终决策】
        - 决策: 做多/做空/观望/平仓/追加多仓/追加空仓
        - 标的: BTC-USDT-SWAP
        - 杠杆倍数: 5
        - 仓位比例: 30%
        - 止盈价格: 98000 USDT
        - 止损价格: 92000 USDT
        - 信心度: 75%
        - 决策理由: ...
        """
        try:
            import re
            
            logger.info("[SignalExtraction] Extracting signal from Leader's text output")
            
            # 🔧 CRITICAL FIX: MUST have 【最终决策】 marker
            # Without this marker, Leader is just discussing, not making final decision
            decision_pattern = r'【最终决策】(.*?)(?=\n\n|$)'
            match = re.search(decision_pattern, response, re.DOTALL)
            
            if not match:
                logger.warning("[SignalExtraction] ⚠️  No 【最终决策】 section found in response")
                logger.warning("[SignalExtraction] This indicates Leader is discussing, not making final decision")
                logger.warning("[SignalExtraction] Returning hold signal to avoid premature execution")
                # 🔧 FIX: Do NOT fallback to parsing the entire response
                # If there's no 【最终决策】 marker, it means Leader is just discussing
                # Return a hold signal to prevent premature execution
                return await self._create_hold_signal(
                    response, 
                    "Leader没有输出【最终决策】标记，可能还在讨论中"
                )
            
            decision_text = match.group(1)
            logger.info(f"[SignalExtraction] ✅ Found 【最终决策】 section")
            logger.info(f"[SignalExtraction] Decision text: {decision_text[:200]}...")
            
            # Extract fields using regex
            def extract_field(pattern, text, default=None):
                match = re.search(pattern, text, re.IGNORECASE)
                return match.group(1).strip() if match else default
            
            # 决策 (决策类型)
            decision_type = extract_field(r'-\s*决策\s*[:：]\s*([^\n]+)', decision_text)
            logger.info(f"[SignalExtraction] decision_type: {decision_type}")
            
            # 标的
            symbol = extract_field(r'-\s*标的\s*[:：]\s*([^\n]+)', decision_text, self.config.symbol)
            
            # 杠杆倍数
            leverage_str = extract_field(r'-\s*杠杆倍数\s*[:：]\s*(\d+)', decision_text, "1")
            leverage = int(leverage_str)
            
            # 仓位比例
            position_str = extract_field(r'-\s*仓位比例\s*[:：]\s*(\d+)', decision_text, "0")
            amount_percent = float(position_str)
            
            # 止盈价格
            tp_str = extract_field(r'-\s*止盈价格\s*[:：]\s*([\d.]+)', decision_text, "0")
            take_profit_price = float(tp_str)
            
            # 止损价格
            sl_str = extract_field(r'-\s*止损价格\s*[:：]\s*([\d.]+)', decision_text, "0")
            stop_loss_price = float(sl_str)
            
            # 信心度
            confidence_str = extract_field(r'-\s*信心度\s*[:：]\s*(\d+)', decision_text, "0")
            confidence = int(confidence_str)
            
            # 决策理由
            reasoning = extract_field(r'-\s*决策理由\s*[:：]\s*([^\n]+)', decision_text, "")
            
            # Map decision_type to direction
            direction = "hold"  # default
            if decision_type:
                dt_lower = decision_type.lower()
                if "做多" in dt_lower or "开多" in dt_lower:
                    direction = "long"
                elif "做空" in dt_lower or "开空" in dt_lower:
                    direction = "short"
                elif "追加多" in dt_lower:
                    direction = "long"  # 追加也是long
                elif "追加空" in dt_lower:
                    direction = "short"
                elif "平仓" in dt_lower:
                    direction = "hold"  # 🔧 FIX: TradingSignal不支持"close"，平仓后使用hold
                elif "观望" in dt_lower or "持有" in dt_lower:
                    direction = "hold"
            
            logger.info(f"[SignalExtraction] Parsed direction: {direction}, leverage: {leverage}, "
                       f"position: {amount_percent}%, confidence: {confidence}%")
            
            # 🔧 FIX: Convert amount_percent from percentage to decimal (e.g., 90% → 0.9)
            # TradingSignal expects amount_percent in range [0, 1], not [0, 100]
            amount_percent_decimal = amount_percent / 100.0
            logger.info(f"[SignalExtraction] Converted amount_percent: {amount_percent}% → {amount_percent_decimal}")
            
            # Get current price
            try:
                from app.core.trading.trading_tools import get_current_btc_price
                current_price = await get_current_btc_price()
                logger.info(f"[SignalExtraction] Current BTC price: ${current_price:,.2f}")
            except Exception as e:
                logger.warning(f"[SignalExtraction] Failed to get real-time price: {e}, using fallback")
                current_price = self.config.fallback_price
            
            # Build consensus dict
            consensus = {v.agent_name: v.direction for v in self._agent_votes}
            
            # Create signal
            signal = TradingSignal(
                direction=direction,
                symbol=symbol,
                leverage=leverage,
                amount_percent=amount_percent_decimal,  # Use decimal value
                entry_price=current_price,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                confidence=confidence,
                reasoning=reasoning or response[:500],
                agents_consensus=consensus
            )
            
            logger.info(f"[SignalExtraction] ✅ Signal extracted: {signal}")
            return signal
            
        except Exception as e:
            logger.error(f"[SignalExtraction] Error extracting signal from text: {e}", exc_info=True)
            return None

    async def _get_position_context(self) -> PositionContext:
        """
        🆕 获取完整的持仓上下文
        
        收集所有持仓、账户、风险相关的信息，用于：
        1. 注入到Agents的prompt中
        2. 传递给Leader做决策
        3. 传递给TradeExecutor做执行
        
        Returns:
            PositionContext: 完整的持仓上下文对象
        """
        try:
            # 检查toolkit和paper_trader是否存在
            if not hasattr(self, 'toolkit') or not self.toolkit:
                logger.error("[PositionContext] No toolkit available")
                raise AttributeError("toolkit not available")
            
            if not hasattr(self.toolkit, 'paper_trader') or not self.toolkit.paper_trader:
                logger.error("[PositionContext] No paper_trader in toolkit")
                raise AttributeError("paper_trader not available")
            
            # 获取当前持仓
            position = await self.toolkit.paper_trader.get_position()
            if position is None:
                logger.warning("[PositionContext] get_position() returned None, using default empty position")
                position = {'has_position': False}
            
            has_position = position.get('has_position', False)
            
            # 获取账户信息
            account = await self.toolkit.paper_trader.get_account()
            if account is None:
                logger.warning("[PositionContext] get_account() returned None, using default balance")
                account = {
                    'available_balance': self.config.default_balance,
                    'total_equity': self.config.default_balance,
                    'used_margin': 0
                }
            
            # 如果无持仓，返回简化的context
            if not has_position:
                return PositionContext(
                    has_position=False,
                    available_balance=account.get('available_balance', self.config.default_balance),
                    total_equity=account.get('total_equity', self.config.default_balance),
                    used_margin=account.get('used_margin', 0),
                    max_position_percent=self.config.max_position_percent,
                    can_add_position=False
                )
            
            # 有持仓，收集详细信息
            # 🔧 FIX: get_position() 返回的是平面字典，不是嵌套在 'position' 键下
            # 直接从 position 字典获取数据，而不是 position.get('position', {})
            current_position = position  # position 本身就是持仓详情
            
            direction = position.get('direction', '')
            entry_price = position.get('entry_price', 0)
            current_price = position.get('current_price', 0)
            size = position.get('size', 0)
            leverage = position.get('leverage', 1)
            margin_used = position.get('margin', 0)
            unrealized_pnl = position.get('unrealized_pnl', 0)
            unrealized_pnl_percent = position.get('unrealized_pnl_percent', 0)
            liquidation_price = position.get('liquidation_price', 0)
            take_profit_price = position.get('take_profit_price')
            stop_loss_price = position.get('stop_loss_price')
            opened_at_str = position.get('opened_at')
            
            # 计算距离止盈止损的距离
            distance_to_tp_percent = 0.0
            distance_to_sl_percent = 0.0
            if take_profit_price and current_price:
                distance_to_tp_percent = ((take_profit_price - current_price) / current_price) * 100
            if stop_loss_price and current_price:
                distance_to_sl_percent = ((stop_loss_price - current_price) / current_price) * 100
            
            # 计算距离强平的距离
            distance_to_liquidation_percent = 0.0
            if liquidation_price and current_price:
                if direction == "long":
                    distance_to_liquidation_percent = ((current_price - liquidation_price) / current_price) * 100
                else:  # short
                    distance_to_liquidation_percent = ((liquidation_price - current_price) / current_price) * 100
            
            # 计算当前仓位占比
            total_equity = account.get('total_equity', self.config.default_balance)
            current_position_percent = margin_used / total_equity if total_equity > 0 else 0
            
            # 计算是否可以追加
            max_margin = total_equity * self.config.max_position_percent
            available_balance = account.get('available_balance', 0)
            can_add_position = (margin_used < max_margin) and (available_balance >= 10)
            max_additional_amount = min(max_margin - margin_used, available_balance) if can_add_position else 0
            
            # 计算持仓时长
            opened_at = None
            holding_duration_hours = 0.0
            if opened_at_str:
                try:
                    opened_at = datetime.fromisoformat(opened_at_str.replace('Z', '+00:00'))
                    holding_duration_hours = (datetime.now(opened_at.tzinfo) - opened_at).total_seconds() / 3600
                except Exception as e:
                    logger.warning(f"Failed to parse opened_at: {e}")
            
            # 返回完整的持仓上下文
            return PositionContext(
                has_position=True,
                current_position=current_position,
                direction=direction,
                entry_price=entry_price,
                current_price=current_price,
                size=size,
                leverage=leverage,
                margin_used=margin_used,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                liquidation_price=liquidation_price,
                distance_to_liquidation_percent=distance_to_liquidation_percent,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                distance_to_tp_percent=distance_to_tp_percent,
                distance_to_sl_percent=distance_to_sl_percent,
                available_balance=account.get('available_balance', 0),
                total_equity=total_equity,
                used_margin=account.get('used_margin', 0),
                max_position_percent=self.config.max_position_percent,
                current_position_percent=current_position_percent,
                can_add_position=can_add_position,
                max_additional_amount=max_additional_amount,
                opened_at=opened_at,
                holding_duration_hours=holding_duration_hours
            )
        
        except Exception as e:
            logger.error(f"[PositionContext] Error getting position context: {e}", exc_info=True)
            # 返回默认的空持仓context
            return PositionContext(
                has_position=False,
                available_balance=self.config.default_balance,
                total_equity=self.config.default_balance,
                used_margin=0,
                max_position_percent=self.config.max_position_percent,
                can_add_position=False
            )
    
    async def _get_position_info_dict(self) -> Dict[str, Any]:
        """
        🔧 NEW: Get position info as a dict for TradeExecutor.
        
        Returns:
            {
                "has_position": bool,
                "current_position": {...} or None,
                "account": {...},
                "can_add": bool,
                ...
            }
        """
        try:
            # Get paper_trader from toolkit
            paper_trader = None
            if hasattr(self, 'toolkit') and hasattr(self.toolkit, 'paper_trader'):
                paper_trader = self.toolkit.paper_trader
            
            if not paper_trader:
                logger.warning("[PositionInfo] No paper_trader available")
                return {
                    "has_position": False,
                    "current_position": None,
                    "account": {},
                    "can_add": False
                }
            
            # Get account and position (使用正确的异步方法)
            # 🔧 FIX: get_account和get_position都是异步方法，需要await
            account = await paper_trader.get_account()
            position = await paper_trader.get_position()
            
            has_position = position is not None and position.get("has_position", False)
            
            # Calculate if can add more position
            can_add = False
            if has_position:
                # 🔧 FIX: position_value 不存在于 get_position() 返回值中
                # 使用 margin × leverage 计算持仓价值
                margin = position.get('margin', 0)
                leverage = position.get('leverage', 1)
                current_value = margin * leverage
                max_value = account.get('balance', 0) * (self.config.max_position_percent or 1.0)
                can_add = current_value < max_value * 0.9  # Leave 10% buffer
            
            return {
                "has_position": has_position,
                "current_position": position,
                "account": account,
                "can_add": can_add,
                "max_leverage": self.config.max_leverage,
                "max_position_percent": self.config.max_position_percent
            }
            
        except Exception as e:
            logger.error(f"[PositionInfo] Error getting position info: {e}")
            return {
                "has_position": False,
                "current_position": None,
                "account": {},
                "can_add": False
            }

    async def _run_execution_phase(self, signal: TradingSignal, position_context: PositionContext = None):
        """
        Phase 5: Trade Execution - NEW Intelligent TradeExecutor
        
        TradeExecutor现在是一个真正的决策Agent，它会：
        1. 理解Leader的会议总结
        2. 分析所有专家的投票
        3. 考虑当前持仓状态
        4. 做出独立的交易决策
        5. 执行交易
        
        不再依赖固定格式或标记！
        """
        self._add_message(
            agent_id="system",
            agent_name="System",
            content=f"## Phase 5: Trade Execution\n\nTrade Executor is analyzing meeting results and making decisions...",
            message_type="phase"
        )
        
        try:
            # Step 1: 获取Leader的会议总结
            leader_summary = self._get_leader_final_summary()
            logger.info(f"[ExecutionPhase] 📝 Leader总结长度: {len(leader_summary)} 字符")
            
            # Step 2: 收集专家投票
            agents_votes = self._get_agents_consensus()
            logger.info(f"[ExecutionPhase] 🗳️ 专家投票: {agents_votes}")
            
            # Step 3: 创建TradeExecutor Agent (具备直接工具调用能力)
            logger.info("[ExecutionPhase] 🤖 创建TradeExecutor Agent...")
            trade_executor_agent = await self._create_trade_executor_agent_instance()
            
            # Step 4: 构建执行prompt
            execution_prompt = self._build_execution_prompt(
                leader_summary=leader_summary,
                agents_votes=agents_votes,
                position_context=position_context
            )
            logger.info(f"[ExecutionPhase] 📝 执行Prompt构建完成，长度: {len(execution_prompt)} 字符")
            
            # Step 5: TradeExecutor通过Tool Calling执行交易
            # 🔧 核心改变: run()直接返回TradingSignal，不需要二次解析！
            logger.info("[ExecutionPhase] 🔍 TradeExecutor开始Tool Calling...")
            final_signal = await trade_executor_agent.run(execution_prompt)
            
            logger.info(
                f"[ExecutionPhase] ✅ TradeExecutor决策完成: {final_signal.direction.upper()} "
                f"| 杠杆 {final_signal.leverage}x "
                f"| 仓位 {final_signal.amount_percent*100:.0f}%"
            )
            
            # Step 5: 添加决策消息
            # FIX: _add_message doesn't support metadata parameter, removed
            self._add_message(
                agent_id="trade_executor",
                agent_name="Trade Executor",
                content=f"""## TradeExecutor Final Decision

**Decision**: {final_signal.direction.upper()}
**Leverage**: {final_signal.leverage}x
**Position**: {final_signal.amount_percent*100:.0f}%
**Confidence**: {final_signal.confidence}%

**Take Profit**: ${final_signal.take_profit_price:,.2f}
**Stop Loss**: ${final_signal.stop_loss_price:,.2f}

**Reasoning**:
{final_signal.reasoning}
""",
                message_type="decision"
            )
            
            # Step 6: 记录执行结果（工具函数已经执行过交易，无需再次执行！）
            # 🔧 核心改变: TradeExecutorAgentWithTools的工具函数已经直接执行了交易
            # open_long/open_short/close_position 函数内部调用了 paper_trader.open_position()
            # 所以这里只需要记录结果，不需要再调用LegacyExecutor
            
            if final_signal.direction != "hold":
                logger.info(f"[ExecutionPhase] ✅ Trade executed via Tool Calling: {final_signal.direction.upper()}")

                self._add_message(
                    agent_id="trade_executor",
                    agent_name="Trade Executor",
                    content=f"✅ Trade Executed\n\nDecision: {final_signal.direction.upper()}\nLeverage: {final_signal.leverage}x\nPosition: {final_signal.amount_percent*100:.0f}%",
                    message_type="execution"
                )

                self._execution_result = {
                    "status": "success",
                    "action": final_signal.direction,
                    "reason": final_signal.reasoning,
                    "details": {
                        "leverage": final_signal.leverage,
                        "amount_percent": final_signal.amount_percent,
                        "entry_price": final_signal.entry_price,
                        "take_profit": final_signal.take_profit_price,
                        "stop_loss": final_signal.stop_loss_price
                    }
                }

                # 🆕 记录 Agent 预测（用于平仓后反思）
                await self._record_agent_predictions_for_trade(final_signal.entry_price)

            else:
                logger.info("[ExecutionPhase] 📊 Decision is hold, no trade executed")
                self._execution_result = {
                    "status": "hold",
                    "action": "hold",
                    "reason": final_signal.reasoning
                }
            
            # Store final signal
            self._final_signal = final_signal
            
        except Exception as e:
            logger.error(f"[ExecutionPhase] ❌ Execution phase failed: {e}", exc_info=True)
            self._add_message(
                agent_id="system",
                agent_name="System",
                content=f"❌ Trade execution phase failed: {str(e)}",
                message_type="error"
            )
            # Return hold signal
            self._final_signal = await self._create_hold_signal(
                "",
                f"Execution phase failed: {str(e)}"
            )
    
    async def _create_trade_executor_agent_instance(self):
        """
        创建TradeExecutor的Agent实例
        
        🆕 重构: 使用现有的Agent类和FunctionTool机制
        - Agent类已有完整的Tool Calling支持（原生 + Legacy）
        - 使用FunctionTool包装交易函数
        - 不再需要硬编码正则检测
        
        架构:
        Leader总结 → TradeExecutor Agent → Agent.call_llm() with tools → 原生Tool Calling → 执行
        """
        from app.core.roundtable.tool import FunctionTool
        
        # 获取Leader的LLM配置
        leader = self._get_agent_by_id("Leader")
        if not leader:
            raise RuntimeError("Leader agent not found, cannot create TradeExecutor")
        
        # 🆕 重构: 使用现有Agent类 + FunctionTool，利用Agent原生的Tool Calling能力
        # 不再使用硬编码的正则检测！
        
        # 保存toolkit引用，供工具函数使用
        toolkit = self.toolkit
        
        # 🔧 创建交易工具函数（这些会被包装成FunctionTool）
        # 每个工具执行交易并返回结果字符串，同时保存TradingSignal到外部变量
        
        # 用于保存执行结果的容器
        execution_result = {"signal": None}
        
        async def get_current_price() -> float:
            """获取当前BTC价格"""
            try:
                if toolkit and hasattr(toolkit, '_get_market_price'):
                    result = await toolkit._get_market_price()
                    if isinstance(result, str):
                        # 🔧 FIX: 优先尝试解析JSON获取price字段
                        try:
                            import json as json_module
                            data = json_module.loads(result)
                            if isinstance(data, dict) and 'price' in data:
                                return float(data['price'])
                        except (json_module.JSONDecodeError, ValueError, KeyError):
                            pass
                        
                        # 🔧 FIX: 改进正则表达式 - 匹配数字开头的价格格式
                        # 先尝试匹配 $XX,XXX.XX 格式
                        price_match = re.search(r'\$(\d[\d,]*\.?\d*)', result)
                        if price_match:
                            return float(price_match.group(1).replace(',', ''))
                        # 再尝试匹配纯数字（如 93000.0）
                        price_match = re.search(r'(\d[\d,]*\.?\d*)', result)
                        if price_match:
                            price_str = price_match.group(1).replace(',', '')
                            if price_str and price_str != '.':
                                return float(price_str)
                    elif isinstance(result, (int, float)):
                        return float(result)
                
                if toolkit and hasattr(toolkit, 'paper_trader'):
                    # 🔧 FIX: PaperTrader使用_current_price属性（私有）
                    if hasattr(toolkit.paper_trader, '_current_price') and toolkit.paper_trader._current_price:
                        return float(toolkit.paper_trader._current_price)
            except Exception as e:
                logger.error(f"[TradeExecutor] 获取价格失败: {e}")
            return 93000.0  # fallback
        
        # 最小追加金额（美元）
        MIN_ADD_AMOUNT = 10.0
        # 安全缓冲（保留一定余额防止意外）
        SAFETY_BUFFER = 50.0
        
        def calculate_safe_stop_loss(direction: str, entry_price: float, leverage: int, margin: float) -> float:
            """
            计算安全的止损价格（确保在强平之前触发）
            
            强平条件: 亏损达到保证金的80%
            安全止损: 在强平价格的基础上增加5%安全缓冲
            """
            # 🔧 FIX: 防止除零错误
            if entry_price <= 0 or margin <= 0 or leverage <= 0:
                # 返回默认止损（3%）
                if direction == "long":
                    return entry_price * 0.97 if entry_price > 0 else 0
                else:
                    return entry_price * 1.03 if entry_price > 0 else float('inf')
            
            size = (margin * leverage) / entry_price
            liquidation_loss = margin * 0.8  # 80%保证金亏损触发强平
            
            if direction == "long":
                # 做多: 强平价 = 入场价 - (强平亏损 / 持仓量)
                liquidation_price = entry_price - (liquidation_loss / size) if size > 0 else 0
                # 安全止损 = 强平价 × 1.05 (比强平价高5%)
                safe_sl = liquidation_price * 1.05
                # 但不能超过默认止损（3%）
                default_sl = entry_price * 0.97
                return max(safe_sl, default_sl)
            else:
                # 做空: 强平价 = 入场价 + (强平亏损 / 持仓量)
                liquidation_price = entry_price + (liquidation_loss / size) if size > 0 else float('inf')
                # 安全止损 = 强平价 × 0.95 (比强平价低5%)
                safe_sl = liquidation_price * 0.95
                # 但不能低于默认止损（3%）
                default_sl = entry_price * 1.03
                return min(safe_sl, default_sl)
        
        def validate_stop_loss(direction: str, entry_price: float, sl_price: float, 
                              leverage: int, margin: float) -> tuple[bool, str, float]:
            """
            验证止损价格是否安全（在强平之前触发）
            
            Returns:
                (is_safe, message, safe_sl_price)
            """
            # 🔧 FIX: 防止除零错误
            if entry_price <= 0 or margin <= 0 or leverage <= 0:
                # 无法验证，直接返回原止损价格
                return True, "", sl_price
            
            size = (margin * leverage) / entry_price
            if size <= 0:
                return True, "", sl_price
            
            liquidation_loss = margin * 0.8
            
            if direction == "long":
                liquidation_price = entry_price - (liquidation_loss / size)
                if sl_price <= liquidation_price:
                    safe_sl = calculate_safe_stop_loss(direction, entry_price, leverage, margin)
                    return False, f"止损价${sl_price:.2f}低于强平价${liquidation_price:.2f}，已自动调整为${safe_sl:.2f}", safe_sl
            else:
                liquidation_price = entry_price + (liquidation_loss / size)
                if sl_price >= liquidation_price:
                    safe_sl = calculate_safe_stop_loss(direction, entry_price, leverage, margin)
                    return False, f"止损价${sl_price:.2f}高于强平价${liquidation_price:.2f}，已自动调整为${safe_sl:.2f}", safe_sl
            
            return True, "", sl_price
        
        async def open_long_tool(leverage: int = None, amount_percent: float = None,
                                confidence: int = None, reasoning: str = "") -> str:
            """
            开多仓（做多BTC）- 完整智能仓位处理 + 保证金风险管理

            决策矩阵:
            - 无仓位 → 正常开多
            - 已有多仓+可追加 → 追加多仓
            - 已有多仓+满仓 → 维持多仓
            - 已有空仓 → 平空→开多（反向操作）

            风险检查:
            - 使用真实可用保证金(考虑浮盈亏)
            - 验证止损价格不低于强平价
            - 保留安全缓冲

            Args:
                leverage: 杠杆倍数 1-20 (None=基于置信度自动计算)
                amount_percent: 仓位比例 0.0-1.0 (None=基于置信度自动计算)
                confidence: 信心度 0-100 (None=基于投票自动计算)
                reasoning: 决策理由
            """
            current_price = await get_current_price()

            # 🔧 FIX: 动态计算参数，不再使用硬编码默认值
            # 如果 confidence 未提供，基于投票动态计算
            if confidence is None:
                # 使用 _get_agents_consensus() 获取投票字典
                votes_dict = self._get_agents_consensus() if hasattr(self, '_get_agents_consensus') else {}
                confidence = calculate_confidence_from_votes(votes_dict, direction='long')
                logger.info(f"[open_long] confidence未提供，基于投票计算: {confidence}%")

            # 如果 leverage 未提供，基于 confidence 计算
            if leverage is None:
                leverage = calculate_leverage_from_confidence(confidence)
                logger.info(f"[open_long] leverage未提供，基于confidence计算: {leverage}x")

            # 如果 amount_percent 未提供，基于 confidence 计算
            if amount_percent is None:
                amount_percent = calculate_amount_from_confidence(confidence)
                logger.info(f"[open_long] amount_percent未提供，基于confidence计算: {amount_percent*100:.0f}%")

            leverage = min(max(int(leverage), 1), 20)
            amount_percent = min(max(float(amount_percent), 0.0), 1.0)
            
            trade_success = False
            entry_price = current_price
            action_taken = "open_long"
            final_reasoning = reasoning or ""
            
            # 根据杠杆调整止盈止损比例
            # 高杠杆 = 更紧的止损
            if leverage >= 15:
                tp_percent, sl_percent = 0.05, 0.02  # 5%止盈, 2%止损
            elif leverage >= 10:
                tp_percent, sl_percent = 0.06, 0.025  # 6%止盈, 2.5%止损
            elif leverage >= 5:
                tp_percent, sl_percent = 0.08, 0.03  # 8%止盈, 3%止损
            else:
                tp_percent, sl_percent = 0.10, 0.05  # 10%止盈, 5%止损
            
            take_profit = current_price * (1 + tp_percent)
            stop_loss = current_price * (1 - sl_percent)
            
            if toolkit and toolkit.paper_trader:
                try:
                    # 📊 Step 1: 收集完整状态信息
                    position = await toolkit.paper_trader.get_position()
                    account = await toolkit.paper_trader.get_account()
                    
                    has_position = position and position.get("has_position", False)
                    # 🔧 FIX: get_position() 返回的是平面字典，不是嵌套结构
                    # 直接从 position 字典获取数据
                    current_direction = position.get("direction") if has_position else None
                    existing_entry = position.get("entry_price", 0) if has_position else 0
                    existing_margin = position.get("margin", 0) if has_position else 0
                    unrealized_pnl = position.get("unrealized_pnl", 0) if has_position else 0
                    liquidation_price = position.get("liquidation_price", 0) if has_position else 0
                    
                    # 🔧 关键修复: 优先使用 OKX 的 max_avail_size（真实可开仓金额）
                    # max_avail_size 是 OKX 通过 /api/v5/account/max-avail-size 返回的
                    # 考虑了维持保证金、初始保证金率等因素，比本地计算更准确
                    max_avail_size = account.get("max_avail_size", 0)

                    # Fallback: 本地计算 true_available_margin = total_equity - used_margin
                    total_equity = account.get("total_equity", 10000)
                    used_margin = account.get("used_margin", 0)
                    local_available = total_equity - used_margin

                    # 使用 OKX 提供的值（如果有效），否则使用本地计算
                    if max_avail_size > 0:
                        true_available_margin = max_avail_size
                        margin_source = "OKX API"
                    else:
                        true_available_margin = local_available
                        margin_source = "本地计算"

                    # 兼容旧接口
                    if true_available_margin <= 0:
                        true_available_margin = account.get("true_available_margin", local_available)

                    available_balance = account.get("available_balance", 0)
                    total_equity = account.get("total_equity", available_balance)
                    used_margin = account.get("used_margin", 0)

                    # 🔧 可追加条件: 真实可用保证金 >= 最小金额 + 安全缓冲
                    can_add = true_available_margin >= (MIN_ADD_AMOUNT + SAFETY_BUFFER)

                    logger.info(f"[TradeExecutor] 📊 状态: 仓位={current_direction or '无'}, "
                               f"可用保证金=${true_available_margin:.2f}({margin_source}), "
                               f"账户余额=${available_balance:.2f}, 已用=${used_margin:.2f}, "
                               f"浮盈亏=${unrealized_pnl:.2f}, 可追加={can_add}")
                    
                    # 📌 场景1: 已有多仓（同方向）
                    if current_direction == "long":
                        if can_add:
                            # 场景1a: 可追加 → 追加多仓
                            # 🔧 使用 true_available_margin（考虑浮盈亏）
                            add_amount = min(
                                true_available_margin * amount_percent,
                                true_available_margin - SAFETY_BUFFER  # 保留安全缓冲
                            )
                            add_amount = max(add_amount, 0)  # 确保非负
                            
                            if add_amount >= MIN_ADD_AMOUNT:
                                logger.info(f"[TradeExecutor] 🔄 已有多仓，追加${add_amount:.2f} (真实可用${true_available_margin:.2f})")
                                
                                # 🔧 验证止损价格安全性
                                is_safe, sl_msg, safe_sl = validate_stop_loss("long", current_price, stop_loss, leverage, add_amount)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                result = await toolkit.paper_trader.open_long(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=add_amount,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "add_to_long"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"追加多仓成功: 原仓入场${existing_entry:.2f}, 追加${add_amount:.2f}(浮盈亏${unrealized_pnl:.2f})。{reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ 追加多仓成功")
                                else:
                                    # 追加失败，维持原仓
                                    trade_success = True
                                    action_taken = "maintain_long"
                                    entry_price = existing_entry
                                    final_reasoning = f"追加失败({result.get('error')}), 维持原多仓(入场${existing_entry:.2f})。{reasoning}"
                            else:
                                # 追加金额太小
                                trade_success = True
                                action_taken = "maintain_long_small"
                                entry_price = existing_entry
                                final_reasoning = f"追加金额太小(${add_amount:.2f}<${MIN_ADD_AMOUNT}), 维持原多仓(浮盈亏${unrealized_pnl:.2f})。{reasoning}"
                        else:
                            # 场景1b: 满仓或接近强平 → 维持多仓
                            trade_success = True
                            action_taken = "maintain_long_full"
                            entry_price = existing_entry
                            # 检查是否接近强平
                            if liquidation_price > 0 and current_price < liquidation_price * 1.1:
                                final_reasoning = f"⚠️ 接近强平(强平价${liquidation_price:.2f}), 维持多仓(浮亏${unrealized_pnl:.2f})。{reasoning}"
                            else:
                                final_reasoning = f"已满仓(真实可用${true_available_margin:.2f}), 维持多仓(入场${existing_entry:.2f}, 浮盈亏${unrealized_pnl:.2f})。{reasoning}"
                            logger.info(f"[TradeExecutor] ✅ 已满仓/不可追加，维持多仓不变")
                    
                    # 📌 场景2: 已有空仓（反方向）→ 平空→开多
                    elif current_direction == "short":
                        logger.info(f"[TradeExecutor] 🔄 反向操作: 平空→开多 (空仓浮盈亏${unrealized_pnl:.2f})")
                        
                        # 先平空仓
                        close_result = await toolkit.paper_trader.close_position(
                            symbol="BTC-USDT-SWAP",
                            reason="反向操作：空转多"
                        )
                        
                        if close_result.get("success"):
                            pnl = close_result.get("pnl", 0)
                            logger.info(f"[TradeExecutor] ✅ 平空仓成功, PnL=${pnl:.2f}")
                            
                            # 🔧 重新获取真实可用保证金（平仓后余额变化）
                            account = await toolkit.paper_trader.get_account()
                            new_true_available = account.get("true_available_margin", 0)
                            if new_true_available <= 0:
                                new_true_available = account.get("total_equity", 10000) - account.get("used_margin", 0)
                            
                            amount_usdt = min(
                                new_true_available * amount_percent,
                                new_true_available - SAFETY_BUFFER
                            )
                            amount_usdt = max(amount_usdt, 0)
                            
                            if amount_usdt >= MIN_ADD_AMOUNT:
                                # 🔧 验证止损价格安全性
                                is_safe, sl_msg, safe_sl = validate_stop_loss("long", current_price, stop_loss, leverage, amount_usdt)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                # 开多仓
                                result = await toolkit.paper_trader.open_long(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=amount_usdt,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "reverse_short_to_long"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"反向成功: 平空(PnL=${pnl:.2f})→开多${amount_usdt:.2f}。{reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ 反向开多成功")
                                else:
                                    trade_success = True  # 平仓成功算部分成功
                                    action_taken = "close_short_only"
                                    entry_price = current_price
                                    final_reasoning = f"平空成功(PnL=${pnl:.2f}), 但开多失败({result.get('error')})。{reasoning}"
                            else:
                                trade_success = True
                                action_taken = "close_short_insufficient"
                                entry_price = current_price
                                final_reasoning = f"平空成功(PnL=${pnl:.2f}), 但余额不足开多(真实可用${new_true_available:.2f})。{reasoning}"
                        else:
                            final_reasoning = f"平空仓失败: {close_result.get('error')}。{reasoning}"
                    
                    # 📌 场景3: 无仓位 → 正常开多
                    else:
                        # 🔧 使用 true_available_margin
                        amount_usdt = min(
                            true_available_margin * amount_percent,
                            true_available_margin - SAFETY_BUFFER
                        )
                        amount_usdt = max(amount_usdt, 0)
                        
                        if amount_usdt >= MIN_ADD_AMOUNT:
                            # 🔧 验证止损价格安全性
                            is_safe, sl_msg, safe_sl = validate_stop_loss("long", current_price, stop_loss, leverage, amount_usdt)
                            if not is_safe:
                                logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                stop_loss = safe_sl
                            
                            logger.info(f"[TradeExecutor] 📈 正常开多: ${amount_usdt:.2f}, {leverage}x (真实可用${true_available_margin:.2f})")
                            
                            result = await toolkit.paper_trader.open_long(
                                symbol="BTC-USDT-SWAP",
                                leverage=leverage,
                                amount_usdt=amount_usdt,
                                tp_price=take_profit,
                                sl_price=stop_loss
                            )
                            
                            if result.get("success"):
                                trade_success = True
                                action_taken = "new_long"
                                entry_price = result.get("executed_price", current_price)
                                final_reasoning = f"开多成功: ${amount_usdt:.2f}, {leverage}x杠杆, 止损${stop_loss:.2f}。{reasoning}"
                                logger.info(f"[TradeExecutor] ✅ 开多仓成功: 入场价${entry_price:.2f}")
                            else:
                                final_reasoning = f"开多失败: {result.get('error')}。{reasoning}"
                        else:
                            final_reasoning = f"余额不足(${available_balance:.2f}), 无法开仓。{reasoning}"
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] 开多仓异常: {e}", exc_info=True)
                    final_reasoning = f"执行异常: {e}。{reasoning}"
            
            # 保存TradingSignal
            execution_result["signal"] = TradingSignal(
                direction="long",
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=entry_price,
                take_profit_price=take_profit,
                stop_loss_price=stop_loss,
                confidence=confidence,
                reasoning=final_reasoning or f"TradeExecutor决定做多({action_taken})",
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            status = "成功" if trade_success else "失败"
            return f"✅ 做多{status}({action_taken}): {leverage}x杠杆, {amount_percent*100:.0f}%仓位, 入场价${entry_price:,.2f}"
        
        async def open_short_tool(leverage: int = None, amount_percent: float = None,
                                 confidence: int = None, reasoning: str = "") -> str:
            """
            开空仓（做空BTC）- 完整智能仓位处理 + 保证金风险管理

            决策矩阵:
            - 无仓位 → 正常开空
            - 已有空仓+可追加 → 追加空仓
            - 已有空仓+满仓 → 维持空仓
            - 已有多仓 → 平多→开空（反向操作）

            风险检查:
            - 使用真实可用保证金(考虑浮盈亏)
            - 验证止损价格不高于强平价
            - 保留安全缓冲

            Args:
                leverage: 杠杆倍数 1-20 (None=基于置信度自动计算)
                amount_percent: 仓位比例 0.0-1.0 (None=基于置信度自动计算)
                confidence: 信心度 0-100 (None=基于投票自动计算)
                reasoning: 决策理由
            """
            current_price = await get_current_price()

            # 🔧 FIX: 动态计算参数，不再使用硬编码默认值
            # 如果 confidence 未提供，基于投票动态计算
            if confidence is None:
                # 使用 _get_agents_consensus() 获取投票字典
                votes_dict = self._get_agents_consensus() if hasattr(self, '_get_agents_consensus') else {}
                confidence = calculate_confidence_from_votes(votes_dict, direction='short')
                logger.info(f"[open_short] confidence未提供，基于投票计算: {confidence}%")

            # 如果 leverage 未提供，基于 confidence 计算
            if leverage is None:
                leverage = calculate_leverage_from_confidence(confidence)
                logger.info(f"[open_short] leverage未提供，基于confidence计算: {leverage}x")

            # 如果 amount_percent 未提供，基于 confidence 计算
            if amount_percent is None:
                amount_percent = calculate_amount_from_confidence(confidence)
                logger.info(f"[open_short] amount_percent未提供，基于confidence计算: {amount_percent*100:.0f}%")

            leverage = min(max(int(leverage), 1), 20)
            amount_percent = min(max(float(amount_percent), 0.0), 1.0)
            
            # 根据杠杆调整止盈止损比例（做空）
            if leverage >= 15:
                tp_percent, sl_percent = 0.05, 0.02
            elif leverage >= 10:
                tp_percent, sl_percent = 0.06, 0.025
            elif leverage >= 5:
                tp_percent, sl_percent = 0.08, 0.03
            else:
                tp_percent, sl_percent = 0.10, 0.05
            
            take_profit = current_price * (1 - tp_percent)  # 做空：价格下跌止盈
            stop_loss = current_price * (1 + sl_percent)    # 做空：价格上涨止损
            
            trade_success = False
            entry_price = current_price
            action_taken = "open_short"
            final_reasoning = reasoning or ""
            
            if toolkit and toolkit.paper_trader:
                try:
                    # 📊 Step 1: 收集完整状态信息
                    position = await toolkit.paper_trader.get_position()
                    account = await toolkit.paper_trader.get_account()
                    
                    has_position = position and position.get("has_position", False)
                    # 🔧 FIX: get_position() 返回的是平面字典，不是嵌套结构
                    # 直接从 position 字典获取数据
                    current_direction = position.get("direction") if has_position else None
                    existing_entry = position.get("entry_price", 0) if has_position else 0
                    existing_margin = position.get("margin", 0) if has_position else 0
                    unrealized_pnl = position.get("unrealized_pnl", 0) if has_position else 0
                    liquidation_price = position.get("liquidation_price", 0) if has_position else 0
                    
                    # 🔧 关键修复: 优先使用 OKX 的 max_avail_size（真实可开仓金额）
                    max_avail_size = account.get("max_avail_size", 0)

                    # Fallback: 本地计算
                    total_equity = account.get("total_equity", 10000)
                    used_margin = account.get("used_margin", 0)
                    local_available = total_equity - used_margin

                    # 使用 OKX 提供的值（如果有效）
                    if max_avail_size > 0:
                        true_available_margin = max_avail_size
                        margin_source = "OKX API"
                    else:
                        true_available_margin = local_available
                        margin_source = "本地计算"

                    if true_available_margin <= 0:
                        true_available_margin = account.get("true_available_margin", local_available)

                    available_balance = account.get("available_balance", 0)
                    total_equity = account.get("total_equity", available_balance)
                    used_margin = account.get("used_margin", 0)

                    # 🔧 可追加条件
                    can_add = true_available_margin >= (MIN_ADD_AMOUNT + SAFETY_BUFFER)

                    logger.info(f"[TradeExecutor] 📊 状态: 仓位={current_direction or '无'}, "
                               f"可用保证金=${true_available_margin:.2f}({margin_source}), "
                               f"账户余额=${available_balance:.2f}, 已用=${used_margin:.2f}, "
                               f"浮盈亏=${unrealized_pnl:.2f}, 可追加={can_add}")

                    # 📌 场景1: 已有空仓（同方向）
                    if current_direction == "short":
                        if can_add:
                            # 场景1a: 可追加 → 追加空仓
                            add_amount = min(
                                true_available_margin * amount_percent,
                                true_available_margin - SAFETY_BUFFER
                            )
                            add_amount = max(add_amount, 0)
                            
                            if add_amount >= MIN_ADD_AMOUNT:
                                logger.info(f"[TradeExecutor] 🔄 已有空仓，追加${add_amount:.2f} (真实可用${true_available_margin:.2f})")
                                
                                # 🔧 验证止损价格安全性
                                is_safe, sl_msg, safe_sl = validate_stop_loss("short", current_price, stop_loss, leverage, add_amount)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                result = await toolkit.paper_trader.open_short(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=add_amount,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "add_to_short"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"追加空仓成功: 原仓入场${existing_entry:.2f}, 追加${add_amount:.2f}(浮盈亏${unrealized_pnl:.2f})。{reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ 追加空仓成功")
                                else:
                                    trade_success = True
                                    action_taken = "maintain_short"
                                    entry_price = existing_entry
                                    final_reasoning = f"追加失败({result.get('error')}), 维持原空仓(入场${existing_entry:.2f})。{reasoning}"
                            else:
                                trade_success = True
                                action_taken = "maintain_short_small"
                                entry_price = existing_entry
                                final_reasoning = f"追加金额太小(${add_amount:.2f}<${MIN_ADD_AMOUNT}), 维持原空仓(浮盈亏${unrealized_pnl:.2f})。{reasoning}"
                        else:
                            # 场景1b: 满仓或接近强平 → 维持空仓
                            trade_success = True
                            action_taken = "maintain_short_full"
                            entry_price = existing_entry
                            if liquidation_price > 0 and current_price > liquidation_price * 0.9:
                                final_reasoning = f"⚠️ 接近强平(强平价${liquidation_price:.2f}), 维持空仓(浮亏${unrealized_pnl:.2f})。{reasoning}"
                            else:
                                final_reasoning = f"已满仓(真实可用${true_available_margin:.2f}), 维持空仓(入场${existing_entry:.2f}, 浮盈亏${unrealized_pnl:.2f})。{reasoning}"
                            logger.info(f"[TradeExecutor] ✅ 已满仓/不可追加，维持空仓不变")
                    
                    # 📌 场景2: 已有多仓（反方向）→ 平多→开空
                    elif current_direction == "long":
                        logger.info(f"[TradeExecutor] 🔄 反向操作: 平多→开空 (多仓浮盈亏${unrealized_pnl:.2f})")
                        
                        # 先平多仓
                        close_result = await toolkit.paper_trader.close_position(
                            symbol="BTC-USDT-SWAP",
                            reason="反向操作：多转空"
                        )
                        
                        if close_result.get("success"):
                            pnl = close_result.get("pnl", 0)
                            logger.info(f"[TradeExecutor] ✅ 平多仓成功, PnL=${pnl:.2f}")
                            
                            # 🔧 重新获取真实可用保证金
                            account = await toolkit.paper_trader.get_account()
                            new_true_available = account.get("true_available_margin", 0)
                            if new_true_available <= 0:
                                new_true_available = account.get("total_equity", 10000) - account.get("used_margin", 0)
                            
                            amount_usdt = min(
                                new_true_available * amount_percent,
                                new_true_available - SAFETY_BUFFER
                            )
                            amount_usdt = max(amount_usdt, 0)
                            
                            if amount_usdt >= MIN_ADD_AMOUNT:
                                # 🔧 验证止损价格安全性
                                is_safe, sl_msg, safe_sl = validate_stop_loss("short", current_price, stop_loss, leverage, amount_usdt)
                                if not is_safe:
                                    logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                    stop_loss = safe_sl
                                
                                # 开空仓
                                result = await toolkit.paper_trader.open_short(
                                    symbol="BTC-USDT-SWAP",
                                    leverage=leverage,
                                    amount_usdt=amount_usdt,
                                    tp_price=take_profit,
                                    sl_price=stop_loss
                                )
                                if result.get("success"):
                                    trade_success = True
                                    action_taken = "reverse_long_to_short"
                                    entry_price = result.get("executed_price", current_price)
                                    final_reasoning = f"反向成功: 平多(PnL=${pnl:.2f})→开空${amount_usdt:.2f}。{reasoning}"
                                    logger.info(f"[TradeExecutor] ✅ 反向开空成功")
                                else:
                                    trade_success = True
                                    action_taken = "close_long_only"
                                    entry_price = current_price
                                    final_reasoning = f"平多成功(PnL=${pnl:.2f}), 但开空失败({result.get('error')})。{reasoning}"
                            else:
                                trade_success = True
                                action_taken = "close_long_insufficient"
                                entry_price = current_price
                                final_reasoning = f"平多成功(PnL=${pnl:.2f}), 但余额不足开空(真实可用${new_true_available:.2f})。{reasoning}"
                        else:
                            final_reasoning = f"平多仓失败: {close_result.get('error')}。{reasoning}"
                    
                    # 📌 场景3: 无仓位 → 正常开空
                    else:
                        amount_usdt = min(
                            true_available_margin * amount_percent,
                            true_available_margin - SAFETY_BUFFER
                        )
                        amount_usdt = max(amount_usdt, 0)
                        
                        if amount_usdt >= MIN_ADD_AMOUNT:
                            # 🔧 验证止损价格安全性
                            is_safe, sl_msg, safe_sl = validate_stop_loss("short", current_price, stop_loss, leverage, amount_usdt)
                            if not is_safe:
                                logger.warning(f"[TradeExecutor] ⚠️ {sl_msg}")
                                stop_loss = safe_sl
                            
                            logger.info(f"[TradeExecutor] 📉 正常开空: ${amount_usdt:.2f}, {leverage}x (真实可用${true_available_margin:.2f})")
                            
                            result = await toolkit.paper_trader.open_short(
                                symbol="BTC-USDT-SWAP",
                                leverage=leverage,
                                amount_usdt=amount_usdt,
                                tp_price=take_profit,
                                sl_price=stop_loss
                            )
                            
                            if result.get("success"):
                                trade_success = True
                                action_taken = "new_short"
                                entry_price = result.get("executed_price", current_price)
                                final_reasoning = f"开空成功: ${amount_usdt:.2f}, {leverage}x杠杆, 止损${stop_loss:.2f}。{reasoning}"
                                logger.info(f"[TradeExecutor] ✅ 开空仓成功: 入场价${entry_price:.2f}")
                            else:
                                final_reasoning = f"开空失败: {result.get('error')}。{reasoning}"
                        else:
                            final_reasoning = f"余额不足(真实可用${true_available_margin:.2f}), 无法开仓。{reasoning}"
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] 开空仓异常: {e}", exc_info=True)
                    final_reasoning = f"执行异常: {e}。{reasoning}"
            
            execution_result["signal"] = TradingSignal(
                direction="short",
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=entry_price,
                take_profit_price=take_profit,
                stop_loss_price=stop_loss,
                confidence=confidence,
                reasoning=final_reasoning or f"TradeExecutor决定做空({action_taken})",
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            status = "成功" if trade_success else "失败"
            return f"✅ 做空{status}({action_taken}): {leverage}x杠杆, {amount_percent*100:.0f}%仓位, 入场价${entry_price:,.2f}"
        
        async def close_position_tool(reasoning: str = "") -> str:
            """
            平仓当前持仓
            
            Args:
                reasoning: 平仓理由
            """
            current_price = await get_current_price()
            close_success = False
            pnl = 0.0
            
            if toolkit and toolkit.paper_trader:
                try:
                    # 传入reason参数以便记录
                    result = await toolkit.paper_trader.close_position(
                        symbol="BTC-USDT-SWAP",
                        reason=reasoning or "TradeExecutor决定平仓"
                    )
                    
                    if result.get("success"):
                        close_success = True
                        pnl = result.get("pnl", 0)
                        logger.info(f"[TradeExecutor] ✅ 平仓成功, PnL: ${pnl:.2f}")
                    else:
                        error_msg = result.get("error", "未知错误")
                        logger.error(f"[TradeExecutor] 平仓失败: {error_msg}")
                        reasoning = f"平仓执行失败: {error_msg}. " + reasoning
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] 平仓异常: {e}")
                    reasoning = f"平仓执行异常: {e}. " + reasoning
            
            execution_result["signal"] = TradingSignal(
                direction="hold",
                symbol="BTC-USDT-SWAP",
                leverage=1,
                amount_percent=0.0,
                entry_price=current_price,
                take_profit_price=current_price,
                stop_loss_price=current_price,
                confidence=100 if close_success else 50,
                reasoning=f"[平仓操作] {reasoning or 'TradeExecutor决定平仓'}" + (f" (PnL: ${pnl:.2f})" if close_success else ""),
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            return f"✅ 平仓{'成功' if close_success else '失败'}" + (f" (PnL: ${pnl:.2f})" if close_success else "")
        
        async def hold_tool(reason: str = "市场不明朗，选择观望") -> str:
            """
            观望不操作
            
            Args:
                reason: 观望原因
            """
            current_price = await get_current_price()
            logger.info(f"[TradeExecutor] ✅ 决定观望: {reason}")
            
            execution_result["signal"] = TradingSignal(
                direction="hold",
                symbol="BTC-USDT-SWAP",
                leverage=1,
                amount_percent=0.0,
                entry_price=current_price,
                take_profit_price=current_price,
                stop_loss_price=current_price,
                confidence=0,
                reasoning=reason,
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            return f"📊 决定观望: {reason}"
        
        # 🆕 创建真正的Agent实例并注册FunctionTool
        # FIX: Agent uses id instead of agent_id, uses llm_gateway_url instead of llm_endpoint
        trade_executor = Agent(
            id="trade_executor",
            name="TradeExecutor",
            role="Trade Execution Specialist",
            system_prompt="""You are the Trade Executor, responsible for executing trades based on expert meeting results.

You must call a tool to execute decisions. Available tools:
- open_long: Open long position (buy BTC)
- open_short: Open short position (sell BTC)
- close_position: Close current position
- hold: Hold/wait, no action

Decision Rules:
1. Experts 3-4 votes unanimous bullish → Call open_long
2. Experts 3-4 votes unanimous bearish → Call open_short
3. Experts split or unclear → Call hold
4. Has opposite position to close → Call close_position

You MUST call a tool based on meeting results!""",
            llm_gateway_url=leader.llm_gateway_url if hasattr(leader, 'llm_gateway_url') else "http://llm_gateway:8003",
            temperature=0.3
        )

        # Register trading tools (using FunctionTool wrapper)
        trade_executor.register_tool(FunctionTool(
            name="open_long",
            description="Open long position (buy BTC) - Call when expert consensus is bullish",
            func=open_long_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage multiplier 1-20"},
                    "amount_percent": {"type": "number", "description": "Position ratio 0.0-1.0"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100"},
                    "reasoning": {"type": "string", "description": "Decision reasoning"}
                },
                "required": ["leverage", "amount_percent"]
            }
        ))

        trade_executor.register_tool(FunctionTool(
            name="open_short",
            description="Open short position (sell BTC) - Call when expert consensus is bearish",
            func=open_short_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Leverage multiplier 1-20"},
                    "amount_percent": {"type": "number", "description": "Position ratio 0.0-1.0"},
                    "confidence": {"type": "integer", "description": "Confidence level 0-100"},
                    "reasoning": {"type": "string", "description": "Decision reasoning"}
                },
                "required": ["leverage", "amount_percent"]
            }
        ))

        trade_executor.register_tool(FunctionTool(
            name="close_position",
            description="Close current position - Call when need TP/SL or reverse operation",
            func=close_position_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "Close reasoning"}
                }
            }
        ))

        trade_executor.register_tool(FunctionTool(
            name="hold",
            description="Hold/wait, no action - Call when market unclear or experts split",
            func=hold_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Hold reason"}
                },
                "required": ["reason"]
            }
        ))

        logger.info(f"[TradeExecutor] ✅ Agent created successfully, registered {len(trade_executor.tools)} trading tools")
        
        # 🆕 包装器类，提供run()方法返回TradingSignal
        class TradeExecutorWrapper:
            def __init__(self, agent, result_container, tools_dict):
                self.agent = agent
                self.result = result_container
                self.tools = tools_dict  # 工具函数字典
            
            async def run(self, prompt: str) -> TradingSignal:
                """
                运行TradeExecutor，调用LLM并处理工具执行
                
                流程:
                1. 调用Agent._call_llm()获取LLM响应
                2. 检测原生tool_calls或Legacy [USE_TOOL: xxx]格式
                3. 执行对应的工具函数
                4. 返回TradingSignal
                """
                try:
                    # Step 1: 调用LLM
                    messages = [{"role": "user", "content": prompt}]
                    response = await self.agent._call_llm(messages)
                    
                    # Step 2: 解析响应
                    content = ""
                    tool_calls = []
                    
                    if isinstance(response, dict):
                        # OpenAI格式响应
                        if "choices" in response and response["choices"]:
                            message = response["choices"][0].get("message", {})
                            content = message.get("content", "")
                            tool_calls = message.get("tool_calls", [])
                        else:
                            content = response.get("content", str(response))
                    else:
                        content = str(response)
                    
                    logger.info(f"[TradeExecutor] LLM响应: {content[:200] if content else 'None'}...")
                    
                    # Step 3: 处理原生tool_calls (OpenAI格式)
                    if tool_calls:
                        logger.info(f"[TradeExecutor] 🎯 检测到原生Tool Calls: {len(tool_calls)}")
                        for tc in tool_calls:
                            func = tc.get("function", {})
                            tool_name = func.get("name", "")
                            tool_args_str = func.get("arguments", "{}")
                            
                            if tool_name in self.tools:
                                try:
                                    import json
                                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                                    logger.info(f"[TradeExecutor] 🔧 执行原生工具: {tool_name}({tool_args})")
                                    await self.tools[tool_name](**tool_args)
                                except Exception as e:
                                    logger.error(f"[TradeExecutor] 工具执行失败: {e}")
                    
                    # Step 4: 处理Legacy格式 [USE_TOOL: xxx]
                    tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
                    legacy_matches = re.findall(tool_pattern, content or "")
                    
                    if legacy_matches:
                        logger.info(f"[TradeExecutor] 🎯 检测到Legacy Tool Calls: {len(legacy_matches)}")
                        for tool_name, params_str in legacy_matches:
                            if tool_name in self.tools:
                                try:
                                    # 解析参数
                                    params = {}
                                    # 尝试各种参数格式
                                    for pattern in [r'(\w+)="([^"]*)"', r"(\w+)='([^']*)'", r'(\w+)=(\d+\.?\d*)']:
                                        for key, value in re.findall(pattern, params_str):
                                            # 类型转换
                                            if value.replace('.', '').replace('-', '').isdigit():
                                                value = float(value) if '.' in value else int(value)
                                            params[key] = value

                                    # 参数名映射 (LLM可能用不同的名称)
                                    param_aliases = {
                                        'reason': 'reasoning',  # LLM常用reason而不是reasoning
                                        'amount': 'amount_percent',
                                        'lev': 'leverage',
                                        'conf': 'confidence',
                                    }
                                    for old_name, new_name in param_aliases.items():
                                        if old_name in params and new_name not in params:
                                            params[new_name] = params.pop(old_name)

                                    logger.info(f"[TradeExecutor] 🔧 执行Legacy工具: {tool_name}({params})")
                                    await self.tools[tool_name](**params)
                                except Exception as e:
                                    logger.error(f"[TradeExecutor] 工具执行失败: {e}")
                    
                    # Step 5: 检查是否有工具执行结果
                    if self.result["signal"]:
                        signal = self.result["signal"]
                        logger.info(f"[TradeExecutor] ✅ 工具执行完成: {signal.direction}")
                        # 清空结果容器以供下次使用
                        self.result["signal"] = None
                        return signal
                    
                    # Step 6: 没有工具调用 - 尝试从响应文本推断决策
                    logger.warning("[TradeExecutor] ⚠️ 未检测到工具调用，尝试从响应推断...")
                    return await self._infer_from_text(content or "")
                    
                except Exception as e:
                    logger.error(f"[TradeExecutor] ❌ 执行失败: {e}", exc_info=True)
                    current_price = await get_current_price()
                    return TradingSignal(
                        direction="hold",
                        symbol="BTC-USDT-SWAP",
                        leverage=1,
                        amount_percent=0.0,
                        entry_price=current_price,
                        take_profit_price=current_price,
                        stop_loss_price=current_price,
                        confidence=0,
                        reasoning=f"TradeExecutor执行失败: {str(e)}",
                        agents_consensus={},
                        timestamp=datetime.now()
                    )
            
            async def _infer_from_text(self, text: str) -> TradingSignal:
                """从自然语言响应推断决策（备用方案）"""
                text_lower = text.lower()

                # 检测方向关键词
                if any(kw in text_lower for kw in ['做多', '开多', 'long', '看涨', '买入']):
                    # 提取参数 - 如果文本中没有，则设为None让工具函数动态计算
                    leverage_match = re.search(r'(\d+)\s*[倍xX]', text)
                    leverage = int(leverage_match.group(1)) if leverage_match else None

                    amount_match = re.search(r'(\d+)\s*%', text)
                    amount = (int(amount_match.group(1)) / 100) if amount_match else None

                    confidence_match = re.search(r'信心[度]?\s*[:：]?\s*(\d+)', text)
                    confidence = int(confidence_match.group(1)) if confidence_match else None

                    logger.info(f"[TradeExecutor] 📊 从文本推断做多: leverage={leverage}, amount={amount}, confidence={confidence}")
                    logger.info(f"[TradeExecutor] 📊 未提供的参数将基于投票动态计算")
                    await self.tools['open_long'](
                        leverage=min(leverage, 20) if leverage else None,
                        amount_percent=min(amount, 1.0) if amount else None,
                        confidence=confidence,
                        reasoning=text[:200]
                    )

                elif any(kw in text_lower for kw in ['做空', '开空', 'short', '看跌', '卖出']):
                    leverage_match = re.search(r'(\d+)\s*[倍xX]', text)
                    leverage = int(leverage_match.group(1)) if leverage_match else None

                    amount_match = re.search(r'(\d+)\s*%', text)
                    amount = (int(amount_match.group(1)) / 100) if amount_match else None

                    confidence_match = re.search(r'信心[度]?\s*[:：]?\s*(\d+)', text)
                    confidence = int(confidence_match.group(1)) if confidence_match else None

                    logger.info(f"[TradeExecutor] 📊 从文本推断做空: leverage={leverage}, amount={amount}, confidence={confidence}")
                    logger.info(f"[TradeExecutor] 📊 未提供的参数将基于投票动态计算")
                    await self.tools['open_short'](
                        leverage=min(leverage, 20) if leverage else None,
                        amount_percent=min(amount, 1.0) if amount else None,
                        confidence=confidence,
                        reasoning=text[:200]
                    )
                    
                elif any(kw in text_lower for kw in ['平仓', '关闭', 'close']):
                    logger.info("[TradeExecutor] 📊 从文本推断平仓")
                    await self.tools['close_position'](reasoning=text[:200])
                    
                else:
                    logger.info("[TradeExecutor] 📊 从文本推断观望")
                    await self.tools['hold'](reason=text[:200] or "市场不明朗")
                
                # 返回执行结果
                if self.result["signal"]:
                    signal = self.result["signal"]
                    self.result["signal"] = None
                    return signal
                
                # 如果工具执行也失败，返回默认hold
                current_price = await get_current_price()
                return TradingSignal(
                    direction="hold",
                    symbol="BTC-USDT-SWAP",
                    leverage=1,
                    amount_percent=0.0,
                    entry_price=current_price,
                    take_profit_price=current_price,
                    stop_loss_price=current_price,
                    confidence=0,
                    reasoning=f"无法推断决策: {text[:100]}",
                    agents_consensus={},
                    timestamp=datetime.now()
                )
        
        # 创建工具函数字典供wrapper使用
        tools_dict = {
            'open_long': open_long_tool,
            'open_short': open_short_tool,
            'close_position': close_position_tool,
            'hold': hold_tool
        }
        
        return TradeExecutorWrapper(trade_executor, execution_result, tools_dict)
    
    def _build_execution_prompt(
        self,
        leader_summary: str,
        agents_votes: Dict[str, str],
        position_context: PositionContext
    ) -> str:
        """
        Build execution phase prompt

        This prompt is sent to TradeExecutor's LLM to call tools and execute trades
        """

        # FIX: Ensure agents_votes is dict type
        if isinstance(agents_votes, list):
            logger.warning(f"[_build_execution_prompt] agents_votes is list type, converting to dict")
            try:
                agents_votes = {v.agent_name: v.direction for v in agents_votes if hasattr(v, 'agent_name') and hasattr(v, 'direction')}
            except Exception as e:
                logger.error(f"[_build_execution_prompt] Cannot convert agents_votes: {e}")
                agents_votes = {}

        # Format votes
        long_count = sum(1 for v in agents_votes.values() if v == 'long')
        short_count = sum(1 for v in agents_votes.values() if v == 'short')
        hold_count = sum(1 for v in agents_votes.values() if v == 'hold')

        vote_details = []
        for agent, vote in agents_votes.items():
            emoji = "🟢" if vote == "long" else "🔴" if vote == "short" else "⚪"
            vote_text = "Long" if vote == "long" else "Short" if vote == "short" else "Hold"
            vote_details.append(f"  {emoji} {agent}: {vote_text}")

        # Format position status
        if position_context.has_position:
            direction = position_context.direction or "unknown"
            position_status = f"""**Has Position** ({direction.upper()})
- Entry Price: ${position_context.entry_price:,.2f}
- Current Price: ${position_context.current_price:,.2f}
- Position Size: {position_context.size:.4f} BTC
- Leverage: {position_context.leverage}x
- Unrealized P&L: ${position_context.unrealized_pnl:,.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- Available Balance: ${position_context.available_balance:,.2f}"""
        else:
            position_status = f"""**No Position**
- Available Balance: ${position_context.available_balance:,.2f}
- Total Equity: ${position_context.total_equity:,.2f}"""

        prompt = f"""## Trade Execution Task

### 1. Expert Voting Results
**Summary**: {long_count} Long / {short_count} Short / {hold_count} Hold

{chr(10).join(vote_details)}

### 2. Current Position Status
{position_status}

### 3. Leader's Meeting Summary
{leader_summary}

---

### Your Task
Based on the above information, you **MUST call a tool** to execute the trading decision.

**Decision Rules (based on voting consensus level)**:
- High consensus (4-5 unanimous votes) → Call open_long/open_short, parameters auto-calculated based on votes
- Moderate consensus (3 votes) → Call open_long/open_short, parameters auto-calculated based on votes
- Weak consensus (2 votes) → Call open_long/open_short, parameters auto-calculated based on votes
- Split opinions or unclear → Call hold(reason="...")
- Has opposite position to handle → First call close_position()

**Important**: confidence/leverage/amount_percent will be auto-calculated based on voting consensus level, no need to manually specify fixed values!

**Output Format (must follow)**:
[USE_TOOL: tool_name(param=value, ...)]

Now, please analyze and call a tool to execute your decision."""

        return prompt
    
    def _get_leader_final_summary(self) -> str:
        """Get Leader's last message as meeting summary"""
        if not hasattr(self, 'message_bus') or not self.message_bus:
            self.logger.warning("[TradingMeeting] message_bus does not exist")
            return "No meeting record"

        # FIX: MessageBus uses message_history instead of messages
        messages = getattr(self.message_bus, 'message_history', [])
        if not messages:
            return "No meeting messages"
        
        # 从消息历史中找Leader的最后一条消息
        leader_messages = [
            msg for msg in messages
            if (hasattr(msg, 'sender') and msg.sender == "Leader") or
               (hasattr(msg, 'agent_name') and msg.agent_name == "Leader") or
               (hasattr(msg, 'agent_id') and msg.agent_id == "leader") or
               (isinstance(msg, dict) and (
                   msg.get("sender") == "Leader" or 
                   msg.get("agent_name") == "Leader" or 
                   msg.get("agent_id") == "leader"
               ))
        ]
        
        if leader_messages:
            last_msg = leader_messages[-1]
            # 处理Message对象或dict
            if isinstance(last_msg, dict):
                return last_msg.get("content", "")
            elif hasattr(last_msg, 'content'):
                return last_msg.content
            else:
                return str(last_msg)
        
        return "Leader did not speak (possibly LLM failure)"

    async def _run_agent_turn(self, agent: Agent, prompt: str) -> str:
        """Run a single agent's turn using agent's own LLM call method with tool execution"""
        # Get conversation history for context
        history = self._get_conversation_history()

        # Build full prompt with history
        full_prompt = f"{history}\n\n{prompt}"

        try:
            # Get agent's memory for context injection
            if not self._memory_store:
                self._memory_store = await get_memory_store()

            memory = await self._memory_store.get_memory(agent.id, agent.name)
            memory_context = memory.get_context_for_prompt()

            # Build enhanced system prompt with memory
            # Use _get_system_prompt() which includes tool usage instructions
            if hasattr(agent, '_get_system_prompt'):
                base_system_prompt = agent._get_system_prompt()
            else:
                base_system_prompt = agent.system_prompt or agent.role_prompt

            # 🔧 FIX: 检查是否有任何有意义的记忆内容需要注入
            # 不仅检查 total_trades，还要检查反思记录和教训
            has_memory_content = (
                memory.total_trades > 0 or
                len(memory.recent_reflections) > 0 or
                memory.last_trade_summary or
                len(memory.lessons_learned) > 0
            )

            if has_memory_content and memory_context.strip():
                # Only inject memory if agent has meaningful history
                enhanced_system_prompt = f"""{base_system_prompt}

---
{memory_context}
---

Please reference your historical performance and lessons learned in your analysis, avoid repeating past mistakes."""
            else:
                enhanced_system_prompt = base_system_prompt

            # Build messages for LLM
            messages = [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": full_prompt}
            ]

            # Use agent's own _call_llm method (has built-in retry)
            logger.info(f"Calling LLM for agent: {agent.name}")
            response = await agent._call_llm(messages)

            # Extract content from response
            # Agent._call_llm returns OpenAI format: {"choices": [{"message": {"content": "..."}}]}
            content = ""
            if isinstance(response, dict):
                if "choices" in response:
                    # OpenAI format
                    try:
                        content = response["choices"][0]["message"]["content"]
                    except (KeyError, IndexError):
                        pass
                if not content:
                    # Fallback to direct content
                    content = response.get("content", response.get("response", ""))
            else:
                content = str(response)

            if not content:
                content = f"[{agent.name}] Analysis complete, no clear recommendation at this time."

            # Handle blocked or empty responses from Gemini safety filter
            if "[Response blocked or empty]" in content or not content.strip():
                logger.warning(f"Agent {agent.name} response was blocked by content filter")
                content = self._get_fallback_response(agent.id, agent.name)

            # ===== Tool Execution =====
            # Clear previous tool executions for this agent turn
            self._last_executed_tools = []
            
            # 🆕 Step 1: 检测原生tool_calls (OpenAI格式)
            native_tool_calls = []
            if isinstance(response, dict) and "choices" in response:
                try:
                    message = response["choices"][0].get("message", {})
                    native_tool_calls = message.get("tool_calls", [])
                except (KeyError, IndexError):
                    pass
            
            if native_tool_calls and hasattr(agent, 'tools') and agent.tools:
                logger.info(f"[{agent.name}] 🎯 检测到原生Tool Calls: {len(native_tool_calls)}")
                tool_results = []
                
                for tc in native_tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    tool_args_str = func.get("arguments", "{}")
                    
                    if tool_name in agent.tools:
                        try:
                            import json
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                            logger.info(f"[{agent.name}] Native Tool Calling: {tool_name}({tool_args})")
                            
                            tool_result = await agent.tools[tool_name].execute(**tool_args)
                            logger.info(f"[{agent.name}] Tool {tool_name} result received")
                            
                            # Record executed tool call
                            self._last_executed_tools.append({
                                "tool_name": tool_name,
                                "params": tool_args,
                                "result": tool_result
                            })
                            
                            # Collect tool results
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name} Result]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name} Result]: {str(tool_result)[:1000]}")

                        except Exception as e:
                            logger.error(f"[{agent.name}] Native tool execution failed: {e}")
                            tool_results.append(f"\n[{tool_name} Error]: {str(e)}")
                
                # If we have tool results, do a follow-up LLM call
                if tool_results:
                    logger.info(f"[{agent.name}] Making follow-up LLM call with native tool results")
                    tool_results_text = "\n".join(tool_results)
                    
                    follow_up_messages = messages + [
                        {"role": "assistant", "content": content or ""},
                        {"role": "user", "content": f"Tool results:\n{tool_results_text}\n\nPlease provide your final analysis conclusion based on this real data."}
                    ]
                    
                    follow_up_response = await agent._call_llm(follow_up_messages)
                    
                    if isinstance(follow_up_response, dict):
                        if "choices" in follow_up_response:
                            try:
                                content = follow_up_response["choices"][0]["message"]["content"]
                            except (KeyError, IndexError):
                                pass
                        if not content:
                            content = follow_up_response.get("content", "")
                    elif isinstance(follow_up_response, str):
                        content = follow_up_response
            
            # 🆕 Step 2: 检测Legacy格式 [USE_TOOL: xxx] (兼容模式)
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content or "")

            # Deduplicate decision tools - only allow the FIRST open_long/open_short/hold call
            # This prevents Leader from accidentally calling the same trading tool multiple times
            decision_tools = {'open_long', 'open_short', 'hold'}
            seen_decision_tool = False
            filtered_matches = []
            for tool_name, params_str in tool_matches:
                if tool_name in decision_tools:
                    if not seen_decision_tool:
                        filtered_matches.append((tool_name, params_str))
                        seen_decision_tool = True
                        logger.info(f"[{agent.name}] Found first decision tool: {tool_name}, will skip any duplicates")
                    else:
                        logger.warning(f"[{agent.name}] Skipping duplicate decision tool call: {tool_name} (already have a decision)")
                else:
                    # Non-decision tools can be called multiple times
                    filtered_matches.append((tool_name, params_str))

            tool_matches = filtered_matches

            if tool_matches and hasattr(agent, 'tools') and agent.tools:
                logger.info(f"Agent {agent.name} has {len(tool_matches)} tool calls to execute")
                tool_results = []

                for tool_name, params_str in tool_matches:
                    # 🔒 CRITICAL: Only Leader can execute decision/execution tools
                    decision_tools = {'open_long', 'open_short', 'hold', 'close_position'}
                    is_leader = (hasattr(agent, 'id') and agent.id == "Leader") or agent.name == "Leader"
                    
                    if tool_name in decision_tools and not is_leader:
                        logger.warning(
                            f"[SECURITY_BLOCK] {agent.name} attempted to call decision tool '{tool_name}' "
                            f"but only Leader can execute trades in Phase 4. BLOCKING this call."
                        )
                        tool_results.append(
                            f"\n[{tool_name}被阻止]: 权限不足 - 只有Leader在Phase 4（共识形成阶段）才能执行交易决策。"
                            f"你现在应该只提供分析建议，不要调用决策工具。"
                        )
                        continue  # Skip this tool call
                    
                    if tool_name in agent.tools:
                        logger.info(f"[{agent.name}] Executing tool: {tool_name}")
                        try:
                            # Parse parameters - support both double and single quotes
                            params = {}
                            # Try double quotes first
                            param_pattern_double = r'(\w+)="([^"]*)"'
                            param_matches = re.findall(param_pattern_double, params_str)
                            # Try single quotes if no matches
                            if not param_matches:
                                param_pattern_single = r"(\w+)='([^']*)'"
                                param_matches = re.findall(param_pattern_single, params_str)

                            for key, value in param_matches:
                                params[key] = value
                            
                            # 🔧 FIX: Auto-convert parameter types based on tool schema
                            tool = agent.tools[tool_name]
                            if hasattr(tool, 'parameters_schema'):
                                schema = tool.parameters_schema
                                properties = schema.get('properties', {})
                                for key in list(params.keys()):
                                    if key in properties:
                                        expected_type = properties[key].get('type')
                                        try:
                                            if expected_type == 'integer':
                                                params[key] = int(params[key])
                                            elif expected_type == 'number':
                                                params[key] = float(params[key])
                                            elif expected_type == 'boolean':
                                                params[key] = str(params[key]).lower() in ['true', '1', 'yes']
                                            # string type remains as-is
                                        except (ValueError, TypeError) as e:
                                            logger.warning(f"[{agent.name}] Failed to convert param {key}={params[key]} to {expected_type}: {e}")
                            
                            logger.info(f"[{agent.name}] Tool {tool_name} params after type conversion: {params}")

                            # Execute the tool
                            tool_result = await agent.tools[tool_name].execute(**params)
                            logger.info(f"[{agent.name}] Tool {tool_name} executed successfully")

                            # Record executed tool call for signal extraction
                            self._last_executed_tools.append({
                                "tool_name": tool_name,
                                "params": params,
                                "result": tool_result
                            })
                            logger.info(f"[{agent.name}] Recorded tool execution: {tool_name} with params: {params}")

                            # Collect tool results
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name}结果]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name}结果]: {str(tool_result)[:1000]}")

                        except Exception as tool_error:
                            logger.error(f"[{agent.name}] Tool {tool_name} error: {tool_error}")
                            tool_results.append(f"\n[{tool_name}错误]: {str(tool_error)}")
                    else:
                        logger.warning(f"[{agent.name}] Tool {tool_name} not found in agent's tools")

                # If we have tool results, do a follow-up LLM call to get final analysis
                if tool_results:
                    logger.info(f"[{agent.name}] Making follow-up LLM call with tool results")
                    tool_results_text = "\n".join(tool_results)

                    follow_up_messages = messages + [
                        {"role": "assistant", "content": content},
                        {"role": "user", "content": f"Tool results:\n{tool_results_text}\n\nPlease provide your final analysis conclusion based on this real data. Note: Use the real data returned by tools, do not fabricate data. **Important: Do NOT call tools again, just summarize your analysis.**"}
                    ]

                    follow_up_response = await agent._call_llm(follow_up_messages)

                    # Extract content from follow-up response
                    if isinstance(follow_up_response, dict) and "choices" in follow_up_response:
                        try:
                            content = follow_up_response["choices"][0]["message"]["content"]
                        except (KeyError, IndexError):
                            pass
                    elif isinstance(follow_up_response, str):
                        content = follow_up_response
                    
                    # 🔒 CRITICAL FIX: Block tool calls in follow-up response
                    # Follow-up is ONLY for summary, should NOT execute tools again
                    follow_up_tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
                    follow_up_tool_matches = re.findall(follow_up_tool_pattern, content)
                    if follow_up_tool_matches:
                        logger.warning(f"[{agent.name}] ⚠️ Follow-up response contains {len(follow_up_tool_matches)} tool calls, BLOCKING them to prevent duplicate execution")
                        for tool_name, _ in follow_up_tool_matches:
                            logger.warning(f"[{agent.name}] Blocked tool call in follow-up: {tool_name}")
                        # Remove all tool call markers from follow-up content
                        content = re.sub(follow_up_tool_pattern, '[工具调用已阻止]', content)
                        logger.info(f"[{agent.name}] Follow-up content cleaned, tool calls removed")
            # ===== End Tool Execution =====

            logger.info(f"Agent {agent.name} response: {content[:100]}...")

            # Add to message history
            self._add_message(
                agent_id=agent.id,
                agent_name=agent.name,
                content=content,
                message_type="response"
            )

            return content

        except Exception as e:
            logger.error(f"Error in agent turn for {agent.name}: {e}")
            self._add_message(
                agent_id="system",
                agent_name="系统",
                content=f"❌ {agent.name} 分析失败: {str(e)[:100]}",
                message_type="error"
            )
            return ""

    def _get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        # self.agents is a dict {name: agent} from parent Meeting class
        for agent in self.agents.values():
            if agent.id == agent_id:
                return agent
        return None

    def _get_conversation_history(self) -> str:
        """Get formatted conversation history"""
        lines = []
        for msg in self.messages[-20:]:  # Last 20 messages
            lines.append(f"**{msg.get('agent_name', 'Unknown')}**: {msg.get('content', '')[:500]}")
        return "\n\n".join(lines)

    def _add_message(
        self,
        agent_id: str,
        agent_name: str,
        content: str,
        message_type: str = "message"
    ):
        """Add message to history and notify callback"""
        message = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "content": content,
            "type": message_type,
            "timestamp": datetime.now().isoformat()
        }

        if not hasattr(self, 'messages'):
            self.messages = []
        self.messages.append(message)

        if self.on_message:
            try:
                self.on_message(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")

    def _summarize_votes(self) -> str:
        """Summarize agent votes"""
        if not self._agent_votes:
            return "No votes yet"

        lines = []
        for vote in self._agent_votes:
            lines.append(
                f"- {vote.agent_name}: {vote.direction} "
                f"(confidence {vote.confidence}%, leverage {vote.suggested_leverage}x)"
            )

        # Count votes
        directions = [v.direction for v in self._agent_votes]
        long_count = directions.count("long")
        short_count = directions.count("short")
        hold_count = directions.count("hold")

        lines.append(f"\nSummary: Long {long_count}, Short {short_count}, Hold {hold_count}")

        return "\n".join(lines)

    def _parse_vote_json(self, agent_id: str, agent_name: str, response: str) -> Optional[AgentVote]:
        """
        Parse JSON-formatted voting signal from Agent response

        Prefer JSON parsing, more reliable than string matching
        """
        try:
            # Try to extract JSON code block from response
            json_data = self._extract_json_from_response(response)

            if not json_data:
                logger.warning(f"[{agent_name}] No valid JSON code block found")
                return None

            # Parse direction (supports multiple formats)
            raw_direction = json_data.get("direction", "hold").lower().strip()
            direction = self._normalize_direction(raw_direction)

            # Parse other fields
            confidence = int(json_data.get("confidence", self.config.min_confidence))
            leverage = int(json_data.get("leverage", 1))
            tp_percent = float(json_data.get("take_profit_percent", self.config.default_tp_percent))
            sl_percent = float(json_data.get("stop_loss_percent", self.config.default_sl_percent))
            reasoning = json_data.get("reasoning", "")

            # Validate value ranges
            confidence = max(0, min(100, confidence))
            leverage = max(1, min(leverage, self.config.max_leverage))
            tp_percent = max(0.1, min(tp_percent, 50.0))
            sl_percent = max(0.1, min(sl_percent, 50.0))

            logger.info(f"[{agent_name}] ✅ JSON parsed successfully: direction={direction}, confidence={confidence}%, leverage={leverage}x")

            return AgentVote(
                agent_id=agent_id,
                agent_name=agent_name,
                direction=direction,
                confidence=confidence,
                reasoning=reasoning[:500] if reasoning else response[:200],
                suggested_leverage=leverage,
                suggested_tp_percent=tp_percent,
                suggested_sl_percent=sl_percent
            )

        except json.JSONDecodeError as e:
            logger.warning(f"[{agent_name}] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[{agent_name}] Error parsing vote: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from Agent response

        Supports multiple formats:
        1. ```json ... ``` code block
        2. ``` ... ``` code block
        3. Direct JSON object {...}
        """
        import json

        # 策略1: 匹配 ```json ... ``` 代码块
        json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 策略2: 匹配 ``` ... ``` 代码块（不带 json 标记）
        code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if code_block_match:
            content = code_block_match.group(1).strip()
            if content.startswith('{'):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

        # 策略3: 直接匹配 JSON 对象（找最后一个，因为结论通常在最后）
        json_matches = list(re.finditer(r'\{[^{}]*"direction"[^{}]*\}', response, re.DOTALL))
        if json_matches:
            try:
                return json.loads(json_matches[-1].group())
            except json.JSONDecodeError:
                pass

        # 策略4: 更宽松的 JSON 匹配（多层嵌套）
        brace_matches = list(re.finditer(r'\{[\s\S]*?\}', response))
        for match in reversed(brace_matches):  # 从后往前尝试
            try:
                data = json.loads(match.group())
                if "direction" in data:
                    return data
            except json.JSONDecodeError:
                continue

        return None

    def _normalize_direction(self, raw_direction: str) -> str:
        """
        标准化交易方向字符串

        将各种输入格式统一转换为 long/short/hold
        """
        direction_map = {
            # Long 方向
            "long": "long",
            "做多": "long",
            "开多": "long",
            "买入": "long",
            "看多": "long",
            "add_long": "long",
            "追加多仓": "long",
            # Short 方向
            "short": "short",
            "做空": "short",
            "开空": "short",
            "卖出": "short",
            "看空": "short",
            "add_short": "short",
            "追加空仓": "short",
            # Hold 方向
            "hold": "hold",
            "观望": "hold",
            "等待": "hold",
            "不操作": "hold",
            "close": "hold",  # 平仓视为 hold（不开新仓）
            "平仓": "hold",
            "reverse": "hold",  # 反向需要特殊处理，暂时视为 hold
            "反向": "hold",
        }
        return direction_map.get(raw_direction, "hold")

    def _parse_vote_fallback(self, agent_id: str, agent_name: str, response: str) -> Optional[AgentVote]:
        """
        降级解析: 当 JSON 解析失败时，使用文本匹配作为备选

        保留原有的字符串匹配逻辑作为兜底
        """
        try:
            # Try to extract structured data - use config for defaults
            direction = "hold"
            confidence = self.config.min_confidence
            leverage = 1
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent

            # 使用改进的方向解析
            direction = self._extract_direction_from_response(response)

            # Parse confidence - support markdown format like **信心度**: **75%**
            conf_match = re.search(r'\*{0,2}信心度\*{0,2}[：:\s]*\*{0,2}(\d+)', response)
            if conf_match:
                confidence = int(conf_match.group(1))

            # Parse leverage - support formats like **建议杠杆**: **3倍**, 杠杆: 3, 3倍杠杆
            lev_match = re.search(r'\*{0,2}(?:建议)?杠杆\*{0,2}[：:\s]*\*{0,2}(\d+)', response)
            if not lev_match:
                lev_match = re.search(r'(\d+)\s*[倍x].*杠杆|杠杆.*?(\d+)\s*[倍x]', response)
            if lev_match:
                lev_value = lev_match.group(1) if lev_match.group(1) else lev_match.group(2)
                if lev_value:
                    leverage = int(lev_value)

            # Parse TP/SL
            tp_match = re.search(r'止盈[：:]\s*(\d+\.?\d*)', response)
            if tp_match:
                tp_percent = float(tp_match.group(1))

            sl_match = re.search(r'止损[：:]\s*(\d+\.?\d*)', response)
            if sl_match:
                sl_percent = float(sl_match.group(1))

            logger.info(f"[{agent_name}] ⚠️ 降级解析: direction={direction}, confidence={confidence}%")

            return AgentVote(
                agent_id=agent_id,
                agent_name=agent_name,
                direction=direction,
                confidence=confidence,
                reasoning=response[:200],
                suggested_leverage=min(leverage, self.config.max_leverage),
                suggested_tp_percent=tp_percent,
                suggested_sl_percent=sl_percent
            )

        except Exception as e:
            logger.error(f"[{agent_name}] Error parsing vote (fallback): {e}")
            logger.error(f"[{agent_name}] Response content: {response[:500]}")

            # Return None to signal parsing failure - caller will handle it
            return None

    def _extract_direction_from_response(self, response: str) -> str:
        """
        🔧 FIX: 从回复中提取交易方向，避免做多偏见

        改进策略：
        1. 首先查找结构化格式 "方向: XXX"
        2. 然后查找特定的决策关键词
        3. 最后统计关键词出现次数，取多数
        4. 避免匹配 "long-term" 等无关词
        """
        response_lower = response.lower()

        # 策略1: 查找结构化格式 "方向: XXX" 或 "- 方向: XXX"
        direction_match = re.search(
            r'[-\*]*\s*方向[：:\s]*[-\*]*\s*(做多|做空|观望|追加多仓|追加空仓|平仓|反向|long|short|hold)',
            response,
            re.IGNORECASE
        )
        if direction_match:
            raw_direction = direction_match.group(1).lower()
            if raw_direction in ['做多', 'long', '追加多仓']:
                return 'long'
            elif raw_direction in ['做空', 'short', '追加空仓']:
                return 'short'
            elif raw_direction in ['平仓', '反向']:
                # 平仓/反向需要看当前持仓，暂时返回 hold
                return 'hold'
            else:
                return 'hold'

        # 策略2: 查找明确的决策语句（在句子结尾或独立行）
        # 匹配 "建议做多"、"我认为应该做空"、"结论是做多" 等
        decision_patterns = [
            (r'建议[：:\s]*(做多|开多|买入|看多)', 'long'),
            (r'建议[：:\s]*(做空|开空|卖出|看空)', 'short'),
            (r'建议[：:\s]*(观望|持币|不操作|等待)', 'hold'),
            (r'结论[：:\s]*(做多|开多|买入|看多)', 'long'),
            (r'结论[：:\s]*(做空|开空|卖出|看空)', 'short'),
            (r'我(认为|建议|推荐).{0,10}(做多|开多|买入)', 'long'),
            (r'我(认为|建议|推荐).{0,10}(做空|开空|卖出)', 'short'),
            (r'(应该|可以|适合)(做多|开多|买入)', 'long'),
            (r'(应该|可以|适合)(做空|开空|卖出)', 'short'),
        ]

        for pattern, direction in decision_patterns:
            if re.search(pattern, response):
                logger.debug(f"[VoteParsing] Matched decision pattern: {pattern} -> {direction}")
                return direction

        # 策略3: 统计关键词出现次数（避免误匹配）
        # 使用更精确的匹配，排除 "long-term", "belong" 等
        long_keywords = ['做多', '开多', '买入', '看多', '多头']
        short_keywords = ['做空', '开空', '卖出', '看空', '空头']
        hold_keywords = ['观望', '持币观望', '等待', '不操作', '维持']

        # 计算每个方向的"强度"
        long_score = sum(response.count(kw) for kw in long_keywords)
        short_score = sum(response.count(kw) for kw in short_keywords)
        hold_score = sum(response.count(kw) for kw in hold_keywords)

        # 只有在英文环境下才检查 long/short，并排除常见误匹配
        # 使用单词边界匹配
        if re.search(r'\blong\b(?!\s*-?\s*term)', response_lower):
            long_score += 1
        if re.search(r'\bshort\b(?!\s*-?\s*term)', response_lower):
            short_score += 1

        logger.debug(f"[VoteParsing] Keyword scores: long={long_score}, short={short_score}, hold={hold_score}")

        # 取最高分，如果平局则返回 hold
        if long_score > short_score and long_score > hold_score:
            return 'long'
        elif short_score > long_score and short_score > hold_score:
            return 'short'
        else:
            return 'hold'

    async def _parse_signal(self, response: str) -> Optional[TradingSignal]:
        """Parse final trading signal from leader's response"""
        try:
            # Use config for all default values
            direction = "hold"
            confidence = self.config.min_confidence
            leverage = 1
            amount_percent = self.config.default_position_percent
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent

            # 🔧 FIX: 使用改进的方向解析方法，避免做多偏见
            direction = self._extract_direction_from_response(response)

            # Parse confidence - support multiple formats
            conf_match = re.search(r'\*{0,2}信心度\*{0,2}[：:\s]*(\d+)', response)
            if conf_match:
                confidence = int(conf_match.group(1))

            # Parse leverage - support multiple formats like "杠杆: 3", "**杠杆**: 3", "杠杆3倍"
            lev_match = re.search(r'\*{0,2}杠杆\*{0,2}[：:\s]*(\d+)', response)
            if not lev_match:
                lev_match = re.search(r'(\d+)\s*[倍x].*杠杆|杠杆.*?(\d+)\s*[倍x]', response)
            if lev_match:
                lev_value = lev_match.group(1) or lev_match.group(2) if lev_match.lastindex and lev_match.lastindex > 1 else lev_match.group(1)
                leverage = min(int(lev_value), self.config.max_leverage)

            # Log parsed leverage for debugging
            logger.info(f"Parsed leverage: {leverage} (max allowed: {self.config.max_leverage})")

            # Parse position size
            pos_match = re.search(r'仓位[：:]\s*(\d+\.?\d*)', response)
            if pos_match:
                raw_percent = float(pos_match.group(1)) / 100
                amount_percent = max(self.config.min_position_percent, min(raw_percent, self.config.max_position_percent))
                logger.info(f"Parsed position percent: {raw_percent*100:.1f}% -> clamped to {amount_percent*100:.1f}%")

            # Parse TP/SL percentages
            tp_match = re.search(r'止盈[：:]\s*(\d+\.?\d*)', response)
            if tp_match:
                tp_percent = float(tp_match.group(1))

            sl_match = re.search(r'止损[：:]\s*(\d+\.?\d*)', response)
            if sl_match:
                sl_percent = float(sl_match.group(1))

            # Get current BTC price from price service (use real price from CoinGecko)
            current_price = await get_current_btc_price(demo_mode=False)
            logger.info(f"Using real BTC price: ${current_price:,.2f}")

            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            elif direction == "short":
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            else:
                tp_price = current_price
                sl_price = current_price

            # Build consensus from votes
            consensus = {v.agent_name: v.direction for v in self._agent_votes}

            return TradingSignal(
                direction=direction,
                symbol=self.config.symbol,
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=current_price,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                confidence=confidence,
                reasoning=response[:500],
                agents_consensus=consensus
            )

        except Exception as e:
            logger.error(f"Error parsing signal: {e}")
            return None

    async def _parse_json_signal(self, response: str) -> Optional[TradingSignal]:
        """Parse trading signal from JSON format in response"""
        import json

        try:
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON object
                json_match = re.search(r'\{[^{}]*"direction"[^{}]*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.warning("No JSON found in response, falling back to regex parsing")
                    return await self._parse_signal(response)

            # Remove comments from JSON (LLM sometimes adds // comments)
            json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)
            # Remove trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)

            logger.info(f"Parsing JSON decision: {json_str[:200]}...")

            decision = json.loads(json_str)

            # Extract values with config-based defaults
            direction = decision.get("direction", "hold").lower()
            if direction not in ["long", "short", "hold"]:
                direction = "hold"

            confidence = int(decision.get("confidence", self.config.min_confidence))
            confidence = max(0, min(100, confidence))

            leverage = int(decision.get("leverage", 1))
            leverage = max(1, min(leverage, self.config.max_leverage))

            position_percent = float(decision.get("position_percent", self.config.default_position_percent * 100))
            raw_percent = position_percent / 100
            amount_percent = max(self.config.min_position_percent, min(raw_percent, self.config.max_position_percent))

            tp_percent = float(decision.get("take_profit_percent", self.config.default_tp_percent))
            sl_percent = float(decision.get("stop_loss_percent", self.config.default_sl_percent))

            reasoning = decision.get("reasoning", "")
            risks = decision.get("risks", "")

            logger.info(f"JSON Parsed - Direction: {direction}, Leverage: {leverage}x, Confidence: {confidence}%")

            # Get current BTC price from CoinGecko
            current_price = await get_current_btc_price(demo_mode=False)
            logger.info(f"Using real BTC price: ${current_price:,.2f}")

            # Calculate TP/SL prices
            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            elif direction == "short":
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            else:
                tp_price = current_price
                sl_price = current_price

            # Build consensus from votes
            consensus = {v.agent_name: v.direction for v in self._agent_votes}

            full_reasoning = f"{reasoning}\n\n风险提示: {risks}" if risks else reasoning

            return TradingSignal(
                direction=direction,
                symbol=self.config.symbol,
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=current_price,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                confidence=confidence,
                reasoning=full_reasoning[:500],
                agents_consensus=consensus
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}, falling back to regex parsing")
            return await self._parse_signal(response)
        except Exception as e:
            logger.error(f"Error parsing JSON signal: {e}")
            return await self._parse_signal(response)

    def _get_fallback_response(self, agent_id: str, agent_name: str) -> str:
        """
        Generate fallback response when Gemini content filter blocks the response.
        This provides a neutral, conservative response to keep the meeting going.
        """
        fallback_responses = {
            "MacroEconomist": """## 宏观经济分析 (数据获取受限)

我是**宏观经济分析师「全球视野」**。

由于数据获取暂时受限，我基于历史经验提供以下分析框架：

### 宏观评分: 5/10 (中性)

### 当前观察要点:
1. **利率环境**: 全球央行货币政策仍需关注
2. **流动性状况**: 市场流动性变化可能影响加密资产
3. **美元指数**: 美元走势与BTC通常呈负相关

### 宏观面建议:
- 建议方向: **观望**
- 当前宏观环境不确定性较高
- 建议等待更明确的宏观信号

### 风险提示:
宏观数据获取受限，建议更多依赖技术面和情绪面分析做出交易决策。""",

            "TechnicalAnalyst": """## 技术分析 (数据获取受限)

我是**技术分析师「图表大师」**。

由于技术数据获取暂时受限，建议参考以下分析框架：

### 技术评分: 5/10 (中性)

### 建议:
- 等待数据恢复后再进行详细技术分析
- 短期内建议观望""",

            "SentimentAnalyst": """## 情绪分析 (数据获取受限)

我是**情绪分析专家「人心洞察」**。

由于情绪数据获取暂时受限，提供以下参考：

### 情绪评分: 5/10 (中性)

### 建议:
- 当前无法获取实时恐慌贪婪指数
- 建议参考其他专家意见
- 短期内持谨慎态度""",

            "QuantStrategist": """## 量化分析 (数据获取受限)

我是**量化策略师「数据猎手」**。

由于量化数据获取暂时受限：

### 量化评分: 5/10 (中性)

### 建议:
- 数据不足，无法提供量化信号
- 建议观望等待数据恢复""",

            "RiskAssessor": """## 风险评估 (审慎模式)

我是**风险评估师「稳健守护」**。

由于部分数据获取受限，启用审慎模式：

### 风险评级: 中高

### 建议:
- 建议降低仓位比例
- 适当降低杠杆倍数
- 设置更严格的止损

### 风险管理建议:
数据不完整时应采取更保守的交易策略。"""
        }

        return fallback_responses.get(agent_id, f"""## {agent_name} 分析 (数据受限)

由于数据获取暂时受限，无法提供完整分析。

### 建议: 观望
### 信心度: 50%

建议参考其他专家意见做出决策。""")
    
