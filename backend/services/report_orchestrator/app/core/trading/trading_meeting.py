"""
Trading Meeting

Specialized roundtable meeting for trading decisions.
Extends the base Meeting class with trading-specific phases and signal generation.
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

from app.core.roundtable.meeting import Meeting
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
    """Configuration for trading meeting"""
    symbol: str = "BTC-USDT-SWAP"
    max_leverage: int = 20
    max_position_percent: float = 0.3  # 最大仓位百分比 (30%)
    min_position_percent: float = 0.1  # 最小仓位百分比 (10%)
    default_position_percent: float = 0.2  # 默认仓位百分比 (20%)
    min_confidence: int = 60
    max_rounds: int = 3
    require_risk_manager_approval: bool = True
    # 默认止盈止损百分比
    default_tp_percent: float = 5.0
    default_sl_percent: float = 2.0
    # 默认余额（用于计算，如果无法获取实际余额）
    default_balance: float = 10000.0
    # 回退价格（仅在无法获取实时价格时使用）
    fallback_price: float = 95000.0


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
        retry_handler: Optional[RetryHandler] = None
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

        self._agent_votes: List[AgentVote] = []
        self._final_signal: Optional[TradingSignal] = None
        self._execution_result: Optional[Dict] = None
        self._memory_store: Optional[AgentMemoryStore] = None

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

请执行以下步骤:
1. 使用 `get_market_price` 获取当前价格
2. 使用 `get_klines` 获取K线数据
3. 使用 `calculate_technical_indicators` 计算技术指标

基于真实数据分析:
- 当前价格和24h涨跌幅
- RSI、MACD、布林带等技术指标
- 趋势判断和关键支撑阻力位
- 你的技术面评分和交易建议""",

            "MacroEconomist": f"""请分析当前影响 {self.config.symbol} 的宏观经济环境。

**重要**: 你必须搜索最新信息，不能仅凭既有知识！

请执行以下步骤:
1. 使用 `tavily_search` 搜索最新的加密货币/宏观经济新闻
2. 搜索 "Fed interest rate decision" 或 "美联储利率" 等关键词
3. 搜索 "Bitcoin regulation news" 或 "加密货币监管" 等关键词

基于搜索结果分析:
- 当前货币政策环境（利率、流动性）
- 影响市场的重大政策/监管动态
- 宏观经济对加密货币的影响
- 你的宏观面评分和方向判断""",

            "SentimentAnalyst": f"""请分析 {self.config.symbol} 的当前市场情绪。

**重要**: 你必须获取实时数据和搜索最新信息！

请执行以下步骤:
1. 使用 `get_fear_greed_index` 获取恐慌贪婪指数
2. 使用 `get_funding_rate` 获取资金费率
3. 使用 `tavily_search` 搜索 "Bitcoin sentiment" 或 "BTC market sentiment" 获取市场情绪新闻

基于真实数据分析:
- 恐慌贪婪指数数值和含义
- 资金费率及多空力量对比
- 社交媒体/新闻中的市场情绪
- 你的情绪面评分和方向判断""",

            "QuantStrategist": f"""请分析 {self.config.symbol} 的量化数据和统计信号。

**重要**: 你必须使用工具获取实时数据进行量化分析！

请执行以下步骤:
1. 使用 `get_market_price` 获取当前价格和成交量
2. 使用 `get_klines` 获取历史K线数据
3. 使用 `calculate_technical_indicators` 计算技术指标

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
"""
            await self._run_agent_turn(risk_agent, prompt)

    async def _run_consensus_phase(self) -> Optional[TradingSignal]:
        """Phase 4: Consensus Building & Execution - Leader makes final decision and executes trade"""
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content="## 阶段4: 共识形成与执行\n\n请主持人综合各方意见，形成最终交易决策并执行。",
            message_type="phase"
        )

        # Use Leader for final decision and execution
        leader = self._get_agent_by_id("Leader")
        if not leader:
            logger.error("Leader not found")
            return None

        # Get current account balance for position calculation
        account_info = ""
        try:
            if hasattr(leader, 'tools') and 'get_account_balance' in leader.tools:
                balance_result = await leader.tools['get_account_balance'].execute()
                account_info = f"\n当前账户信息: {balance_result}"
        except Exception as e:
            logger.warning(f"Failed to get account balance: {e}")

        # Request Leader to make decision and DIRECTLY EXECUTE using tools
        prompt = f"""作为圆桌主持人，请综合以上所有讨论内容和专家意见，形成最终交易决策。

## 会议讨论总结
你已经听取了以下专家的分析：
- 技术分析师 (TechnicalAnalyst): K线形态、技术指标分析
- 宏观经济分析师 (MacroEconomist): 宏观经济、货币政策分析
- 情绪分析师 (SentimentAnalyst): 市场情绪、资金流向分析
- 量化策略师 (QuantStrategist): 量化指标、统计分析
- 风险评估师 (RiskAssessor): 风险评估和建议
{account_info}

## 交易参数限制
- 最大杠杆: {self.config.max_leverage}倍 (可选: 1,2,3,...,{self.config.max_leverage})
- 最大仓位: {int(self.config.max_position_percent * 100)}% 资金
- 最低信心度要求: {self.config.min_confidence}%

## 杠杆选择规则 (强制执行)
**你必须严格按照信心度选择对应区间的杠杆倍数！这是强制要求！**
- **高信心度 (>80%)**: **必须**使用 {int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}倍杠杆 (例如85%信心 → 至少{int(self.config.max_leverage * 0.5)}倍)
- **中信心度 (60-80%)**: **必须**使用 {int(self.config.max_leverage * 0.25)}-{int(self.config.max_leverage * 0.5)}倍杠杆
- **低信心度 (<60%)**: 使用 1-{int(self.config.max_leverage * 0.25)}倍杠杆 或选择观望

**示例**: 如果你综合评估信心度为85%，那么杠杆必须在{int(self.config.max_leverage * 0.5)}-{self.config.max_leverage}倍之间，不能选择低于{int(self.config.max_leverage * 0.5)}倍的杠杆！

## 你的任务

1. **综合分析**: 总结各专家的核心观点和分歧
2. **评估信心度**: 根据专家意见一致性和市场信号强度，评估你的综合信心度 (0-100%)
3. **形成决策**: 基于专家意见，决定是做多(long)、做空(short)还是观望(hold)
4. **确定参数**:
   - 杠杆倍数 (根据信心度从上方指南中选择，范围1-{self.config.max_leverage})
   - 仓位百分比 (范围{int(self.config.min_position_percent * 100)}-{int(self.config.max_position_percent * 100)}%，建议{int(self.config.default_position_percent * 100)}%)
   - 止盈止损百分比 (默认止盈{self.config.default_tp_percent}%，止损{self.config.default_sl_percent}%)
5. **直接执行**: 如果决定交易，使用工具直接执行

## 执行方式

如果决定做多，请调用:
[USE_TOOL: open_long(leverage="杠杆倍数", amount_usdt="金额", tp_price="止盈价", sl_price="止损价")]

如果决定做空，请调用:
[USE_TOOL: open_short(leverage="杠杆倍数", amount_usdt="金额", tp_price="止盈价", sl_price="止损价")]

如果决定观望，请说明原因，不需要调用工具。

请先给出你的分析总结，然后做出决策并执行。
"""

        response = await self._run_agent_turn(leader, prompt)

        # Try to extract signal from the response for tracking purposes
        signal = await self._parse_json_signal(response)
        if not signal:
            # If no JSON, try to parse from tool call results
            signal = self._extract_signal_from_response(response)

        return signal

    def _extract_signal_from_response(self, response: str) -> Optional[TradingSignal]:
        """Extract trading signal from Leader's response (tool call or text)"""
        try:
            from app.core.trading.price_service import get_current_btc_price
            import asyncio

            # Default values from config
            direction = "hold"
            leverage = 1
            amount_percent = self.config.default_position_percent
            tp_percent = self.config.default_tp_percent
            sl_percent = self.config.default_sl_percent
            confidence = self.config.min_confidence

            # Parse direction from tool calls or text
            if "open_long" in response.lower() or "做多" in response:
                direction = "long"
            elif "open_short" in response.lower() or "做空" in response:
                direction = "short"

            # Parse leverage from tool call
            import re
            lev_match = re.search(r'leverage["\s=:]+(\d+)', response, re.IGNORECASE)
            if lev_match:
                leverage = min(int(lev_match.group(1)), self.config.max_leverage)

            # Parse amount
            amt_match = re.search(r'amount_usdt["\s=:]+(\d+\.?\d*)', response, re.IGNORECASE)
            if amt_match:
                # Convert USDT to percent using configured default balance
                amount_usdt = float(amt_match.group(1))
                amount_percent = min(amount_usdt / self.config.default_balance, self.config.max_position_percent)

            # Get current price for TP/SL calculation
            try:
                loop = asyncio.get_event_loop()
                current_price = loop.run_until_complete(get_current_btc_price())
            except:
                current_price = self.config.fallback_price  # 使用配置的回退价格

            if direction == "long":
                tp_price = current_price * (1 + tp_percent / 100)
                sl_price = current_price * (1 - sl_percent / 100)
            elif direction == "short":
                tp_price = current_price * (1 - tp_percent / 100)
                sl_price = current_price * (1 + sl_percent / 100)
            else:
                tp_price = current_price
                sl_price = current_price

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
            logger.error(f"Error extracting signal from response: {e}")
            return None

    async def _run_execution_phase(self, signal: TradingSignal):
        """Phase 5: Execution confirmation (trade already executed by Leader in consensus phase)"""
        # Leader already executed the trade in consensus phase via tool calls
        # This phase is just for confirmation/reporting
        self._add_message(
            agent_id="system",
            agent_name="系统",
            content=f"## 交易执行完成\n\n交易方向: {signal.direction}\n杠杆: {signal.leverage}倍\n入场价: ${signal.entry_price:,.2f}",
            message_type="phase"
        )

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

            # ===== Tool Execution (copied from agent._parse_llm_response) =====
            # Check for tool calls in the content using [USE_TOOL: tool_name(params)] format
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content)

            if tool_matches and hasattr(agent, 'tools') and agent.tools:
                logger.info(f"Agent {agent.name} has {len(tool_matches)} tool calls to execute")
                tool_results = []

                for tool_name, params_str in tool_matches:
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

                            # Execute the tool
                            tool_result = await agent.tools[tool_name].execute(**params)
                            logger.info(f"[{agent.name}] Tool {tool_name} executed successfully")

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
                        {"role": "user", "content": f"工具返回结果:\n{tool_results_text}\n\n请基于这些真实数据给出最终分析结论。注意：请使用工具返回的真实数据，不要编造数据。"}
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
            logger.error(f"Error parsing vote: {e}")
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
                amount_percent = min(float(pos_match.group(1)) / 100, self.config.max_position_percent)

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
            amount_percent = min(position_percent / 100, self.config.max_position_percent)

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
