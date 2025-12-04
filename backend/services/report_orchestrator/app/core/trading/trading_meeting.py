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
from app.core.trading.agent_memory import get_memory_store, AgentMemoryStore
from app.core.trading.price_service import get_current_btc_price

logger = logging.getLogger(__name__)


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

        # Build the meeting agenda
        agenda = self._build_agenda(context)

        # Add agenda as initial message
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content=agenda,
            message_type="agenda"
        )

        try:
            # Phase 1: Market Analysis
            await self._run_market_analysis_phase()

            # Phase 2: Signal Generation (collect votes)
            await self._run_signal_generation_phase()

            # Phase 3: Risk Assessment
            await self._run_risk_assessment_phase()

            # Phase 4: Consensus Building
            signal = await self._run_consensus_phase()

            if signal:
                self._final_signal = signal

                # Notify callback
                if self.on_signal:
                    await self.on_signal(signal)

                # Phase 5: Execution (if not hold)
                if signal.direction != "hold":
                    await self._run_execution_phase(signal)

            return self._final_signal

        except Exception as e:
            logger.error(f"Error in trading meeting: {e}")
            self._add_message(
                agent_id="system",
                agent_name="系统",
                content=f"会议出现错误: {str(e)}",
                message_type="error"
            )
            return None

    def _build_agenda(self, context: Optional[str] = None) -> str:
        """Build the meeting agenda"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        reason = context or "定时分析"

        return f"""# 交易分析会议

**时间**: {now}
**标的**: {self.config.symbol}
**触发原因**: {reason}

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

    async def _run_market_analysis_phase(self):
        """Phase 1: Market Analysis"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段1: 市场分析\n\n请技术分析师、宏观经济分析师、情绪分析师开始分析市场。",
            message_type="phase"
        )

        # Run analysis agents (using agent names from ReWOO agents)
        # Agent.id defaults to agent.name in ReWOOAgent
        analysis_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst"]

        # 针对不同类型的agent提供不同的分析指令
        agent_prompts = {
            "TechnicalAnalyst": f"""请分析 {self.config.symbol} 的当前技术面状况。

**重要**: 你必须使用工具获取实时数据，不能凭空编造！

**工具调用格式** (必须严格遵守):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

请执行以下步骤:
1. [USE_TOOL: get_market_price(symbol="{self.config.symbol}")]
2. [USE_TOOL: get_klines(symbol="{self.config.symbol}", timeframe="4h", limit="100")]
3. [USE_TOOL: calculate_technical_indicators(symbol="{self.config.symbol}", timeframe="4h")]

基于真实数据分析:
- 当前价格和24h涨跌幅
- RSI、MACD、布林带等技术指标
- 趋势判断和关键支撑阻力位
- 你的技术面评分和交易建议""",

            "MacroEconomist": f"""请分析当前影响 {self.config.symbol} 的宏观经济环境。

**重要**: 你必须搜索最新信息，不能仅凭既有知识！

**工具调用格式** (必须严格遵守):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

请执行以下步骤 (直接复制这些工具调用):
1. [USE_TOOL: tavily_search(query="Bitcoin BTC market news today price analysis")]
2. [USE_TOOL: tavily_search(query="cryptocurrency institutional investment outlook")]

基于搜索结果分析:
- 当前市场流动性状况
- 机构投资者动向
- 美元指数与加密货币的相关性
- 你的宏观面评分和方向判断

**注意**: 聚焦于市场数据和投资分析，避免讨论敏感话题。""",

            "SentimentAnalyst": f"""请分析 {self.config.symbol} 的当前市场情绪。

**重要**: 你必须获取实时数据和搜索最新信息！

**工具调用格式** (必须严格遵守):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

请执行以下步骤 (直接复制这些工具调用):
1. [USE_TOOL: get_fear_greed_index()]
2. [USE_TOOL: get_funding_rate(symbol="{self.config.symbol}")]
3. [USE_TOOL: tavily_search(query="Bitcoin BTC market sentiment social media")]

