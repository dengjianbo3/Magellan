"""
Reflection Engine

Implements the Reflexion pattern for learning from trade outcomes.
Generates insights and updates agent weights based on trade results.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class TradeReflection:
    """A single trade reflection record."""
    trade_id: str
    timestamp: datetime
    
    # Trade details
    direction: str
    entry_price: float
    exit_price: float
    leverage: int
    
    # Outcome
    pnl: float
    pnl_percent: float
    close_reason: str  # "tp", "sl", "manual", "liquidation", "signal"
    is_win: bool
    
    # Reflection
    reflection_text: str
    lessons: Dict[str, str]  # agent_id -> lesson learned
    
    # Agent predictions
    agent_votes: List[Dict]
    correct_predictions: List[str]  # agent IDs that predicted correctly
    incorrect_predictions: List[str]  # agent IDs that predicted wrong
    
    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "leverage": self.leverage,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "close_reason": self.close_reason,
            "is_win": self.is_win,
            "reflection_text": self.reflection_text,
            "lessons": self.lessons,
            "agent_votes": self.agent_votes,
            "correct_predictions": self.correct_predictions,
            "incorrect_predictions": self.incorrect_predictions
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TradeReflection":
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            trade_id=data["trade_id"],
            timestamp=timestamp or datetime.now(),
            direction=data["direction"],
            entry_price=data["entry_price"],
            exit_price=data["exit_price"],
            leverage=data["leverage"],
            pnl=data["pnl"],
            pnl_percent=data["pnl_percent"],
            close_reason=data["close_reason"],
            is_win=data["is_win"],
            reflection_text=data.get("reflection_text", ""),
            lessons=data.get("lessons", {}),
            agent_votes=data.get("agent_votes", []),
            correct_predictions=data.get("correct_predictions", []),
            incorrect_predictions=data.get("incorrect_predictions", [])
        )


class ReflectionMemory:
    """
    Persistent storage for reflections.
    
    Stores reflections in Redis for:
    - Historical analysis
    - Context injection into future trading decisions
    - Agent weight adjustments
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self.key_prefix = "trading:reflection"
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url)
        return self._redis
    
    async def store_reflection(self, reflection: TradeReflection) -> None:
        """Store a reflection record."""
        r = await self._get_redis()
        
        # Store individual reflection
        key = f"{self.key_prefix}:{reflection.trade_id}"
        await r.set(key, json.dumps(reflection.to_dict()))
        
        # Add to recent reflections list (keep last 100)
        list_key = f"{self.key_prefix}:recent"
        await r.lpush(list_key, reflection.trade_id)
        await r.ltrim(list_key, 0, 99)
        
        # Update agent-specific learnings
        for agent_id, lesson in reflection.lessons.items():
            agent_key = f"{self.key_prefix}:agent:{agent_id}:lessons"
            await r.lpush(agent_key, json.dumps({
                "trade_id": reflection.trade_id,
                "timestamp": reflection.timestamp.isoformat(),
                "is_win": reflection.is_win,
                "lesson": lesson
            }))
            await r.ltrim(agent_key, 0, 19)  # Keep last 20 lessons per agent
    
    async def get_reflection(self, trade_id: str) -> Optional[TradeReflection]:
        """Get a specific reflection by trade ID."""
        r = await self._get_redis()
        key = f"{self.key_prefix}:{trade_id}"
        data = await r.get(key)
        if data:
            return TradeReflection.from_dict(json.loads(data))
        return None
    
    async def get_recent_reflections(self, limit: int = 10) -> List[TradeReflection]:
        """Get recent reflections."""
        r = await self._get_redis()
        list_key = f"{self.key_prefix}:recent"
        trade_ids = await r.lrange(list_key, 0, limit - 1)
        
        reflections = []
        for tid_bytes in trade_ids:
            tid = tid_bytes.decode() if isinstance(tid_bytes, bytes) else tid_bytes
            reflection = await self.get_reflection(tid)
            if reflection:
                reflections.append(reflection)
        
        return reflections
    
    async def get_agent_lessons(self, agent_id: str, limit: int = 5) -> List[dict]:
        """Get recent lessons for a specific agent."""
        r = await self._get_redis()
        key = f"{self.key_prefix}:agent:{agent_id}:lessons"
        lessons_raw = await r.lrange(key, 0, limit - 1)
        
        lessons = []
        for l in lessons_raw:
            data = l.decode() if isinstance(l, bytes) else l
            lessons.append(json.loads(data))
        
        return lessons
    
    async def get_win_loss_stats(self) -> Dict[str, Any]:
        """Get win/loss statistics from recent reflections."""
        reflections = await self.get_recent_reflections(limit=50)
        
        if not reflections:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0}
        
        wins = sum(1 for r in reflections if r.is_win)
        losses = len(reflections) - wins
        
        return {
            "total": len(reflections),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(reflections)) * 100 if reflections else 0,
            "total_pnl": sum(r.pnl for r in reflections),
            "avg_pnl": sum(r.pnl for r in reflections) / len(reflections) if reflections else 0
        }


