"""
Trade Executor Agent - Intelligent Trading Decision Agent

Responsibilities:
1. Understand Leader's meeting summary
2. Analyze all expert votes
3. Consider current position status
4. Make independent trading decisions
5. Output structured trading instructions

Design Philosophy:
- No dependency on fixed formats or markers
- Fully based on semantic understanding
- Support multiple LLMs and output formats
- Robust and testable
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.models.trading_models import TradingSignal
from app.core.trading.position_context import PositionContext

logger = logging.getLogger(__name__)


class TradeExecutorAgent:
    """
    Trade Execution Decision Agent

    This is a true intelligent agent, not a simple executor.
    It can:
    - Understand the semantics of meeting discussions
    - Synthesize opinions from multiple experts
    - Consider current account and position status
    - Make independent trading decisions
    """

    def __init__(self, agent_instance, toolkit, config):
        """
        Initialize TradeExecutor

        Args:
            agent_instance: LLM Agent instance
            toolkit: Trading toolkit (for getting prices, etc.)
            config: Trading configuration
        """
        self.agent = agent_instance
        self.toolkit = toolkit
        self.config = config
        self.logger = logger
        # Store vote data for dynamic confidence calculation
        self._agents_votes: Dict[str, str] = {}

        # Validate required dependencies
        if not self.toolkit:
            raise RuntimeError("TradeExecutor requires toolkit")
        # FIX: toolkit may have _get_market_price instead of price_service
        # Check if toolkit has price retrieval capability
        if not (hasattr(self.toolkit, 'price_service') or hasattr(self.toolkit, '_get_market_price')):
            raise RuntimeError("Toolkit must have price_service or _get_market_price method")
        if not self.config:
            raise RuntimeError("TradeExecutor requires config")

    def _calculate_confidence_from_votes(self, direction: str = None) -> int:
        """
        Dynamically calculate confidence based on expert votes

        Calculation rules:
        - 5 unanimous votes: 90%
        - 4 unanimous votes: 80%
        - 3 unanimous votes: 65%
        - 2 unanimous votes: 50%
        - 1 or fewer: 30%
        """
        votes = self._agents_votes
        if not votes:
            self.logger.warning("[TradeExecutor] No vote data, using minimum confidence 30%")
            return 30

        # Count votes for each direction
        long_count = sum(1 for v in votes.values() if v == 'long')
        short_count = sum(1 for v in votes.values() if v == 'short')
        hold_count = sum(1 for v in votes.values() if v == 'hold')

        # Determine target direction and vote count
        if direction:
            if direction == 'long':
                target_count = long_count
            elif direction == 'short':
                target_count = short_count
            else:
                target_count = hold_count
        else:
            target_count = max(long_count, short_count, hold_count)

        # Calculate confidence based on vote count
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

        self.logger.info(f"[TradeExecutor][Confidence] Votes: {long_count}long/{short_count}short/{hold_count}hold, "
                        f"target_direction={direction or 'majority'}, votes={target_count}, confidence={confidence}%")
        return confidence

    def _calculate_leverage_from_confidence(self, confidence: int) -> int:
        """Calculate reasonable leverage based on confidence"""
        max_leverage = self._get_config_value('max_leverage', 20)

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

        leverage = min(leverage, max_leverage)
        self.logger.info(f"[TradeExecutor][Leverage] confidence={confidence}% -> leverage={leverage}x")
        return leverage

    def _calculate_amount_from_confidence(self, confidence: int) -> float:
        """Calculate reasonable position size based on confidence"""
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

        self.logger.info(f"[TradeExecutor][Amount] confidence={confidence}% -> position={amount*100:.0f}%")
        return amount

    async def _get_current_price_safe(self) -> float:
        """
        Safely get current price

        Priority:
        1. Extract from LLM's JSON response (if already provided)
        2. TradeExecutor Agent calls tool itself
        3. Direct toolkit method call (fallback)
        """
        try:
            # Method 1: Check if agent has tool calling capability
            # If agent can call tools, let it get the price itself
            if hasattr(self.agent, 'tools') and self.agent.tools:
                self.logger.info("[TradeExecutor] Agent has tool capability, let Agent get price")
                # Agent will call tools during decision process
                # Return placeholder here, actual price will be obtained in decision
                # But for compatibility, we still provide fallback
                pass

            # Method 2: Use toolkit's _get_market_price method (TradingToolkit)
            if hasattr(self.toolkit, '_get_market_price'):
                result = await self.toolkit._get_market_price()
                # _get_market_price returns formatted string, need to parse
                if isinstance(result, str):
                    # Extract price from returned string
                    import re
                    price_match = re.search(r'Current price.*?(\d+(?:,\d+)*(?:\.\d+)?)', result)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        if price > 0:
                            self.logger.info(f"[TradeExecutor] Got price via _get_market_price: ${price:,.2f}")
                            return price
                elif isinstance(result, (int, float)):
                    price = float(result)
                    if price > 0:
                        self.logger.info(f"[TradeExecutor] Got price via _get_market_price: ${price:,.2f}")
                        return price

            # Method 3: Use price_service (if exists)
            if hasattr(self.toolkit, 'price_service') and self.toolkit.price_service:
                price = await self.toolkit.price_service.get_current_price()
                if price and price > 0:
                    self.logger.info(f"[TradeExecutor] Got price via price_service: ${price:,.2f}")
                    return price

            # Method 4: Get from paper_trader directly
            if hasattr(self.toolkit, 'paper_trader') and self.toolkit.paper_trader:
                if hasattr(self.toolkit.paper_trader, 'current_price'):
                    price = self.toolkit.paper_trader.current_price
                    if price and price > 0:
                        self.logger.info(f"[TradeExecutor] Got price via paper_trader: ${price:,.2f}")
                        return price

        except Exception as e:
            self.logger.error(f"[TradeExecutor] Failed to get price: {e}", exc_info=True)

        # Fallback: raise exception, let upper layer handle
        raise RuntimeError("Cannot get current price, all price retrieval methods failed")

    def _get_config_value(self, key: str, default: Any) -> Any:
        """
        Safely get config value

        Args:
            key: Config key
            default: Default value

        Returns:
            Config value or default
        """
        return getattr(self.config, key, default)
    
    async def analyze_and_decide(
        self,
        meeting_summary: str,
        agents_votes: Dict[str, str],
        position_context: PositionContext,
        message_history: Optional[List[Dict]] = None
    ) -> TradingSignal:
        """
        Analyze meeting results and make trading decision

        This is TradeExecutor's core method, completely independent of fixed formats.

        Args:
            meeting_summary: Leader's meeting summary text
            agents_votes: Expert vote dictionary {"TechnicalAnalyst": "long", ...}
            position_context: Current position and account status
            message_history: Complete meeting history (optional)

        Returns:
            TradingSignal: Final trading decision
        """
        try:
            self.logger.info("[TradeExecutor] Starting to analyze meeting results...")

            # Store vote data for subsequent dynamic confidence calculation
            self._agents_votes = agents_votes or {}
            self.logger.info(f"[TradeExecutor] Vote data stored: {self._agents_votes}")

            # 1. Build decision prompt
            prompt = self._build_decision_prompt(
                meeting_summary=meeting_summary,
                agents_votes=agents_votes,
                position_context=position_context
            )

            self.logger.info("[TradeExecutor] Prompt built, calling LLM for decision...")

            # 2. Call LLM for decision
            try:
                response = await self.agent.run(prompt)
                self.logger.info(f"[TradeExecutor] LLM response success: {response[:200]}...")
            except Exception as e:
                self.logger.error(f"[TradeExecutor] LLM call failed: {e}")
                # When LLM fails, make simple decision based on votes
                return await self._fallback_decision(agents_votes, position_context)

            # 3. Parse decision (support multiple formats)
            signal = await self._parse_decision(response, position_context)

            # 4. Validate decision reasonableness
            validated_signal = await self._validate_decision(signal, position_context)

            self.logger.info(
                f"[TradeExecutor] Decision complete: {validated_signal.direction.upper()} "
                f"| leverage {validated_signal.leverage}x "
                f"| position {validated_signal.amount_percent*100:.0f}% "
                f"| confidence {validated_signal.confidence}%"
            )

            return validated_signal

        except Exception as e:
            self.logger.error(f"[TradeExecutor] Decision process failed: {e}", exc_info=True)
            # Return hold on error
            return await self._create_safe_hold_signal(
                position_context,
                f"TradeExecutor decision failed: {str(e)}"
            )
    
    def _build_decision_prompt(
        self,
        meeting_summary: str,
        agents_votes: Dict[str, str],
        position_context: PositionContext
    ) -> str:
        """
        Build TradeExecutor's decision prompt

        This prompt is designed to:
        - Clearly express TradeExecutor's responsibilities
        - Provide all necessary context information
        - Not enforce output format
        - Encourage independent thinking
        """

        # Format position status
        position_status = self._format_position_status(position_context)

        # Format vote summary
        vote_summary = self._format_vote_summary(agents_votes)

        # Calculate consensus level
        consensus_level = self._calculate_consensus_level(agents_votes)

        # Safely get config value
        max_leverage = self._get_config_value('max_leverage', 20)

        prompt = f"""# Trading Execution Decision Task