基于真实数据分析:
- 恐慌贪婪指数数值和含义
- 资金费率及多空力量对比
- 社交媒体/新闻中的市场情绪
- 你的情绪面评分和方向判断""",

            "QuantStrategist": f"""请分析 {self.config.symbol} 的量化数据和统计信号。

**重要**: 你必须使用工具获取实时数据进行量化分析！

**工具调用格式** (必须严格遵守):
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

请执行以下步骤 (直接复制这些工具调用):
1. [USE_TOOL: get_market_price(symbol="{self.config.symbol}")]
2. [USE_TOOL: get_klines(symbol="{self.config.symbol}", timeframe="1h", limit="200")]
3. [USE_TOOL: calculate_technical_indicators(symbol="{self.config.symbol}", timeframe="1h")]

基于真实数据进行量化分析:
- 价格波动率和成交量分析
- 多时间周期趋势一致性
- 动量和趋势指标的量化信号
- 你的量化评分和方向判断"""
        }

        # 默认 prompt 也要求使用工具
        default_prompt = f"""请分析 {self.config.symbol} 的当前市场状况。

**重要**: 你必须使用工具获取实时数据，不能凭空编造！

请使用以下工具之一获取数据:
- `get_market_price` 获取当前价格
- `tavily_search` 搜索相关新闻

基于真实数据给出你的分析和观点。"""

        for agent_id in analysis_agents:
            agent = self._get_agent_by_id(agent_id)
            if agent:
                prompt = agent_prompts.get(agent_id, default_prompt)
                await self._run_agent_turn(agent, prompt)

    async def _run_signal_generation_phase(self):
        """Phase 2: Signal Generation"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段2: 信号生成\n\n请各位专家提出交易建议（做多/做空/观望）。",
            message_type="phase"
        )

        vote_prompt = f"""基于以上分析和你收集到的实时数据，请给出你的交易建议。

**注意**: 如果你在上一阶段没有使用工具获取数据，请现在使用相关工具获取最新信息再做判断！

⚠️ **重要提示 - 请勿调用决策工具**:
- 你现在处于"信号生成阶段"，只需要给出**文字建议**
- **不要**调用任何决策工具（open_long/open_short/hold/close_position）
- 只有Leader在"Phase 4: 共识形成阶段"才能执行交易
- 如果你调用了决策工具，系统会阻止并忽略

**重要：杠杆倍数必须与信心度严格对应！**
- 高信心度(>80%): 必须使用 {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}倍杠杆
- 中信心度(60-80%): 必须使用 {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}倍杠杆
- 低信心度(<60%): 使用 1-{int(self.config.max_leverage * 0.25)}倍杠杆或观望

请按以下格式回复：
- 方向: [做多/做空/观望]
- 信心度: [0-100]%
- 建议杠杆: [根据信心度选择对应区间的杠杆，最高{self.config.max_leverage}倍]
- 建议止盈: [X]%
- 建议止损: [X]%
- 理由: [简述，必须引用具体数据支撑你的判断]
"""

        vote_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst", "QuantStrategist"]
        for agent_id in vote_agents:
            agent = self._get_agent_by_id(agent_id)
            if agent:
                response = await self._run_agent_turn(agent, vote_prompt)
                vote = self._parse_vote(agent_id, agent.name, response)
                if vote:
                    self._agent_votes.append(vote)

    async def _run_risk_assessment_phase(self):
        """Phase 3: Risk Assessment"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段3: 风险评估\n\n请风险管理师评估交易风险。",
            message_type="phase"
        )

        # Summarize votes for risk manager
        votes_summary = self._summarize_votes()

        risk_agent = self._get_agent_by_id("RiskAssessor")
        if risk_agent:
            prompt = f"""以下是各专家的投票结果：

{votes_summary}

请评估这笔交易的风险，并决定是否批准。
如果批准，请给出最终的仓位建议和止盈止损设置。
如果不批准，请说明原因。

