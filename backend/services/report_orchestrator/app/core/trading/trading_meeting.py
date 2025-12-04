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
from app.core.trading.position_context import PositionContext
# 🔧 TradeExecutorAgent已内联到TradeExecutorAgentWithTools，不再需要导入

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
                agent_name="系统",
                content=f"会议出现错误: {str(e)}",
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
            agent_name="系统",
            content="## 阶段1: 市场分析\n\n请技术分析师、宏观经济分析师、情绪分析师开始分析市场。",
            message_type="phase"
        )

        # Run analysis agents (using agent names from ReWOO agents)
        # Agent.id defaults to agent.name in ReWOOAgent
        analysis_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst"]

        # 🆕 持仓状况提示（用于所有分析师）
        position_hint = position_context.to_summary()

        # 针对不同类型的agent提供不同的分析指令
        agent_prompts = {
            "TechnicalAnalyst": f"""请分析 {self.config.symbol} 的当前技术面状况。

{position_hint}

⚠️ **请在分析时考虑当前持仓**: 如果有持仓，技术指标是支持持有、追加还是反向？

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
- {'如果有持仓: 技术面是否支持当前' + (position_context.direction or 'unknown') + '仓？' if position_context.has_position and position_context.direction else ''}
- 你的技术面评分和交易建议""",

            "MacroEconomist": f"""请分析当前影响 {self.config.symbol} 的宏观经济环境。

{position_hint}

⚠️ **请在分析时考虑当前持仓**: 如果有持仓，宏观面是否支持持有？

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
- {'如果有持仓: 宏观面是否支持当前' + (position_context.direction or 'unknown') + '仓？' if position_context.has_position and position_context.direction else ''}
- 你的宏观面评分和方向判断

**注意**: 聚焦于市场数据和投资分析，避免讨论敏感话题。""",

            "SentimentAnalyst": f"""请分析 {self.config.symbol} 的当前市场情绪。

{position_hint}

⚠️ **请在分析时考虑当前持仓**: {'情绪面是否支持当前' + (position_context.direction or 'unknown') + '仓？' if position_context.has_position and position_context.direction else ''}

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
- {'如果有持仓: 情绪面是否支持继续持有？' if position_context.has_position else ''}
- 你的情绪面评分和方向判断""",

            "QuantStrategist": f"""请分析 {self.config.symbol} 的量化数据和统计信号。

{position_hint}

⚠️ **请在分析时考虑当前持仓**: {'量化信号是否支持当前' + (position_context.direction or 'unknown') + '仓？' if position_context.has_position and position_context.direction else ''}

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
- {'如果有持仓: 统计上是否应该继续持有？' if position_context.has_position else ''}
- 你的量化评分和方向判断"""
        }

        # 默认 prompt 也要求使用工具
        default_prompt = f"""请分析 {self.config.symbol} 的当前市场状况。

{position_hint}

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

    async def _run_signal_generation_phase(self, position_context: PositionContext):
        """Phase 2: Signal Generation"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段2: 信号生成\n\n请各位专家提出交易建议（做多/做空/观望）。",
            message_type="phase"
        )

        # 🆕 根据持仓状态生成不同的决策选项提示
        decision_options = self._get_decision_options_for_analysts(position_context)

        vote_prompt = f"""基于以上分析和你收集到的实时数据，请给出你的交易建议。

{position_context.to_summary()}

{decision_options}

**注意**: 如果你在上一阶段没有使用工具获取数据，请现在使用相关工具获取最新信息再做判断！

⚠️ **重要提示 - 请勿调用决策工具**:
- 你现在处于"信号生成阶段"，只需要给出**文字建议**
- **不要**调用任何决策工具（open_long/open_short/hold/close_position）
- 只有TradeExecutor（交易执行专员）在Phase 5才能执行交易
- 如果你调用了决策工具，系统会阻止并忽略

**重要：杠杆倍数必须与信心度严格对应！**
- 高信心度(>80%): 必须使用 {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}倍杠杆
- 中信心度(60-80%): 必须使用 {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}倍杠杆
- 低信心度(<60%): 使用 1-{int(self.config.max_leverage * 0.25)}倍杠杆或观望

请按以下格式回复：
- 方向: [做多/做空/观望/追加多仓/追加空仓/平仓/反向]
- 信心度: [0-100]%
- 建议杠杆: [根据信心度选择对应区间的杠杆，最高{self.config.max_leverage}倍]
- 建议止盈: [X]%
- 建议止损: [X]%
- 理由: [简述，必须引用具体数据支撑你的判断，并说明是否考虑了当前持仓]
"""

        vote_agents = ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst", "QuantStrategist"]
        for agent_id in vote_agents:
            agent = self._get_agent_by_id(agent_id)
            if agent:
                response = await self._run_agent_turn(agent, vote_prompt)
                vote = self._parse_vote(agent_id, agent.name, response)
                if vote:
                    self._agent_votes.append(vote)

    async def _run_risk_assessment_phase(self, position_context: PositionContext):
        """Phase 3: Risk Assessment"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段3: 风险评估\n\n请风险管理师评估交易风险。",
            message_type="phase"
        )

        # Summarize votes for risk manager
        votes_summary = self._summarize_votes()

        # 🆕 生成持仓风险评估提示
        risk_context = self._generate_risk_context(position_context)

        risk_agent = self._get_agent_by_id("RiskAssessor")
        if risk_agent:
            prompt = f"""以下是各专家的投票结果：