class AgentWeightAdjuster:
    """
    Adjusts agent weights based on prediction accuracy.
    
    Agents that consistently predict correctly get higher weights.
    Agents that consistently predict wrong get lower weights.
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self.key_prefix = "trading:weights"
        
        # Weight adjustment parameters
        self.correct_bonus = 0.05  # +5% for correct prediction
        self.incorrect_penalty = 0.03  # -3% for incorrect prediction
        self.min_weight = 0.5  # Minimum weight multiplier
        self.max_weight = 2.0  # Maximum weight multiplier
        self.default_weight = 1.0
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url)
        return self._redis
    
    async def get_weight(self, agent_id: str) -> float:
        """Get current weight for an agent."""
        r = await self._get_redis()
        key = f"{self.key_prefix}:{agent_id}"
        weight = await r.get(key)
        if weight:
            return float(weight.decode() if isinstance(weight, bytes) else weight)
        return self.default_weight
    
    async def set_weight(self, agent_id: str, weight: float) -> None:
        """Set weight for an agent."""
        r = await self._get_redis()
        key = f"{self.key_prefix}:{agent_id}"
        clamped_weight = max(self.min_weight, min(self.max_weight, weight))
        await r.set(key, str(clamped_weight))
    
    async def get_all_weights(self) -> Dict[str, float]:
        """Get weights for all agents."""
        r = await self._get_redis()
        pattern = f"{self.key_prefix}:*"
        keys = await r.keys(pattern)
        
        weights = {}
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            agent_id = key_str.replace(f"{self.key_prefix}:", "")
            weights[agent_id] = await self.get_weight(agent_id)
        
        return weights
    
    async def adjust_weights(
        self,
        correct_agents: List[str],
        incorrect_agents: List[str]
    ) -> Dict[str, float]:
        """
        Adjust weights based on prediction accuracy.
        
        Args:
            correct_agents: Agent IDs that predicted correctly
            incorrect_agents: Agent IDs that predicted incorrectly
            
        Returns:
            New weights for all adjusted agents
        """
        new_weights = {}
        
        for agent_id in correct_agents:
            current = await self.get_weight(agent_id)
            new_weight = current + self.correct_bonus
            await self.set_weight(agent_id, new_weight)
            new_weights[agent_id] = min(self.max_weight, new_weight)
            logger.info(f"[WEIGHT] {agent_id}: {current:.2f} -> {new_weights[agent_id]:.2f} (+correct)")
        
        for agent_id in incorrect_agents:
            current = await self.get_weight(agent_id)
            new_weight = current - self.incorrect_penalty
            await self.set_weight(agent_id, new_weight)
            new_weights[agent_id] = max(self.min_weight, new_weight)
            logger.info(f"[WEIGHT] {agent_id}: {current:.2f} -> {new_weights[agent_id]:.2f} (-incorrect)")
        
        return new_weights


class ReflectionEngine:
    """
    Main Reflection Engine.
    
    Implements the Reflexion pattern:
    1. Analyze trade outcome
    2. Compare with agent predictions
    3. Generate lessons learned
    4. Store for future reference
    5. Adjust agent weights
    
    Usage:
        engine = ReflectionEngine(llm_service)
        await engine.reflect_on_trade(trade_result, agent_votes)
    """
    
    def __init__(
        self,
        llm_service: Any = None,
        redis_url: str = "redis://redis:6379"
    ):
        self.llm = llm_service
        self.memory = ReflectionMemory(redis_url)
        self.weight_adjuster = AgentWeightAdjuster(redis_url)
    
    async def reflect_on_trade(
        self,
        trade_id: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        leverage: int,
        pnl: float,
        pnl_percent: float,
        close_reason: str,
        agent_votes: List[Dict],
        market_context: Dict = None
    ) -> TradeReflection:
        """
        Generate reflection for a completed trade.
        
        Args:
            trade_id: Unique trade identifier
            direction: Trade direction ("long" or "short")
            entry_price: Entry price
            exit_price: Exit price
            leverage: Leverage used
            pnl: Profit/loss in USDT
            pnl_percent: Profit/loss percentage
            close_reason: Why the trade was closed
            agent_votes: List of agent votes at entry
            market_context: Optional market context at entry
            
        Returns:
            TradeReflection with insights and lessons
        """
        is_win = pnl > 0
        
        # Analyze predictions
        correct_agents = []
        incorrect_agents = []
        
        for vote in agent_votes:
            agent_id = vote.get("agent_id") or vote.get("agent_name", "unknown")
            vote_direction = vote.get("direction", "").lower()
            
            # Normalize direction
            if hasattr(vote_direction, 'value'):
                vote_direction = vote_direction.value
            
            # Check if prediction was correct
            if vote_direction in ("hold", "close"):
                # Neutral votes - no adjustment
                continue
            
            predicted_correctly = (
                (vote_direction == direction and is_win) or
                (vote_direction != direction and not is_win and vote_direction in ("long", "short"))
            )
            
            if predicted_correctly:
                correct_agents.append(agent_id)
            elif vote_direction in ("long", "short"):
                incorrect_agents.append(agent_id)
        
        # Generate reflection text via LLM
        reflection_text = await self._generate_reflection_text(
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            pnl_percent=pnl_percent,
            close_reason=close_reason,
            agent_votes=agent_votes,
            correct_agents=correct_agents,
            incorrect_agents=incorrect_agents,
            market_context=market_context
        )
        
        # Extract lessons for each agent
        lessons = await self._extract_lessons(
            agent_votes=agent_votes,
            is_win=is_win,
            close_reason=close_reason,
            reflection_text=reflection_text
        )
        
        # Create reflection record
        reflection = TradeReflection(
            trade_id=trade_id,
            timestamp=datetime.now(),
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            leverage=leverage,
            pnl=pnl,
            pnl_percent=pnl_percent,
            close_reason=close_reason,
            is_win=is_win,
            reflection_text=reflection_text,
            lessons=lessons,
            agent_votes=agent_votes,
            correct_predictions=correct_agents,
            incorrect_predictions=incorrect_agents
        )
        
        # Store reflection
        await self.memory.store_reflection(reflection)
        
        # Adjust weights
        await self.weight_adjuster.adjust_weights(correct_agents, incorrect_agents)
        
        logger.info(
            f"[REFLECTION] Trade {trade_id}: {'WIN' if is_win else 'LOSS'} "
            f"PnL: ${pnl:.2f} ({pnl_percent:.1f}%) "
            f"Correct: {correct_agents}, Incorrect: {incorrect_agents}"
        )
        
        return reflection
    
    async def _generate_reflection_text(
        self,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_percent: float,
        close_reason: str,
        agent_votes: List[Dict],
        correct_agents: List[str],
        incorrect_agents: List[str],
        market_context: Dict = None
    ) -> str:
        """Generate reflection text using LLM."""
        if not self.llm:
            # Fallback without LLM
            outcome = "profitable" if pnl > 0 else "unprofitable"
            return (
                f"Trade was {outcome}. "
                f"Closed via {close_reason} with {pnl_percent:.1f}% return. "
                f"Correct predictions: {', '.join(correct_agents) or 'none'}. "
                f"Incorrect predictions: {', '.join(incorrect_agents) or 'none'}."
            )
        
        # Format votes for prompt
        votes_text = []
        for vote in agent_votes:
            agent = vote.get("agent_name", vote.get("agent_id", "Unknown"))
            dir_val = vote.get("direction", "unknown")
            if hasattr(dir_val, 'value'):
                dir_val = dir_val.value
            conf = vote.get("confidence", 0)
            reason = vote.get("reasoning", "")[:100]
            votes_text.append(f"- {agent}: {dir_val} ({conf}%) - {reason}")
        
        prompt = f"""Analyze this completed trade and provide a brief reflection:

## Trade Details
- Direction: {direction.upper()}
- Entry: ${entry_price:,.2f} → Exit: ${exit_price:,.2f}
- Result: {"WIN" if pnl > 0 else "LOSS"} ${pnl:,.2f} ({pnl_percent:+.1f}%)
- Close Reason: {close_reason}

## Agent Predictions
{chr(10).join(votes_text)}

## Accuracy
- Correct Predictions: {', '.join(correct_agents) or 'None'}
- Incorrect Predictions: {', '.join(incorrect_agents) or 'None'}

Provide a 2-3 sentence reflection on:
1. What factors led to this outcome
2. What could be improved for similar situations
"""
        
        try:
            response = await self.llm.generate(prompt, max_tokens=200)
            return response.strip()
        except Exception as e:
            logger.warning(f"LLM reflection failed: {e}")
            outcome = "profitable" if pnl > 0 else "unprofitable"
            return f"Trade was {outcome}. Closed via {close_reason}."
    
    async def _extract_lessons(
        self,
        agent_votes: List[Dict],
        is_win: bool,
        close_reason: str,
        reflection_text: str
    ) -> Dict[str, str]:
        """Extract specific lessons for each agent."""
        lessons = {}
        
        for vote in agent_votes:
            agent_id = vote.get("agent_id") or vote.get("agent_name", "unknown")
            direction = vote.get("direction", "unknown")
            if hasattr(direction, 'value'):
                direction = direction.value
            confidence = vote.get("confidence", 0)
            
            # Generate simple lesson based on outcome
            if direction in ("long", "short"):
                if is_win:
                    if confidence >= 70:
                        lessons[agent_id] = f"High confidence {direction} prediction validated."
                    else:
                        lessons[agent_id] = f"Low confidence but correct. Consider increasing confidence in similar setups."
                else:
                    if confidence >= 70:
                        lessons[agent_id] = f"High confidence {direction} prediction failed. Review analysis criteria."
                    else:
                        lessons[agent_id] = f"Low confidence and incorrect. Analysis approach may need adjustment."
            else:
                lessons[agent_id] = f"Neutral ({direction}) position during {close_reason} outcome."
        
        return lessons
    
    async def get_context_for_analysis(self, limit: int = 3) -> str:
        """
        Get recent reflections formatted for injection into analysis prompts.
        
        Args:
            limit: Number of recent reflections to include
            
        Returns:
            Formatted string for prompt injection
        """
        reflections = await self.memory.get_recent_reflections(limit=limit)
        
        if not reflections:
            return ""
        
        lines = ["## Recent Trade Reflections (Learn from these):"]
        
        for r in reflections:
            outcome = "✅ WIN" if r.is_win else "❌ LOSS"
            lines.append(
                f"\n### Trade {r.trade_id[:8]}: {r.direction.upper()} {outcome}"
            )
            lines.append(f"- PnL: ${r.pnl:,.2f} ({r.pnl_percent:+.1f}%)")
            lines.append(f"- Close: {r.close_reason}")
            lines.append(f"- Insight: {r.reflection_text[:150]}")
        
        return "\n".join(lines)