⚠️ **重要**: 
- 你只需要给出风险评估的**文字建议**
- **不要**调用任何决策工具（open_long/open_short/hold/close_position）
- 只有TradeExecutor（交易执行专员）在Phase 5才能执行交易
- 你的职责是评估风险，而非执行交易
"""
            await self._run_agent_turn(risk_agent, prompt)

    async def _run_consensus_phase(self) -> Optional[TradingSignal]:
        """Phase 4: Consensus Building - Leader makes final decision (WITHOUT execution)"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段4: 共识形成\n\n请主持人综合各方意见，形成最终交易决策。",
            message_type="phase"
        )

        # Use Leader for final decision (NO execution)
        leader = self._get_agent_by_id("Leader")
        if not leader:
            logger.error("Leader not found")
            return None

        # 🔧 Get current position context for Leader
        position_context = await self._get_position_context()

        # Get current account balance for position calculation
        account_info = ""
        try:
            # Leader没有tools了，需要从其他agent获取或使用toolkit
            # 这里简化，直接从paper_trader获取
            pass  # account_info later from position_context
        except Exception as e:
            logger.warning(f"Failed to get account balance: {e}")

        # 🔧 ARCHITECTURE CHANGE: Leader只决策，不执行
        prompt = f"""作为圆桌主持人，请综合以上所有讨论内容和专家意见，形成最终交易决策。

{position_context}

## 专家意见总结
你已经听取了以下专家的分析：
- 技术分析师 (TechnicalAnalyst): K线形态、技术指标分析
- 宏观经济分析师 (MacroEconomist): 宏观经济、货币政策分析
- 情绪分析师 (SentimentAnalyst): 市场情绪、资金流向分析
- 量化策略师 (QuantStrategist): 量化指标、统计分析
- 风险评估师 (RiskAssessor): 风险评估和建议

## 交易参数限制
- 最大杠杆: {self.config.max_leverage}倍
- 最大仓位: {int(self.config.max_position_percent * 100)}% 资金
- 最低信心度要求: {self.config.min_confidence}%

## 杠杆选择规则
**你必须严格按照信心度选择对应区间的杠杆倍数！**
- **高信心度 (>80%)**: **必须**使用 {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}倍杠杆
- **中信心度 (60-80%)**: **必须**使用 {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}倍杠杆
- **低信心度 (<60%)**: 使用 1-{int(self.config.max_leverage * 0.25)}倍杠杆 或选择观望

## 🎯 你的职责（重要）

⚠️ **关键：你只负责决策，不负责执行**
1. 你是决策者，不是执行者
2. 你的决策会传递给"交易执行专员"（TradeExecutor）
3. **不要调用任何工具！** 你没有工具执行权限
4. 只需要用结构化格式输出你的决策

## 决策流程

1. **分析当前状态**: 根据上方"当前持仓状态"，判断是无持仓还是有持仓
2. **综合专家意见**: 总结各专家的核心观点、一致性和分歧点
3. **评估信心度**: 根据专家意见一致性和市场信号强度，评估综合信心度 (0-100%)
4. **选择合适策略**: 
   - 如果**无持仓**: 开新仓或观望
   - 如果**有持仓**: 考虑持有/追加/平仓/反向（参考上方"决策参考"）
5. **输出结构化决策**: 按照下面的格式输出

## 📋 决策输出格式（必须严格遵守）

请按以下格式输出你的决策：

```
【最终决策】
- 决策: [做多/做空/观望/平仓/追加多仓/追加空仓]
- 标的: {self.config.symbol}
- 杠杆倍数: [1-{self.config.max_leverage}]
- 仓位比例: [0-100]%
- 止盈价格: [具体价格] USDT
- 止损价格: [具体价格] USDT
- 信心度: [0-100]%
- 决策理由: [综合分析，包括对历史持仓的考虑]
```

**示例1 (无持仓，看多开仓)**:
```
【最终决策】
- 决策: 做多
- 标的: BTC-USDT-SWAP
- 杠杆倍数: 5
- 仓位比例: 30%
- 止盈价格: 98000 USDT
- 止损价格: 92000 USDT
- 信心度: 75%
- 决策理由: 技术面突破关键阻力，宏观面美联储利好，情绪面贪婪指数回升，专家一致看多
```

**示例2 (有多仓，继续持有)**:
```
【最终决策】
- 决策: 观望
- 标的: BTC-USDT-SWAP
- 杠杆倍数: 0
- 仓位比例: 0%
- 止盈价格: 0 USDT
- 止损价格: 0 USDT
- 信心度: 60%
- 决策理由: 当前多仓盈利中，专家意见仍然看多，继续持有等待止盈触发
```

**示例3 (有多仓，追加仓位)**:
```
【最终决策】
- 决策: 追加多仓
- 标的: BTC-USDT-SWAP
- 杠杆倍数: 7
- 仓位比例: 20%
- 止盈价格: 100000 USDT
- 止损价格: 93000 USDT
- 信心度: 85%
- 决策理由: 当前多仓小幅盈利，技术面强势突破，专家强烈看多，资金充足可追加
```

⚠️ **重要提醒**:
- ❌ **不要调用任何工具**（你没有工具权限）
- ❌ 不要使用 [USE_TOOL: ...] 语法
- ✅ 只需要输出【最终决策】格式的文字
- ✅ 你的决策会由"交易执行专员"来执行

请开始你的决策分析！
"""

        response = await self._run_agent_turn(leader, prompt)

        # Extract signal from Leader's structured text output
        signal = await self._extract_signal_from_text(response)

        # Log meeting summary for monitoring
        vote_summary = self._get_vote_summary()
        logger.info(f"[Meeting Summary] Votes: {len(self._agent_votes)} collected, "
                   f"Decision: {signal.direction if signal else 'None'}, "
                   f"Vote breakdown: {vote_summary}")

        return signal

    def _get_vote_summary(self) -> str:
        """Get vote summary for logging"""
        if not self._agent_votes:
            return "no votes"
        directions = [v.direction for v in self._agent_votes]
        long_count = directions.count("long")
        short_count = directions.count("short")
        hold_count = directions.count("hold")
        return f"{long_count}L/{short_count}S/{hold_count}H"

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
            
            # Look for 【最终决策】 section
            decision_pattern = r'【最终决策】(.*?)(?=\n\n|$)'
            match = re.search(decision_pattern, response, re.DOTALL)
            
            if not match:
                logger.warning("[SignalExtraction] No 【最终决策】 section found in response")
                # Fallback: try to parse without the header
                decision_text = response
            else:
                decision_text = match.group(1)
            
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
                    direction = "close"
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
            
            # Get account and position
            account = paper_trader.get_account_status()
            position = paper_trader.get_position()
            
            has_position = position is not None
            
            # Calculate if can add more position
            can_add = False
            if has_position:
                current_value = position.get('position_value', 0)
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

    async def _run_execution_phase(self, signal: TradingSignal):
        """Phase 5: Trade Execution - TradeExecutor executes the Leader's decision"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content=f"## 阶段5: 交易执行\n\n交易执行专员正在执行Leader的决策...",
            message_type="phase"
        )
        
        # Import TradeExecutor
        from app.core.trading.trade_executor import TradeExecutor
        
        # Get paper_trader from toolkit if available
        paper_trader = None
        if hasattr(self, 'toolkit') and hasattr(self.toolkit, 'paper_trader'):
            paper_trader = self.toolkit.paper_trader
        
        # Create TradeExecutor
        executor = TradeExecutor(
            toolkit=self.toolkit if hasattr(self, 'toolkit') else None,
            paper_trader=paper_trader
        )
        
        # Get current position info for executor
        position_info = await self._get_position_info_dict()
        
        # Execute the signal
        logger.info(f"[Execution] Passing signal to TradeExecutor: {signal.direction}")
        execution_result = await executor.execute_signal(signal, position_info)
        
        # Log execution result
        logger.info(f"[Execution] TradeExecutor result: {execution_result}")
        
        # Update message based on execution result
        if execution_result.get('status') == 'success':
            self._add_message(
                agent_id="TradeExecutor",
                agent_name="交易执行专员",
                content=f"✅ 执行成功\n\n操作: {execution_result.get('action')}\n理由: {execution_result.get('reason')}",
                message_type="execution"
            )
        elif execution_result.get('status') == 'rejected':
            self._add_message(
                agent_id="TradeExecutor",
                agent_name="交易执行专员",
                content=f"⚠️ 执行被拒绝\n\n原因: {execution_result.get('reason')}",
                message_type="execution"
            )
        else:
            self._add_message(
                agent_id="TradeExecutor",
                agent_name="交易执行专员",
                content=f"❌ 执行失败\n\n错误: {execution_result.get('reason')}",
                message_type="execution"
            )
        
        # Store execution result
        self._execution_result = execution_result

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

            if memory.total_trades > 0:
                # Only inject memory if agent has trading history
                enhanced_system_prompt = f"""{base_system_prompt}