You are the **Trade Executor**, responsible for making final trading decisions based on the expert roundtable discussion results.

## 1. Current Account and Position Status

{position_status}

## 2. Expert Vote Summary

{vote_summary}

**Consensus Level**: {consensus_level}

## 3. Leader's Meeting Summary

{meeting_summary}

---

## Your Task

Based on all the above information, make the final trading decision.

### Decision Considerations

1. **Expert Consensus**:
   - High consensus (4-5 unanimous votes): Higher confidence, leverage and position size increase accordingly
   - Moderate consensus (3 votes): Medium confidence, moderate leverage and position size
   - Divergent opinions (scattered votes): Lower confidence, recommend holding or minimum position

   ⚠️ Note: confidence/leverage/amount_percent all have strict calculation rules (see below), don't guess randomly

2. **Current Position Status**:
   - **No position**: Evaluate whether to open new position
   - **Long position and experts bullish**: Consider adding or holding
   - **Long position but experts bearish**: Consider closing or reversing
   - **Short position and experts bearish**: Consider adding or holding
   - **Short position but experts bullish**: Consider closing or reversing

3. **Risk Management**:
   - When uncertain, prefer to hold
   - Leverage should strictly correspond to confidence (see calculation rules below)
   - Stop loss/take profit auto-adjust based on leverage: high leverage = tight stop, low leverage = wide stop
   - Position cannot exceed available funds