{votes_summary}

{position_context.to_summary()}

{risk_context}

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
    
    def _generate_risk_context(self, position_context: PositionContext) -> str:
        """
        🆕 生成风险评估上下文
        
        帮助RiskAssessor评估当前持仓的风险
        """
        if not position_context.has_position:
            return """
## 🛡️ 风险评估重点（无持仓）

**评估要点**:
1. 开仓方向是否有充分依据？
2. 杠杆倍数是否与信心度匹配？
3. 止盈止损设置是否合理？
4. 仓位大小是否符合风险管理原则？
5. 当前市场波动率是否适合开仓？
"""
        
        # 有持仓
        direction = position_context.direction or "unknown"
        pnl = position_context.unrealized_pnl
        pnl_percent = position_context.unrealized_pnl_percent
        
        # 风险等级
        if position_context.distance_to_liquidation_percent > 50:
            risk_level = "🟢 安全"
        elif position_context.distance_to_liquidation_percent > 20:
            risk_level = "🟡 警戒"
        else:
            risk_level = "🔴 危险"
        
        # 接近TP/SL警告
        warnings = []
        if abs(position_context.distance_to_tp_percent) < 5:
            warnings.append(f"⚠️ 接近止盈（仅{abs(position_context.distance_to_tp_percent):.1f}%）")
        if abs(position_context.distance_to_sl_percent) < 5:
            warnings.append(f"🚨 接近止损（仅{abs(position_context.distance_to_sl_percent):.1f}%）")
        
        warnings_text = "\n".join(warnings) if warnings else "无特殊警告"
        
        return f"""
## 🛡️ 风险评估重点（有{direction.upper()}持仓）

**当前持仓风险**:
- 风险等级: {risk_level}
- 距离强平: {position_context.distance_to_liquidation_percent:.1f}%
- 浮动盈亏: ${pnl:.2f} ({pnl_percent:+.2f}%)
- 仓位占比: {position_context.current_position_percent*100:.1f}%

**风险警告**:
{warnings_text}

**评估要点**（根据专家建议类型）:

### 如果专家建议"继续看{direction}/追加"
1. 当前{direction}仓的盈亏状态如何？是否健康？
2. 追加后的总仓位是否超过风险上限？
3. 是否过于集中在单一方向？
4. 持仓时长是否已较长（当前{position_context.holding_duration_hours:.1f}小时）？

### 如果专家建议"平仓"
1. 平仓理由是否充分？
2. 当前盈亏状态是否适合平仓？
3. 是否止盈/止损的合适时机？

### 如果专家建议"反向操作"
1. 反向信号是否足够强？
2. 当前持仓是否盈利？平仓成本如何？
3. 反向后的新仓位风险如何？
4. 是否值得承担双重交易成本？

### 如果专家建议"观望"
1. 继续持有当前仓位的风险如何？
2. 是否应该主动平仓而非被动等待？

请综合评估，给出风险建议！
"""

    async def _run_consensus_phase(self, position_context: PositionContext) -> Optional[TradingSignal]:
        """
        Phase 4: Consensus Building - Leader总结会议
        
        NEW ARCHITECTURE:
        - Leader只负责总结会议讨论和专家意见
        - 不再输出结构化的交易决策
        - 决策由TradeExecutor在Phase 5做出
        """
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段4: 共识形成\n\n请主持人总结各位专家的意见，给出会议结论。",
            message_type="phase"
        )

        # Use Leader for meeting summary
        leader = self._get_agent_by_id("Leader")
        if not leader:
            logger.error("Leader not found")
            return None

        # 🆕 生成持仓感知的决策指导
        decision_guidance = self._generate_decision_guidance(position_context)

        # 🔧 NEW PROMPT: Leader作为主持人总结会议
        prompt = f"""作为圆桌主持人，请综合总结本次会议的讨论内容和专家意见。

{position_context.to_summary()}

{decision_guidance}

## 专家意见总结
你已经听取了以下专家的分析：
- 技术分析师 (TechnicalAnalyst): K线形态、技术指标分析
- 宏观经济分析师 (MacroEconomist): 宏观经济、货币政策分析
- 情绪分析师 (SentimentAnalyst): 市场情绪、资金流向分析
- 量化策略师 (QuantStrategist): 量化指标、统计分析
- 风险评估师 (RiskAssessor): 风险评估和建议

## 你的任务

作为主持人，请：

1. **总结专家共识**:
   - 有多少专家看多？多少看空？多少观望？
   - 各专家意见的核心理由是什么？
   - 专家之间有哪些一致性和分歧？

2. **综合市场判断**:
   - 基于所有讨论，你对当前市场的总体看法
   - 技术面、基本面、情绪面各方面的综合评估
   - 当前持仓状态下应该考虑的因素

3. **风险和机会评估**:
   - 当前的主要风险是什么？
   - 潜在的交易机会在哪里？
   - 对于当前持仓（如果有）的建议

4. **给出会议结论**:
   - 基于所有分析，你认为应该采取什么策略？
   - 建议的风险水平和仓位规模
   - 你的信心度如何？

## 📋 输出格式

请自由表达你的总结和建议，**不需要严格遵守特定格式**。

你可以自然地表达，例如：

"综合各位专家的意见，我认为...
- TechnicalAnalyst 和 SentimentAnalyst 都看多，理由是...
- 但 MacroEconomist 建议谨慎，因为...
- 考虑到当前{('无持仓' if not position_context.has_position else f'{position_context.direction}仓')}的状态...
我建议采取...策略，理由是...
建议的杠杆是...，仓位规模是...，我的信心度大约是...%"

⚠️ **重要提醒**:
- ✅ 用自然语言表达你的总结和建议
- ✅ 包含专家意见、你的判断、建议策略
- ✅ 不需要【最终决策】这样的标记
- ✅ 你的总结会传递给交易执行专员，他会根据你的建议做出最终决策

请开始你的总结！
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
        🆕 根据持仓状态生成决策指导
        
        帮助Leader理解在不同持仓状态下应该考虑哪些决策选项
        """
        if not position_context.has_position:
            # 无持仓
            return """
## 💡 决策指导（无持仓状态）

**可选操作**:
1. **做多** - 开多仓（如果专家看多）
2. **做空** - 开空仓（如果专家看空）
3. **观望** - 等待更好的时机

**决策要点**:
- 综合专家意见，判断方向
- 根据信心度选择杠杆（高信心=高杠杆）
- 根据信心度选择仓位（建议30-50%）
- 设置合理的止盈止损
"""
        
        # 有持仓
        direction = position_context.direction or "unknown"
        pnl = position_context.unrealized_pnl
        pnl_percent = position_context.unrealized_pnl_percent
        can_add = position_context.can_add_position
        
        # 判断盈亏状态
        pnl_status = "盈利" if pnl >= 0 else "亏损"
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        
        # 判断是否接近止盈止损
        near_tp = abs(position_context.distance_to_tp_percent) < 5
        near_sl = abs(position_context.distance_to_sl_percent) < 5
        
        guidance = f"""
## 💡 决策指导（有{direction.upper()}持仓）

**当前持仓状态**: {pnl_emoji} {pnl_status} ${abs(pnl):.2f} ({pnl_percent:+.2f}%)
"""
        
        if near_tp:
            guidance += f"""
⚠️ **接近止盈**: 距离止盈价仅 {abs(position_context.distance_to_tp_percent):.1f}%
"""
        
        if near_sl:
            guidance += f"""
🚨 **接近止损**: 距离止损价仅 {abs(position_context.distance_to_sl_percent):.1f}%
"""
        
        guidance += f"""
**可选操作**:
1. **观望** - 继续持有当前{direction}仓（如果专家仍然看{direction}）
2. **追加{direction}仓** - 追加同方向仓位（如果专家强烈看{direction}，且{'可追加' if can_add else '❌已满仓，不可追加'}）
3. **平仓** - 平掉当前{direction}仓（如果专家转为中性，或止盈/止损）
4. **反向操作** - 平掉{direction}仓，开{'空' if direction == 'long' else '多'}仓（如果专家强烈反向）

**决策矩阵**（重要参考）:

| 专家意见 | 持仓状态 | 建议操作 | 理由 |
|---------|---------|---------|------|
| 继续看{direction} | {'可追加' if can_add else '已满仓'} | {'追加' + direction + '仓' if can_add else '观望（已满仓）'} | 趋势延续，{'资金充足可追加' if can_add else '仓位已满，维持即可'} |
| 中性/观望 | {pnl_status}中 | {'观望' if pnl >= 0 else '考虑平仓'} | {'盈利中，继续持有' if pnl >= 0 else '亏损中，止损考虑'} |
| 转为看{'空' if direction == 'long' else '多'} | {pnl_status}中 | 反向操作 | 趋势反转，平仓+反向 |
| 强烈看{'空' if direction == 'long' else '多'} | 任何状态 | 反向操作 | 强反转信号，立即反向 |

**决策要点**:
- **优先考虑**当前持仓的盈亏状态
- **评估**专家意见是否与持仓方向一致
- **判断**是否接近止盈止损触发点
- **考虑**持仓时长（已持有 {position_context.holding_duration_hours:.1f} 小时）
- **计算**追加或反向操作的风险收益比
"""
        
        return guidance
    
    def _get_decision_options_for_analysts(self, position_context: PositionContext) -> str:
        """
        🆕 为分析师生成决策选项提示
        
        根据持仓状态，告诉分析师他们可以建议哪些操作
        """
        if not position_context.has_position:
            return """
## 💡 决策选项（当前无持仓）

你可以建议以下操作:
1. **做多** - 如果你认为价格会上涨
2. **做空** - 如果你认为价格会下跌
3. **观望** - 如果你认为时机不成熟或方向不明

请基于你的专业领域给出建议。
"""
        
        # 有持仓
        direction = position_context.direction or "unknown"
        opposite = "空" if direction == "long" else "多"
        can_add = "✅ 可以" if position_context.can_add_position else "❌ 已满仓，不可以"
        
        return f"""
## 💡 决策选项（当前有{direction.upper()}持仓）

你可以建议以下操作:
1. **观望/维持** - 如果你认为应该继续持有当前{direction}仓
2. **追加{direction}仓** - 如果你强烈看{direction}（当前{can_add}追加）
3. **平仓** - 如果你认为应该止盈或止损
4. **反向操作** - 如果你认为市场反转，应该平{direction}开{opposite}

**当前持仓参考**:
- 方向: {direction.upper()}
- 盈亏: ${position_context.unrealized_pnl:.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- 仓位: {position_context.current_position_percent*100:.1f}%
- 持仓时长: {position_context.holding_duration_hours:.1f}小时

请基于你的专业领域和当前持仓状态给出建议。
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
            current_position = position.get('position', {})
            if not current_position:
                logger.warning("[PositionContext] position.position is empty, treating as no position")
                return PositionContext(
                    has_position=False,
                    available_balance=account.get('available_balance', self.config.default_balance),
                    total_equity=account.get('total_equity', self.config.default_balance),
                    used_margin=account.get('used_margin', 0),
                    max_position_percent=self.config.max_position_percent,
                    can_add_position=False
                )
            
            direction = current_position.get('direction', '')
            entry_price = current_position.get('entry_price', 0)
            current_price = current_position.get('current_price', 0)
            size = current_position.get('size', 0)
            leverage = current_position.get('leverage', 1)
            margin_used = current_position.get('margin', 0)
            unrealized_pnl = current_position.get('unrealized_pnl', 0)
            unrealized_pnl_percent = current_position.get('unrealized_pnl_percent', 0)
            liquidation_price = current_position.get('liquidation_price', 0)
            take_profit_price = current_position.get('take_profit_price')
            stop_loss_price = current_position.get('stop_loss_price')
            opened_at_str = current_position.get('opened_at')
            
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
            agent_name="系统",
            content=f"## 阶段5: 交易执行\n\n交易执行专员正在分析会议结果并做出决策...",
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
            self._add_message(
                agent_id="trade_executor",
                agent_name="交易执行专员",
                content=f"""## TradeExecutor的最终决策