---
{memory_context}
---

请在分析时参考你的历史表现和经验教训，避免重复过去的错误。"""
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
                content = f"[{agent.name}] 分析完成，暂无明确建议。"

            # Handle blocked or empty responses from Gemini safety filter
            if "[Response blocked or empty]" in content or not content.strip():
                logger.warning(f"Agent {agent.name} response was blocked by content filter")
                content = self._get_fallback_response(agent.id, agent.name)

            # ===== Tool Execution (copied from agent._parse_llm_response) =====
            # Check for tool calls in the content using [USE_TOOL: tool_name(params)] format
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content)

            # Clear previous tool executions for this agent turn
            self._last_executed_tools = []

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
                        {"role": "user", "content": f"工具返回结果:\n{tool_results_text}\n\n请基于这些真实数据给出最终分析结论。注意：请使用工具返回的真实数据，不要编造数据。**重要：不要再次调用工具，只需要总结分析。**"}
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
            return "暂无投票"

        lines = []
        for vote in self._agent_votes:
            lines.append(
                f"- {vote.agent_name}: {vote.direction} "
                f"(信心度 {vote.confidence}%, 杠杆 {vote.suggested_leverage}x)"
            )

        # Count votes
        directions = [v.direction for v in self._agent_votes]
        long_count = directions.count("long")
        short_count = directions.count("short")
        hold_count = directions.count("hold")

        lines.append(f"\n统计: 做多 {long_count}, 做空 {short_count}, 观望 {hold_count}")

        return "\n".join(lines)

    def _parse_vote(self, agent_id: str, agent_name: str, response: str) -> Optional[AgentVote]:
        """Parse agent vote from response"""
        try:
            # Try to extract structured data - use config for defaults
            direction = "hold"
            confidence = self.config.min_confidence
            leverage = 1
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent

            # Parse direction
            if "做多" in response or "long" in response.lower():
                direction = "long"
            elif "做空" in response or "short" in response.lower():
                direction = "short"

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
            logger.error(f"[{agent_name}] Error parsing vote: {e}")
            logger.error(f"[{agent_name}] Response content: {response[:500]}")

            # Return None to signal parsing failure - caller will handle it
            # This makes parsing errors distinguishable from genuine "hold" votes
            return None

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

            # Parse direction
            if "做多" in response or "方向: long" in response.lower():
                direction = "long"
            elif "做空" in response or "方向: short" in response.lower():
                direction = "short"

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
    
    async def _get_position_context(self) -> str:
        """
        🔧 NEW: Get formatted position context for Leader's decision making.
        
        Returns detailed information about:
        - Current position status
        - Available balance and margin
        - Unrealized PnL
        - Position limits
        - Recommended actions based on position state
        """
        try:
            # Get position and account info from toolkit
            position_info = "### 当前持仓状态\n\n"
            
            # Try to get position through Leader's tools
            leader = self._get_agent_by_id("Leader")
            if not leader or not hasattr(leader, 'tools'):
                return position_info + "⚠️ 无法获取持仓信息（Leader工具不可用）\n"
            
            # Get current position
            has_position = False
            current_direction = None
            unrealized_pnl = 0
            pnl_percent = 0
            used_margin = 0
            position_leverage = 0
            
            if 'get_current_position' in leader.tools:
                try:
                    pos_result = await leader.tools['get_current_position'].execute()
                    if isinstance(pos_result, str):
                        pos_data = json.loads(pos_result)
                    else:
                        pos_data = pos_result
                    
                    has_position = pos_data.get('has_position', False)
                    if has_position:
                        current_direction = pos_data.get('direction', 'unknown')
                        unrealized_pnl = pos_data.get('unrealized_pnl', 0)
                        pnl_percent = pos_data.get('unrealized_pnl_percent', 0)
                        used_margin = pos_data.get('margin', 0)
                        position_leverage = pos_data.get('leverage', 0)
                        entry_price = pos_data.get('entry_price', 0)
                        current_price = pos_data.get('current_price', 0)
                        tp_price = pos_data.get('take_profit_price', 0)
                        sl_price = pos_data.get('stop_loss_price', 0)
                except Exception as e:
                    logger.warning(f"Failed to get position info: {e}")
            
            # Get account balance
            available_balance = self.config.default_balance
            total_equity = self.config.default_balance
            
            if 'get_account_balance' in leader.tools:
                try:
                    balance_result = await leader.tools['get_account_balance'].execute()
                    if isinstance(balance_result, str):
                        balance_data = json.loads(balance_result)
                    else:
                        balance_data = balance_result
                    
                    available_balance = balance_data.get('available_balance', self.config.default_balance)
                    total_equity = balance_data.get('total_equity', self.config.default_balance)
                    true_available_margin = balance_data.get('true_available_margin', available_balance)
                except Exception as e:
                    logger.warning(f"Failed to get account balance: {e}")
                    true_available_margin = available_balance
            else:
                true_available_margin = available_balance
            
            # Format position status
            if has_position:
                position_info += f"""**持仓状态**: ✅ 有持仓