4. **Leader's Recommendation**:
   - Leader's summary is important reference, but you have full autonomy
   - If you think Leader is too conservative/aggressive, you can adjust

---

## Output Format

Please output your decision in the following JSON format (must be valid JSON):

```json
{{
  "decision": "open_long",
  "reasoning": "Give reasons based on specific voting situation and expert analysis...",
  "confidence": <Based on voting consensus: 5 unanimous=90, 4 votes=80, 3 votes=65, 2 votes=50, 1 vote=30>,
  "leverage": <Based on confidence: >=85 use 10x, >=75 use 8x, >=65 use 6x, >=55 use 5x, others use 3x>,
  "amount_percent": <Based on confidence: >=85 use 0.6, >=75 use 0.5, >=65 use 0.4, >=55 use 0.3, others use 0.2>,
  "take_profit_price": <Set reasonably based on current price>,
  "stop_loss_price": <Set reasonably based on current price>
}}
```

**decision field options**:
- `open_long`: Open long position
- `open_short`: Open short position
- `close_position`: Close position
- `add_to_position`: Add to position (current direction)
- `hold`: Hold/wait

**Important - confidence/leverage/amount must be calculated based on votes**:
1. **confidence**: Calculate based on voting consensus, don't use fixed values
   - 5 unanimous votes → 90%
   - 4 unanimous votes → 80%
   - 3 unanimous votes → 65%
   - 2 unanimous votes → 50%
   - Others → 30%
2. **leverage**: Must correspond to confidence, don't set arbitrarily
   - confidence >= 85 → 10x
   - confidence >= 75 → 8x
   - confidence >= 65 → 6x
   - confidence >= 55 → 5x
   - confidence >= 45 → 3x
   - Others → 2x
3. **amount_percent**: Must correspond to confidence
   - confidence >= 85 → 0.6
   - confidence >= 75 → 0.5
   - confidence >= 65 → 0.4
   - confidence >= 55 → 0.3
   - Others → 0.2
4. reasoning must cite specific expert opinions and data
5. Prices must be reasonable (TP > current price > SL for long; SL > current price > TP for short)