**决策**: {final_signal.direction.upper()}
**杠杆**: {final_signal.leverage}x
**仓位**: {final_signal.amount_percent*100:.0f}%
**信心度**: {final_signal.confidence}%

**止盈**: ${final_signal.take_profit_price:,.2f}
**止损**: ${final_signal.stop_loss_price:,.2f}

**决策理由**:
{final_signal.reasoning}
""",
                metadata={"signal": final_signal.dict()}
            )
            
            # Step 6: 记录执行结果（工具函数已经执行过交易，无需再次执行！）
            # 🔧 核心改变: TradeExecutorAgentWithTools的工具函数已经直接执行了交易
            # open_long/open_short/close_position 函数内部调用了 paper_trader.open_position()
            # 所以这里只需要记录结果，不需要再调用LegacyExecutor
            
            if final_signal.direction != "hold":
                logger.info(f"[ExecutionPhase] ✅ 交易已由Tool Calling执行: {final_signal.direction.upper()}")
                
                self._add_message(
                    agent_id="trade_executor",
                    agent_name="交易执行专员",
                    content=f"✅ 交易已执行\n\n决策: {final_signal.direction.upper()}\n杠杆: {final_signal.leverage}x\n仓位: {final_signal.amount_percent*100:.0f}%",
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
            else:
                logger.info("[ExecutionPhase] 📊 决策为观望，无交易执行")
                self._execution_result = {
                    "status": "hold",
                    "action": "hold",
                    "reason": final_signal.reasoning
                }
            
            # Store final signal
            self._final_signal = final_signal
            
        except Exception as e:
            logger.error(f"[ExecutionPhase] ❌ 执行阶段失败: {e}", exc_info=True)
            self._add_message(
                agent_id="system",
                agent_name="系统",
                content=f"❌ 交易执行阶段失败: {str(e)}",
                message_type="error"
            )
            # 返回hold信号
            self._final_signal = await self._create_hold_signal(
                "",
                f"执行阶段失败: {str(e)}"
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
                        price_match = re.search(r'\$?([\d,]+\.?\d*)', result)
                        if price_match:
                            return float(price_match.group(1).replace(',', ''))
                    elif isinstance(result, (int, float)):
                        return float(result)
                
                if toolkit and hasattr(toolkit, 'paper_trader'):
                    if hasattr(toolkit.paper_trader, 'current_price'):
                        return float(toolkit.paper_trader.current_price)
            except Exception as e:
                logger.error(f"[TradeExecutor] 获取价格失败: {e}")
            return 93000.0  # fallback
        
        async def open_long_tool(leverage: int = 5, amount_percent: float = 0.4, 
                                confidence: int = 70, reasoning: str = "") -> str:
            """
            开多仓（做多BTC）
            
            Args:
                leverage: 杠杆倍数 1-20
                amount_percent: 仓位比例 0.0-1.0
                confidence: 信心度 0-100
                reasoning: 决策理由
            """
            current_price = await get_current_price()
            take_profit = current_price * 1.08  # 默认8%止盈
            stop_loss = current_price * 0.97    # 默认3%止损
            
            leverage = min(max(int(leverage), 1), 20)
            amount_percent = min(max(float(amount_percent), 0.0), 1.0)
            
            # 执行交易
            trade_success = False
            entry_price = current_price
            if toolkit and toolkit.paper_trader:
                try:
                    # 🔧 FIX: paper_trader.open_long需要amount_usdt，而不是amount_percent
                    # 先获取账户余额，计算实际金额
                    account = await toolkit.paper_trader.get_account()
                    available_balance = account.get("available_balance", 0) or account.get("balance", 10000)
                    amount_usdt = available_balance * amount_percent
                    
                    logger.info(f"[TradeExecutor] 开多仓参数: 余额=${available_balance:.2f}, "
                               f"仓位比例={amount_percent*100:.0f}%, 金额=${amount_usdt:.2f}")
                    
                    result = await toolkit.paper_trader.open_long(
                        symbol="BTC-USDT-SWAP",
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=take_profit,
                        sl_price=stop_loss
                    )
                    
                    if result.get("success"):
                        trade_success = True
                        entry_price = result.get("executed_price", current_price)
                        logger.info(f"[TradeExecutor] ✅ 开多仓成功: {leverage}x, ${amount_usdt:.2f}, 入场价${entry_price:.2f}")
                    else:
                        error_msg = result.get("error", "未知错误")
                        logger.error(f"[TradeExecutor] 开多仓失败: {error_msg}")
                        reasoning = f"开仓执行失败: {error_msg}. " + reasoning
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] 开多仓异常: {e}")
                    reasoning = f"开仓执行异常: {e}. " + reasoning
            
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
                reasoning=reasoning or "TradeExecutor决定做多",
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            return f"✅ 开多仓{'成功' if trade_success else '失败'}: {leverage}x杠杆, {amount_percent*100:.0f}%仓位, 入场价${entry_price:,.2f}"
        
        async def open_short_tool(leverage: int = 5, amount_percent: float = 0.4,
                                 confidence: int = 70, reasoning: str = "") -> str:
            """
            开空仓（做空BTC）
            
            Args:
                leverage: 杠杆倍数 1-20
                amount_percent: 仓位比例 0.0-1.0
                confidence: 信心度 0-100
                reasoning: 决策理由
            """
            current_price = await get_current_price()
            take_profit = current_price * 0.92  # 默认8%止盈（做空）
            stop_loss = current_price * 1.03    # 默认3%止损（做空）
            
            leverage = min(max(int(leverage), 1), 20)
            amount_percent = min(max(float(amount_percent), 0.0), 1.0)
            
            # 执行交易
            trade_success = False
            entry_price = current_price
            if toolkit and toolkit.paper_trader:
                try:
                    # 🔧 FIX: paper_trader.open_short需要amount_usdt，而不是amount_percent
                    account = await toolkit.paper_trader.get_account()
                    available_balance = account.get("available_balance", 0) or account.get("balance", 10000)
                    amount_usdt = available_balance * amount_percent
                    
                    logger.info(f"[TradeExecutor] 开空仓参数: 余额=${available_balance:.2f}, "
                               f"仓位比例={amount_percent*100:.0f}%, 金额=${amount_usdt:.2f}")
                    
                    result = await toolkit.paper_trader.open_short(
                        symbol="BTC-USDT-SWAP",
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=take_profit,
                        sl_price=stop_loss
                    )
                    
                    if result.get("success"):
                        trade_success = True
                        entry_price = result.get("executed_price", current_price)
                        logger.info(f"[TradeExecutor] ✅ 开空仓成功: {leverage}x, ${amount_usdt:.2f}, 入场价${entry_price:.2f}")
                    else:
                        error_msg = result.get("error", "未知错误")
                        logger.error(f"[TradeExecutor] 开空仓失败: {error_msg}")
                        reasoning = f"开仓执行失败: {error_msg}. " + reasoning
                        
                except Exception as e:
                    logger.error(f"[TradeExecutor] 开空仓异常: {e}")
                    reasoning = f"开仓执行异常: {e}. " + reasoning
            
            execution_result["signal"] = TradingSignal(
                direction="short",
                symbol="BTC-USDT-SWAP",
                leverage=leverage,
                amount_percent=amount_percent,
                entry_price=entry_price,
                take_profit_price=take_profit,
                stop_loss_price=stop_loss,
                confidence=confidence,
                reasoning=reasoning or "TradeExecutor决定做空",
                agents_consensus={},
                timestamp=datetime.now()
            )
            
            return f"✅ 开空仓{'成功' if trade_success else '失败'}: {leverage}x杠杆, {amount_percent*100:.0f}%仓位, 入场价${current_price:,.2f}"
        
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
        trade_executor = Agent(
            agent_id="trade_executor",
            name="TradeExecutor",
            role="交易执行决策专员",
            system_prompt="""你是交易执行专员 (TradeExecutor)，负责根据专家会议结果执行交易。