**持仓方向**: {"🟢 做多 (LONG)" if current_direction == "long" else "🔴 做空 (SHORT)"}
**杠杆倍数**: {position_leverage}x
**入场价格**: ${entry_price:,.2f}
**当前价格**: ${current_price:,.2f}
**止盈价格**: ${tp_price:,.2f}
**止损价格**: ${sl_price:,.2f}
**未实现盈亏**: {"📈 +" if unrealized_pnl >= 0 else "📉 "} ${abs(unrealized_pnl):.2f} ({pnl_percent:+.2f}%)
**已用保证金**: ${used_margin:.2f}

"""
            else:
                position_info += """**持仓状态**: ❌ 无持仓
**当前状态**: 可以开新仓

"""
            
            # Account info
            position_info += f"""### 账户资金状况

**总权益**: ${total_equity:.2f}
**可用余额**: ${available_balance:.2f}
**真实可用保证金**: ${true_available_margin:.2f}
**已用保证金**: ${used_margin:.2f}

"""
            
            # Position limits and recommendations
            max_position_usdt = total_equity * self.config.max_position_percent
            min_position_usdt = total_equity * self.config.min_position_percent
            
            position_info += f"""### 仓位限制

**最大单次仓位**: {self.config.max_position_percent*100:.0f}% = ${max_position_usdt:.2f}
**最小单次仓位**: {self.config.min_position_percent*100:.0f}% = ${min_position_usdt:.2f}
**最大杠杆**: {self.config.max_leverage}x
**最低信心度**: {self.config.min_confidence}%