Now, please make your final decision. Output JSON only, no other explanation needed.
"""
        
        return prompt
    
    def _format_position_status(self, position_context: PositionContext) -> str:
        """Format position status into readable text"""

        if not position_context.has_position:
            return f"""- **Position Status**: No position
- **Available Balance**: ${position_context.available_balance:,.2f}
- **Total Equity**: ${position_context.total_equity:,.2f}
"""

        # Safely get direction, prevent None
        direction = position_context.direction or "unknown"

        pnl_sign = "+" if position_context.unrealized_pnl >= 0 else ""
        pnl_color = "📈" if position_context.unrealized_pnl >= 0 else "📉"

        return f"""- **Position Status**: {direction.upper()} position
- **Direction**: {direction}
- **Entry Price**: ${position_context.entry_price:,.2f}
- **Current Price**: ${position_context.current_price:,.2f}
- **Position Size**: {position_context.size:.4f}
- **Leverage**: {position_context.leverage}x
- **Unrealized PnL**: {pnl_color} {pnl_sign}${position_context.unrealized_pnl:,.2f} ({pnl_sign}{position_context.unrealized_pnl_percent:.2f}%)
- **Take Profit Price**: ${position_context.take_profit_price:,.2f}
- **Stop Loss Price**: ${position_context.stop_loss_price:,.2f}
- **Available Balance**: ${position_context.available_balance:,.2f}
- **Total Equity**: ${position_context.total_equity:,.2f}
"""
    
    def _format_vote_summary(self, agents_votes: Dict[str, str]) -> str:
        """Format vote summary"""

        # Count votes
        long_count = sum(1 for v in agents_votes.values() if v == 'long')
        short_count = sum(1 for v in agents_votes.values() if v == 'short')
        hold_count = sum(1 for v in agents_votes.values() if v == 'hold')

        # Build detail list
        vote_details = []
        for agent, vote in agents_votes.items():
            emoji = "🟢" if vote == "long" else "🔴" if vote == "short" else "⚪"
            vote_text = "long" if vote == "long" else "short" if vote == "short" else "hold"
            vote_details.append(f"  {emoji} **{agent}**: {vote_text}")

        vote_list = "\n".join(vote_details)

        return f"""**Vote Distribution**: {long_count} long / {short_count} short / {hold_count} hold