你必须通过调用工具来执行决策，可用工具:
- open_long: 开多仓（做多BTC）
- open_short: 开空仓（做空BTC）
- close_position: 平仓当前持仓
- hold: 观望不操作

决策规则:
1. 专家3-4票一致看多 → 调用open_long
2. 专家3-4票一致看空 → 调用open_short
3. 专家意见分歧或不明朗 → 调用hold
4. 有反向持仓需要平仓 → 调用close_position

你必须根据会议结果调用一个工具！""",
            llm_endpoint=leader.llm_endpoint if hasattr(leader, 'llm_endpoint') else "http://llm_gateway:8003",
            temperature=0.3
        )
        
        # 注册交易工具（使用FunctionTool包装）
        trade_executor.register_tool(FunctionTool(
            name="open_long",
            description="开多仓（做多BTC）- 当专家共识看涨时调用",
            func=open_long_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "杠杆倍数1-20"},
                    "amount_percent": {"type": "number", "description": "仓位比例0.0-1.0"},
                    "confidence": {"type": "integer", "description": "信心度0-100"},
                    "reasoning": {"type": "string", "description": "决策理由"}
                },
                "required": ["leverage", "amount_percent"]
            }
        ))
        
        trade_executor.register_tool(FunctionTool(
            name="open_short",
            description="开空仓（做空BTC）- 当专家共识看跌时调用",
            func=open_short_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "杠杆倍数1-20"},
                    "amount_percent": {"type": "number", "description": "仓位比例0.0-1.0"},
                    "confidence": {"type": "integer", "description": "信心度0-100"},
                    "reasoning": {"type": "string", "description": "决策理由"}
                },
                "required": ["leverage", "amount_percent"]
            }
        ))
        
        trade_executor.register_tool(FunctionTool(
            name="close_position",
            description="平仓当前持仓 - 当需要止盈止损或反向操作时调用",
            func=close_position_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "平仓理由"}
                }
            }
        ))
        
        trade_executor.register_tool(FunctionTool(
            name="hold",
            description="观望不操作 - 当市场不明朗或专家意见分歧时调用",
            func=hold_tool,
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "观望原因"}
                },
                "required": ["reason"]
            }
        ))
        
        logger.info(f"[TradeExecutor] ✅ 创建Agent成功，注册了{len(trade_executor.tools)}个交易工具")
        
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
                    # 提取参数
                    leverage_match = re.search(r'(\d+)\s*[倍xX]', text)
                    leverage = int(leverage_match.group(1)) if leverage_match else 5
                    
                    amount_match = re.search(r'(\d+)\s*%', text)
                    amount = (int(amount_match.group(1)) / 100) if amount_match else 0.4
                    
                    confidence_match = re.search(r'信心[度]?\s*[:：]?\s*(\d+)', text)
                    confidence = int(confidence_match.group(1)) if confidence_match else 70
                    
                    logger.info(f"[TradeExecutor] 📊 从文本推断做多: {leverage}x, {amount*100:.0f}%")
                    await self.tools['open_long'](
                        leverage=min(leverage, 20),
                        amount_percent=min(amount, 1.0),
                        confidence=confidence,
                        reasoning=text[:200]
                    )
                    
                elif any(kw in text_lower for kw in ['做空', '开空', 'short', '看跌', '卖出']):
                    leverage_match = re.search(r'(\d+)\s*[倍xX]', text)
                    leverage = int(leverage_match.group(1)) if leverage_match else 5
                    
                    amount_match = re.search(r'(\d+)\s*%', text)
                    amount = (int(amount_match.group(1)) / 100) if amount_match else 0.4
                    
                    confidence_match = re.search(r'信心[度]?\s*[:：]?\s*(\d+)', text)
                    confidence = int(confidence_match.group(1)) if confidence_match else 70
                    
                    logger.info(f"[TradeExecutor] 📊 从文本推断做空: {leverage}x, {amount*100:.0f}%")
                    await self.tools['open_short'](
                        leverage=min(leverage, 20),
                        amount_percent=min(amount, 1.0),
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
        构建执行阶段的prompt
        
        这个prompt会发送给TradeExecutor的LLM，让它调用工具执行交易
        """
        
        # 格式化投票
        long_count = sum(1 for v in agents_votes.values() if v == 'long')
        short_count = sum(1 for v in agents_votes.values() if v == 'short')
        hold_count = sum(1 for v in agents_votes.values() if v == 'hold')
        
        vote_details = []
        for agent, vote in agents_votes.items():
            emoji = "🟢" if vote == "long" else "🔴" if vote == "short" else "⚪"
            vote_text = "做多" if vote == "long" else "做空" if vote == "short" else "观望"
            vote_details.append(f"  {emoji} {agent}: {vote_text}")
        
        # 格式化持仓状态
        if position_context.has_position:
            direction = position_context.direction or "unknown"
            position_status = f"""**有持仓** ({direction.upper()})
- 入场价: ${position_context.entry_price:,.2f}
- 当前价: ${position_context.current_price:,.2f}
- 持仓量: {position_context.size:.4f} BTC
- 杠杆: {position_context.leverage}x
- 浮动盈亏: ${position_context.unrealized_pnl:,.2f} ({position_context.unrealized_pnl_percent:+.2f}%)
- 可用余额: ${position_context.available_balance:,.2f}"""
        else:
            position_status = f"""**无持仓**
- 可用余额: ${position_context.available_balance:,.2f}
- 总权益: ${position_context.total_equity:,.2f}"""
        
        prompt = f"""## 交易执行任务

### 1. 专家投票结果
**统计**: {long_count}票做多 / {short_count}票做空 / {hold_count}票观望

{chr(10).join(vote_details)}

### 2. 当前持仓状态
{position_status}

### 3. Leader的会议总结
{leader_summary}

---

### 你的任务
根据以上信息，**必须调用一个工具**来执行交易决策。

**决策规则**:
- 3-4票一致看多 → 调用 open_long(leverage=5-10, amount_percent=0.4-0.6)
- 3-4票一致看空 → 调用 open_short(leverage=5-10, amount_percent=0.4-0.6)
- 2票左右 → 谨慎操作 (leverage=3-5, amount_percent=0.2-0.4)
- 意见分歧或不明朗 → 调用 hold(reason="...")
- 有反向持仓需要处理 → 先调用 close_position()

**输出格式（必须遵守）**:
[USE_TOOL: 工具名(参数=值, ...)]

现在，请分析并调用工具执行你的决策。"""
        
        return prompt
    
    def _get_leader_final_summary(self) -> str:
        """获取Leader的最后一条消息作为会议总结"""
        if not hasattr(self, 'message_bus') or not self.message_bus:
            self.logger.warning("[TradingMeeting] message_bus不存在")
            return "无会议记录"
        
        # 🔧 FIX: MessageBus使用message_history而不是messages
        messages = getattr(self.message_bus, 'message_history', [])
        if not messages:
            return "无会议消息"
        
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
        
        return "Leader未发言（可能LLM失败）"

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
                                tool_results.append(f"\n[{tool_name}结果]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name}结果]: {str(tool_result)[:1000]}")
                                
                        except Exception as e:
                            logger.error(f"[{agent.name}] Native tool execution failed: {e}")
                            tool_results.append(f"\n[{tool_name}错误]: {str(e)}")
                
                # If we have tool results, do a follow-up LLM call
                if tool_results:
                    logger.info(f"[{agent.name}] Making follow-up LLM call with native tool results")
                    tool_results_text = "\n".join(tool_results)
                    
                    follow_up_messages = messages + [
                        {"role": "assistant", "content": content or ""},
                        {"role": "user", "content": f"工具返回结果:\n{tool_results_text}\n\n请基于这些真实数据给出最终分析结论。"}
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
    