"""
            
            # Decision framework based on current state
            position_info += """### 决策参考

"""
            
            if not has_position:
                position_info += """**情况A: 无持仓状态**
- ✅ 可以根据专家意见开新仓（做多/做空）
- ✅ 或选择观望等待更好机会
- 📊 建议仓位范围: ${:.0f} - ${:.0f}

**可用决策**:
1. `[USE_TOOL: open_long(leverage="X", amount_usdt="XXXX", tp_percent="X.X", sl_percent="X.X")]`
2. `[USE_TOOL: open_short(leverage="X", amount_usdt="XXXX", tp_percent="X.X", sl_percent="X.X")]`
3. `[USE_TOOL: hold(reason="观望理由")]`

""".format(min_position_usdt, max_position_usdt)
            
            else:
                # Has position - provide detailed action recommendations
                remaining_capacity = max_position_usdt - used_margin
                can_add_position = remaining_capacity > min_position_usdt and true_available_margin > min_position_usdt
                
                position_info += f"""**情况B: 有持仓状态（{current_direction.upper()}）**

当前你需要考虑以下几种决策：

"""
                
                # Recommendation 1: Hold if direction aligns and profitable
                if unrealized_pnl > 0:
                    position_info += f"""**策略1️⃣: 继续持有现有{current_direction}仓**