{vote_list}
"""
    
    def _calculate_consensus_level(self, agents_votes: Dict[str, str]) -> str:
        """Calculate consensus level"""

        if not agents_votes:
            return "No votes"

        vote_counts = {}
        for vote in agents_votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

        max_count = max(vote_counts.values())
        total_count = len(agents_votes)

        if max_count >= 4:
            return "🟢 High consensus (>= 4 votes)"
        elif max_count == 3:
            return "🟡 Moderate consensus (3 votes)"
        elif max_count == 2:
            return "🟠 Weak consensus (2 votes)"
        else:
            return "🔴 Complete divergence"
    
    async def _parse_decision(
        self,
        response: str,
        position_context: PositionContext
    ) -> TradingSignal:
        """
        Parse TradeExecutor's decision

        Supports multiple formats (priority from high to low):
        1. JSON format (highest priority)
        2. Natural language extraction (fallback)
        """

        self.logger.info("[TradeExecutor] Parsing decision response...")

        # Method 1: Extract JSON (priority)
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if not json_match:
            # Try to find raw JSON
            json_match = re.search(r'\{[^}]*"decision"[^}]*\}', response, re.DOTALL)

        if json_match:
            try:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
                data = json.loads(json_str)
                self.logger.info("[TradeExecutor] Successfully parsed JSON format")
                return await self._build_signal_from_dict(data, position_context)
            except json.JSONDecodeError as e:
                self.logger.warning(f"[TradeExecutor] JSON parse failed: {e}")

        # Method 2: Natural language extraction (fallback)
        self.logger.info("[TradeExecutor] Using natural language extraction...")
        return await self._extract_from_natural_language(response, position_context)
    
    async def _build_signal_from_dict(
        self,
        data: Dict[str, Any],
        position_context: PositionContext
    ) -> TradingSignal:
        """Build TradingSignal from dictionary"""

        decision = data.get("decision", "hold")

        # Map decision to direction
        direction_map = {
            "open_long": "long",
            "open_short": "short",
            "close_position": "close",
            "add_to_position": position_context.direction if position_context.has_position else "hold",
            "hold": "hold"
        }

        direction = direction_map.get(decision, "hold")

        # Safely get current price
        current_price = await self._get_current_price_safe()

        # Extract fields - if not provided, dynamically calculate based on votes
        raw_confidence = data.get("confidence")
        raw_leverage = data.get("leverage")
        raw_amount = data.get("amount_percent")

        # confidence: if LLM didn't provide, calculate based on votes
        if raw_confidence is not None:
            confidence = int(raw_confidence)
            self.logger.info(f"[TradeExecutor] confidence from LLM response: {confidence}%")
        else:
            confidence = self._calculate_confidence_from_votes(direction)
            self.logger.info(f"[TradeExecutor] confidence from vote calculation: {confidence}%")

        # leverage: if LLM didn't provide, calculate based on confidence
        if raw_leverage is not None:
            leverage = int(raw_leverage)
            self.logger.info(f"[TradeExecutor] leverage from LLM response: {leverage}x")
        else:
            leverage = self._calculate_leverage_from_confidence(confidence)
            self.logger.info(f"[TradeExecutor] leverage from confidence calculation: {leverage}x")

        # amount_percent: if LLM didn't provide, calculate based on confidence
        if raw_amount is not None:
            amount_percent = float(raw_amount)
            self.logger.info(f"[TradeExecutor] amount_percent from LLM response: {amount_percent*100:.0f}%")
        else:
            amount_percent = self._calculate_amount_from_confidence(confidence)
            self.logger.info(f"[TradeExecutor] amount_percent from confidence calculation: {amount_percent*100:.0f}%")

        reasoning = data.get("reasoning", "TradeExecutor decision")

        # Get take profit and stop loss
        take_profit = float(data.get("take_profit_price", 0))
        stop_loss = float(data.get("stop_loss_price", 0))

        # Safely get config values
        tp_percent = self._get_config_value('default_take_profit_percent', 0.08)
        sl_percent = self._get_config_value('default_stop_loss_percent', 0.03)
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')

        # If TP/SL not provided, use defaults
        if take_profit == 0:
            if direction == "long":
                take_profit = current_price * (1 + tp_percent)
            elif direction == "short":
                take_profit = current_price * (1 - tp_percent)
            else:
                take_profit = current_price
        
        if stop_loss == 0:
            if direction == "long":
                stop_loss = current_price * (1 - sl_percent)
            elif direction == "short":
                stop_loss = current_price * (1 + sl_percent)
            else:
                stop_loss = current_price
        
        return TradingSignal(
            direction=direction,
            symbol=symbol,
            leverage=leverage,
            amount_percent=amount_percent,
            entry_price=current_price,
            take_profit_price=take_profit,
            stop_loss_price=stop_loss,
            confidence=confidence,
            reasoning=reasoning,
            agents_consensus={},
            timestamp=datetime.now()
        )
    
    async def _extract_from_natural_language(
        self,
        response: str,
        position_context: PositionContext
    ) -> TradingSignal:
        """
        Extract decision from natural language (last resort)

        Example:
        "I decide to go long BTC, 5x leverage, 50% position, TP 98000, SL 92000"
        """

        self.logger.info("[TradeExecutor] Extracting decision from natural language...")

        # Extract direction
        direction = "hold"
        if re.search(r'(long|buy|open.*long)', response, re.I):
            direction = "long"
        elif re.search(r'(short|sell|open.*short)', response, re.I):
            direction = "short"
        elif re.search(r'(close|exit)', response, re.I):
            direction = "hold"  # FIX: TradingSignal doesn't support "close", use hold after closing
        elif re.search(r'(hold|wait|no action)', response, re.I):
            direction = "hold"

        self.logger.info(f"[TradeExecutor] Extracted direction: {direction}")

        # Safely get config values
        max_leverage = self._get_config_value('max_leverage', 20)
        tp_percent = self._get_config_value('default_take_profit_percent', 0.08)
        sl_percent = self._get_config_value('default_stop_loss_percent', 0.03)
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')

        # Extract confidence - if not in text, calculate based on votes
        confidence_match = re.search(r'confidence[：:]?\s*(\d+)', response, re.I)
        if confidence_match:
            confidence = int(confidence_match.group(1))
            confidence = min(max(confidence, 0), 100)
            self.logger.info(f"[TradeExecutor] confidence from text extraction: {confidence}%")
        else:
            confidence = self._calculate_confidence_from_votes(direction)
            self.logger.info(f"[TradeExecutor] confidence from vote calculation: {confidence}%")

        # Extract leverage - if not in text, calculate based on confidence
        leverage_match = re.search(r'(\d+)\s*[xX×]', response)
        if leverage_match:
            leverage = int(leverage_match.group(1))
            leverage = min(max(leverage, 1), max_leverage)
            self.logger.info(f"[TradeExecutor] leverage from text extraction: {leverage}x")
        else:
            leverage = self._calculate_leverage_from_confidence(confidence)
            self.logger.info(f"[TradeExecutor] leverage from confidence calculation: {leverage}x")

        # Extract position - if not in text, calculate based on confidence
        position_match = re.search(r'position[：:]?\s*(\d+)%', response, re.I)
        if not position_match:
            position_match = re.search(r'(\d+)%.*position', response, re.I)
        if position_match:
            amount_percent = float(position_match.group(1)) / 100
            amount_percent = min(max(amount_percent, 0.0), 1.0)
            self.logger.info(f"[TradeExecutor] amount_percent from text extraction: {amount_percent*100:.0f}%")
        else:
            amount_percent = self._calculate_amount_from_confidence(confidence)
            self.logger.info(f"[TradeExecutor] amount_percent from confidence calculation: {amount_percent*100:.0f}%")

        # Extract prices
        tp_match = re.search(r'(take.?profit|tp)[：:]?\s*(\d+)', response, re.I)
        sl_match = re.search(r'(stop.?loss|sl)[：:]?\s*(\d+)', response, re.I)

        # Safely get current price
        current_price = await self._get_current_price_safe()

        # Calculate TP/SL
        if tp_match:
            take_profit = float(tp_match.group(2))
        else:
            if direction == "long":
                take_profit = current_price * (1 + tp_percent)
            elif direction == "short":
                take_profit = current_price * (1 - tp_percent)
            else:
                take_profit = current_price

        if sl_match:
            stop_loss = float(sl_match.group(2))
        else:
            if direction == "long":
                stop_loss = current_price * (1 - sl_percent)
            elif direction == "short":
                stop_loss = current_price * (1 + sl_percent)
            else:
                stop_loss = current_price

        self.logger.info(
            f"[TradeExecutor] Extraction result: {direction} | "
            f"leverage {leverage}x | position {amount_percent*100:.0f}% | "
            f"confidence {confidence}%"
        )

        return TradingSignal(
            direction=direction,
            symbol=symbol,
            leverage=leverage,
            amount_percent=amount_percent,
            entry_price=current_price,
            take_profit_price=take_profit,
            stop_loss_price=stop_loss,
            confidence=confidence,
            reasoning=response[:500],  # Take first 500 chars as reasoning
            agents_consensus={},
            timestamp=datetime.now()
        )
    
    async def _validate_decision(
        self,
        signal: TradingSignal,
        position_context: PositionContext
    ) -> TradingSignal:
        """
        Validate decision reasonableness and make necessary adjustments

        Validation items:
        1. Leverage within allowed range
        2. Position doesn't exceed available funds
        3. TP/SL prices are reasonable
        4. Confidence corresponds to leverage
        """

        self.logger.info("[TradeExecutor] Validating decision reasonableness...")

        # Safely get config values
        max_leverage = self._get_config_value('max_leverage', 20)
        tp_percent = self._get_config_value('default_take_profit_percent', 0.08)
        sl_percent = self._get_config_value('default_stop_loss_percent', 0.03)

        # 1. Limit leverage
        if signal.leverage > max_leverage:
            self.logger.warning(
                f"[TradeExecutor] Leverage {signal.leverage}x exceeds max {max_leverage}x, adjusted"
            )
            signal.leverage = max_leverage

        if signal.leverage < 1:
            signal.leverage = 1

        # 2. Limit position
        if signal.amount_percent > 1.0:
            self.logger.warning(
                f"[TradeExecutor] Position {signal.amount_percent*100:.0f}% exceeds 100%, adjusted"
            )
            signal.amount_percent = 1.0

        if signal.amount_percent < 0:
            signal.amount_percent = 0

        # 3. Validate TP/SL
        current_price = signal.entry_price

        if signal.direction == "long":
            if signal.take_profit_price <= current_price:
                self.logger.warning("[TradeExecutor] Long TP price invalid, using default")
                signal.take_profit_price = current_price * (1 + tp_percent)

            if signal.stop_loss_price >= current_price:
                self.logger.warning("[TradeExecutor] Long SL price invalid, using default")
                signal.stop_loss_price = current_price * (1 - sl_percent)

        elif signal.direction == "short":
            if signal.take_profit_price >= current_price:
                self.logger.warning("[TradeExecutor] Short TP price invalid, using default")
                signal.take_profit_price = current_price * (1 - tp_percent)

            if signal.stop_loss_price <= current_price:
                self.logger.warning("[TradeExecutor] Short SL price invalid, using default")
                signal.stop_loss_price = current_price * (1 + sl_percent)

        # 4. Limit confidence
        if signal.confidence > 100:
            signal.confidence = 100
        if signal.confidence < 0:
            signal.confidence = 0

        self.logger.info("[TradeExecutor] Decision validation complete")

        return signal
    
    async def _fallback_decision(
        self,
        agents_votes: Dict[str, str],
        position_context: PositionContext
    ) -> TradingSignal:
        """
        Fallback decision logic when LLM call fails

        Make simple majority decision based on expert votes
        """

        self.logger.info("[TradeExecutor] Using fallback decision logic (based on votes)...")

        # Count votes
        long_count = sum(1 for v in agents_votes.values() if v == 'long')
        short_count = sum(1 for v in agents_votes.values() if v == 'short')
        hold_count = sum(1 for v in agents_votes.values() if v == 'hold')

        total_votes = len(agents_votes)

        # Majority decision
        if long_count >= total_votes * 0.6:  # 60%+ bullish
            direction = "long"
            confidence = int(long_count / total_votes * 100)
        elif short_count >= total_votes * 0.6:  # 60%+ bearish
            direction = "short"
            confidence = int(short_count / total_votes * 100)
        else:
            direction = "hold"
            confidence = 0

        # Use unified calculation functions
        leverage = self._calculate_leverage_from_confidence(confidence)
        amount_percent = self._calculate_amount_from_confidence(confidence)

        # Safely get current price and config values
        current_price = await self._get_current_price_safe()
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')

        self.logger.info(f"[TradeExecutor] Fallback decision: {direction} | confidence={confidence}% | leverage={leverage}x | amount={amount_percent*100:.0f}%")

        # Dynamically calculate TP/SL based on leverage (consistent with other places)
        if leverage >= 15:
            tp_pct, sl_pct = 0.05, 0.02  # High leverage: 5% TP, 2% SL
        elif leverage >= 10:
            tp_pct, sl_pct = 0.06, 0.025
        elif leverage >= 5:
            tp_pct, sl_pct = 0.08, 0.03
        else:
            tp_pct, sl_pct = 0.10, 0.05  # Low leverage: 10% TP, 5% SL

        if direction == "long":
            take_profit = current_price * (1 + tp_pct)
            stop_loss = current_price * (1 - sl_pct)
        elif direction == "short":
            take_profit = current_price * (1 - tp_pct)
            stop_loss = current_price * (1 + sl_pct)
        else:
            take_profit = current_price
            stop_loss = current_price

        return TradingSignal(
            direction=direction,
            symbol=symbol,
            leverage=leverage,
            amount_percent=amount_percent,
            entry_price=current_price,
            take_profit_price=take_profit,
            stop_loss_price=stop_loss,
            confidence=confidence,
            reasoning=f"LLM call failed, fallback decision based on votes: {long_count} long/{short_count} short/{hold_count} hold",
            agents_consensus=agents_votes,
            timestamp=datetime.now()
        )
    
    async def _create_safe_hold_signal(
        self,
        position_context: PositionContext,
        reason: str
    ) -> TradingSignal:
        """Create a safe hold signal"""

        # Safely get current price and config values
        current_price = await self._get_current_price_safe()
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')
        
        return TradingSignal(
            direction="hold",
            symbol=symbol,
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