- 当前盈利: +${unrealized_pnl:.2f} ({pnl_percent:+.2f}%)
- 适用场景: 专家意见与现有方向一致，且盈利情况良好
- 决策: `[USE_TOOL: hold(reason="继续持有盈利的{current_direction}仓位，理由...")]`

"""
                
                # Recommendation 2: Add position if capacity allows
                if can_add_position:
                    position_info += f"""**策略2️⃣: 追加{current_direction}仓位**
- 剩余容量: ${remaining_capacity:.2f}
- 真实可用保证金: ${true_available_margin:.2f}
- **适用场景**: 专家高度一致看{current_direction}，信心度提升
- ⚠️ 注意: 不要因为"已有持仓"就自动观望，如果信号强烈且资金充足，应该追加！
- 决策示例: `[USE_TOOL: open_{current_direction}(leverage="X", amount_usdt="{min(remaining_capacity, true_available_margin):.0f}", tp_percent="X.X", sl_percent="X.X")]`

"""
                else:
                    position_info += f"""**策略2️⃣: 无法追加仓位**
- 原因: {"已达仓位上限" if remaining_capacity <= min_position_usdt else "可用保证金不足"}
- 剩余容量: ${remaining_capacity:.2f}
- 真实可用保证金: ${true_available_margin:.2f}

"""
                
                # Recommendation 3: Close position if direction changed or risk high
                position_info += f"""**策略3️⃣: 平仓当前{current_direction}持仓**
- 适用场景1: 市场方向改变，专家意见转向相反方向
- 适用场景2: 浮亏过大（当前{pnl_percent:+.2f}%），风险控制需要止损
- 适用场景3: 技术指标转差，需要保护利润
- **如何操作**: 说明需要平仓，调用 `[USE_TOOL: hold(reason="建议平仓当前{current_direction}仓，原因...")]`
  （实际平仓会在后续处理）

"""
                
                # Recommendation 4: Reverse position
                opposite_direction = "short" if current_direction == "long" else "long"
                position_info += f"""**策略4️⃣: 反向操作（平{current_direction} + 开{opposite_direction}）**
- 适用场景: 市场趋势明确逆转，专家强烈建议{opposite_direction}
- 当前浮动: {pnl_percent:+.2f}%
- **操作**: 先通过hold说明需要平仓并反向
- 决策示例: `[USE_TOOL: hold(reason="市场反转，建议平掉{current_direction}仓后开{opposite_direction}仓")]`

"""
                
                position_info += """**⚠️ 决策关键点**:
1. **不要自动观望**: 即使有持仓，如果信号强烈且资金充足，应该追加
2. **评估方向一致性**: 现有持仓方向 vs 专家建议方向
3. **评估资金容量**: 是否还有追加空间
4. **评估风险收益**: 当前盈亏状况 vs 市场前景

"""
            
            return position_info
            
        except Exception as e:
            logger.error(f"Error getting position context: {e}")
            return f"### 持仓信息获取失败\n\n错误: {str(e)}\n\n请基于专家意见谨慎决策。\n"
