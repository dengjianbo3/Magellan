"""
Agent Memory System

Stores and retrieves agent trading experiences for learning and improvement.
Each agent maintains its own memory of past trades, predictions, and lessons learned.

Enhanced Features (2024-12):
- AgentPrediction: Records each Agent's prediction at position opening
- TradeReflection: Post-trade reflection summary generated after closing
- Enhanced memory injection into next meeting's prompt
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
import redis.asyncio as redis

logger = logging.getLogger(__name__)


# ============================================
# Agent Prediction Records
# ============================================

@dataclass
class AgentPrediction:
    """Single Agent's prediction record for one trade"""
    agent_id: str           # Agent ID
    agent_name: str         # Agent name
    trade_id: str           # Trade ID (linked to specific trade)
    timestamp: datetime     # Prediction time

    # Prediction content
    direction: str          # Predicted direction: "long" / "short" / "hold"
    confidence: int         # Confidence: 0-100
    reasoning: str          # Prediction reasoning
    key_factors: List[str] = field(default_factory=list)  # Key factors

    # Market state snapshot
    market_price: float = 0.0
    market_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentPrediction':
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


# ============================================
# Trade Reflection Records
# ============================================

@dataclass
class TradeReflection:
    """Post-trade reflection after closing position"""
    trade_id: str
    agent_id: str
    agent_name: str
    timestamp: datetime

    # Trade result
    entry_price: float
    exit_price: float
    direction: str
    pnl: float
    pnl_percent: float
    holding_duration_hours: float = 0.0
    close_reason: str = ""       # "tp" / "sl" / "manual" / "reverse"

    # Prediction vs Result
    original_prediction: str = ""  # Original prediction direction
    prediction_was_correct: bool = False

    # LLM generated reflection content
    reflection_summary: str = ""           # Overall reflection summary
    what_went_well: List[str] = field(default_factory=list)
    what_went_wrong: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    next_time_action: str = ""  # Suggested action for similar situations

    # === NEW: Enhanced structured fields ===
    # Market condition at trade time
    market_condition: str = ""  # "trending_up" / "trending_down" / "ranging" / "volatile" / "calm"
    volatility_level: str = ""  # "high" / "normal" / "low"
    
    # Trade quality evaluation
    entry_timing: str = ""      # "excellent" / "good" / "neutral" / "poor" / "terrible"
    exit_timing: str = ""       # "excellent" / "good" / "neutral" / "poor" / "terrible"
    risk_taken: str = ""        # "appropriate" / "aggressive" / "conservative"
    
    # Pattern tags for future matching
    pattern_tags: List[str] = field(default_factory=list)  # e.g., ["breakout", "reversal", "trend_follow"]
    key_indicators_used: List[str] = field(default_factory=list)  # e.g., ["RSI_oversold", "MACD_cross"]
    
    # Similarity matching score (for finding similar past trades)
    market_snapshot_hash: str = ""  # Hash of market conditions for similarity matching

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeReflection':
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

    def get_summary_for_prompt(self) -> str:
        """Generate enhanced summary for prompt injection with market context"""
        emoji = "✅" if self.pnl > 0 else "❌"
        direction_text = "Long" if self.direction == "long" else "Short" if self.direction == "short" else "Hold"

        summary = f"{emoji} Last trade: {direction_text} BTC, "
        if self.pnl > 0:
            summary += f"Profit ${self.pnl:.2f} (+{self.pnl_percent:.1f}%)"
        else:
            summary += f"Loss ${abs(self.pnl):.2f} ({self.pnl_percent:.1f}%)"

        # Add market condition context
        if self.market_condition:
            condition_emoji = {
                "trending_up": "📈", "trending_down": "📉", 
                "ranging": "↔️", "volatile": "⚡", "calm": "😌"
            }.get(self.market_condition, "")
            summary += f"\nMarket: {condition_emoji} {self.market_condition}"
        
        # Add timing evaluation
        if self.entry_timing:
            timing_emoji = {"excellent": "🎯", "good": "👍", "neutral": "➖", "poor": "👎", "terrible": "💀"}.get(self.entry_timing, "")
            summary += f" | Entry: {timing_emoji} {self.entry_timing}"

        # Add lesson
        if self.lessons_learned:
            summary += f"\nLesson: {self.lessons_learned[0]}"

        return summary


@dataclass
class TradeExperience:
    """Record of a single trading experience"""
    trade_id: str
    timestamp: datetime
    agent_id: str
    prediction: Dict[str, Any]  # What the agent predicted
    actual_outcome: Dict[str, Any]  # What actually happened
    was_correct: bool
    pnl: float
    lesson_learned: Optional[str] = None


@dataclass
class AgentMemory:
    """Memory storage for a single agent"""
    agent_id: str
    agent_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    average_pnl: float = 0.0
    best_trade_pnl: float = 0.0
    worst_trade_pnl: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    lessons_learned: List[str] = field(default_factory=list)
    recent_experiences: List[Dict] = field(default_factory=list)
    prediction_accuracy: Dict[str, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    # Reflection related fields
    recent_reflections: List[Dict] = field(default_factory=list)  # Recent reflection records
    last_trade_summary: str = ""  # Brief summary of last trade
    current_focus: str = ""       # Current focus points to pay attention to
    common_mistakes: List[str] = field(default_factory=list)  # Common mistakes made
    
    # 🆕 Context Engineering: Compacted historical summary
    compacted_history_summary: str = ""  # Summary of older reflections (beyond recent 10)

    def get_recent_win_rate(self, n: int = 10) -> float:
        """
        Calculate win rate for the most recent N trades.
        
        Args:
            n: Number of recent trades to consider
            
        Returns:
            Win rate between 0.0 and 1.0
        """
        if not self.recent_reflections and not self.recent_experiences:
            return 0.5  # Default to 50% if no history
        
        # Get recent trades from reflections (preferred) or experiences
        recent_trades = []
        
        if self.recent_reflections:
            for ref in self.recent_reflections[-n:]:
                pnl = ref.get('pnl', 0)
                recent_trades.append(pnl > 0)
        elif self.recent_experiences:
            for exp in self.recent_experiences[-n:]:
                pnl = exp.get('pnl', 0)
                recent_trades.append(pnl > 0)
        
        if not recent_trades:
            return 0.5
        
        return sum(recent_trades) / len(recent_trades)

    def _compact_old_reflection(self, old_reflection: Dict):
        """
        🆕 Context Engineering: Summarize old reflection before discarding.
        Appends key info to compacted_history_summary string.
        """
        # Extract key info from old reflection
        pnl = old_reflection.get('pnl', 0)
        direction = old_reflection.get('direction', 'unknown')
        result = "win" if pnl > 0 else "loss"
        lessons = old_reflection.get('lessons_learned', [])
        
        # Create concise summary line
        summary_line = f"• {direction} {result} (${pnl:.2f})"
        if lessons and len(lessons) > 0:
            summary_line += f": {lessons[0][:50]}"
        
        # Append to compacted summary (keep under 500 chars)
        if self.compacted_history_summary:
            self.compacted_history_summary = (
                self.compacted_history_summary + "\n" + summary_line
            )[-500:]
        else:
            self.compacted_history_summary = summary_line

    def add_trade_result(self, experience: TradeExperience):
        """Add a new trade result and update statistics"""
        self.total_trades += 1

        if experience.pnl > 0:
            self.winning_trades += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.max_consecutive_wins = max(self.max_consecutive_wins, self.consecutive_wins)
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.max_consecutive_losses = max(self.max_consecutive_losses, self.consecutive_losses)

        self.total_pnl += experience.pnl
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        self.average_pnl = self.total_pnl / self.total_trades if self.total_trades > 0 else 0

        self.best_trade_pnl = max(self.best_trade_pnl, experience.pnl)
        self.worst_trade_pnl = min(self.worst_trade_pnl, experience.pnl)

        # Add lesson if provided
        if experience.lesson_learned:
            self.lessons_learned.append(experience.lesson_learned)
            # Keep only last 20 lessons
            if len(self.lessons_learned) > 20:
                self.lessons_learned = self.lessons_learned[-20:]

        # Store recent experience
        self.recent_experiences.append(asdict(experience))
        # Keep only last 50 experiences
        if len(self.recent_experiences) > 50:
            self.recent_experiences = self.recent_experiences[-50:]

        self.last_updated = datetime.now()

    def add_reflection(self, reflection: 'TradeReflection'):
        """Add a trade reflection while updating trade statistics"""
        # Save reflection record
        self.recent_reflections.append(reflection.to_dict())
        
        # 🆕 Context Engineering: Compact old reflections before discarding
        if len(self.recent_reflections) > 10:
            # Summarize the oldest reflection before removing
            old_reflection = self.recent_reflections[0]
            self._compact_old_reflection(old_reflection)
            self.recent_reflections = self.recent_reflections[-10:]

        # Update last trade summary
        self.last_trade_summary = reflection.get_summary_for_prompt()

        # Update trade statistics
        self.total_trades += 1
        self.total_pnl += reflection.pnl

        if reflection.pnl > 0:
            self.winning_trades += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.max_consecutive_wins = max(self.max_consecutive_wins, self.consecutive_wins)
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.max_consecutive_losses = max(self.max_consecutive_losses, self.consecutive_losses)

        # Update win rate and average pnl
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        self.average_pnl = self.total_pnl / self.total_trades if self.total_trades > 0 else 0

        # Update best/worst trade
        self.best_trade_pnl = max(self.best_trade_pnl, reflection.pnl)
        self.worst_trade_pnl = min(self.worst_trade_pnl, reflection.pnl)

        # Accumulate lessons
        for lesson in reflection.lessons_learned:
            if lesson and lesson not in self.lessons_learned:
                self.lessons_learned.append(lesson)
        # Keep only last 20 lessons
        if len(self.lessons_learned) > 20:
            self.lessons_learned = self.lessons_learned[-20:]

        # Update current focus
        if reflection.next_time_action:
            self.current_focus = reflection.next_time_action

        # If loss, record mistakes
        if reflection.pnl < 0 and reflection.what_went_wrong:
            for mistake in reflection.what_went_wrong:
                if mistake and mistake not in self.common_mistakes:
                    self.common_mistakes.append(mistake)
            # Keep only last 10 mistakes
            if len(self.common_mistakes) > 10:
                self.common_mistakes = self.common_mistakes[-10:]

        self.last_updated = datetime.now()

    def get_context_for_prompt(self) -> str:
        """Generate enhanced context string for agent's system prompt"""
        context_parts = []

        # 1. Last trade review (most important, placed first)
        if self.last_trade_summary:
            context_parts.append(f"## 📊 Last Trade Review\n{self.last_trade_summary}")

        # 2. Current focus points
        if self.current_focus:
            context_parts.append(f"\n## ⚠️ Current Focus\n{self.current_focus}")

        # 3. Accumulated lessons learned
        if self.lessons_learned:
            context_parts.append("\n## 📝 Lessons You've Learned")
            for lesson in self.lessons_learned[-5:]:  # Last 5 lessons
                context_parts.append(f"- {lesson}")

        # 4. Trading statistics (if has trade history)
        if self.total_trades > 0:
            context_parts.append(f"""
## 📈 Your Trading Performance
- Total Trades: {self.total_trades}
- Win Rate: {self.win_rate*100:.1f}%
- Total P&L: ${self.total_pnl:,.2f}
- Average P&L: ${self.average_pnl:,.2f}""")

            if self.consecutive_wins > 0:
                context_parts.append(f"- Current Win Streak: {self.consecutive_wins}")
            elif self.consecutive_losses > 0:
                context_parts.append(f"- Current Losing Streak: {self.consecutive_losses}")

        # 5. Common mistakes reminder
        if self.common_mistakes:
            context_parts.append("\n## 🚫 Mistakes to Avoid")
            for mistake in self.common_mistakes[-3:]:
                context_parts.append(f"- {mistake}")

        # 6. Strengths and weaknesses
        if self.strengths:
            context_parts.append("\n## ✅ Your Strengths")
            for s in self.strengths[:3]:
                context_parts.append(f"- {s}")

        if self.weaknesses:
            context_parts.append("\n## 🔧 Areas for Improvement")
            for w in self.weaknesses[:3]:
                context_parts.append(f"- {w}")

        return "\n".join(context_parts)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentMemory':
        """Create from dictionary"""
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


class AgentMemoryStore:
    """
    Persistent storage for agent memories using Redis.

    Features:
    - Store/retrieve agent memories
    - Track performance across sessions
    - Generate learning insights
    """

    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._local_cache: Dict[str, AgentMemory] = {}
        self.key_prefix = "trading:agent_memory:"

    async def connect(self):
        """Connect to Redis"""
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("Connected to Redis for agent memory storage")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using local cache only.")
            self._redis = None

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()

    async def get_memory(self, agent_id: str, agent_name: str = "") -> AgentMemory:
        """Get agent memory, creating if doesn't exist"""
        # Check local cache first
        if agent_id in self._local_cache:
            return self._local_cache[agent_id]

        # Try to load from Redis
        if self._redis:
            try:
                key = f"{self.key_prefix}{agent_id}"
                data = await self._redis.get(key)
                if data:
                    memory = AgentMemory.from_dict(json.loads(data))
                    self._local_cache[agent_id] = memory
                    return memory
            except Exception as e:
                logger.error(f"Error loading memory from Redis: {e}")

        # Create new memory
        memory = AgentMemory(agent_id=agent_id, agent_name=agent_name)
        self._local_cache[agent_id] = memory
        return memory

    async def save_memory(self, memory: AgentMemory):
        """Save agent memory to Redis"""
        self._local_cache[memory.agent_id] = memory

        if self._redis:
            try:
                key = f"{self.key_prefix}{memory.agent_id}"
                await self._redis.set(key, json.dumps(memory.to_dict()))
            except Exception as e:
                logger.error(f"Error saving memory to Redis: {e}")

    async def record_trade_result(
        self,
        agent_id: str,
        agent_name: str,
        trade_id: str,
        prediction: Dict[str, Any],
        actual_outcome: Dict[str, Any],
        pnl: float,
        lesson: Optional[str] = None
    ):
        """Record a trade result for an agent"""
        memory = await self.get_memory(agent_id, agent_name)

        # Determine if prediction was correct
        was_correct = self._evaluate_prediction(prediction, actual_outcome)

        experience = TradeExperience(
            trade_id=trade_id,
            timestamp=datetime.now(),
            agent_id=agent_id,
            prediction=prediction,
            actual_outcome=actual_outcome,
            was_correct=was_correct,
            pnl=pnl,
            lesson_learned=lesson
        )

        memory.add_trade_result(experience)
        await self.save_memory(memory)

        # Generate insights after certain number of trades
        if memory.total_trades % 10 == 0:
            await self._generate_insights(memory)

    def _evaluate_prediction(self, prediction: Dict, outcome: Dict) -> bool:
        """Evaluate if agent's prediction was correct"""
        pred_direction = prediction.get('direction', 'hold')
        actual_pnl = outcome.get('pnl', 0)

        if pred_direction == 'long':
            return actual_pnl > 0
        elif pred_direction == 'short':
            return actual_pnl > 0  # If short was suggested and we made money
        else:
            # Hold prediction - correct if no significant movement
            return True

    async def _generate_insights(self, memory: AgentMemory):
        """Generate insights about agent's performance"""
        # Analyze strengths
        if memory.win_rate > 0.6:
            memory.strengths.append("High overall win rate")
        if memory.max_consecutive_wins > 5:
            memory.strengths.append("Able to maintain consecutive wins")
        if memory.average_pnl > 0:
            memory.strengths.append("Positive average P&L per trade")

        # Analyze weaknesses
        if memory.max_consecutive_losses > 3:
            memory.weaknesses.append("Need better risk control for consecutive losses")
        if memory.win_rate < 0.4:
            memory.weaknesses.append("Win rate too low, need better judgment accuracy")
        if memory.worst_trade_pnl < -500:
            memory.weaknesses.append("Large single-trade loss, need stricter stop loss")

        # Keep unique items
        memory.strengths = list(set(memory.strengths))[:5]
        memory.weaknesses = list(set(memory.weaknesses))[:5]

        await self.save_memory(memory)

    async def get_all_memories(self) -> Dict[str, AgentMemory]:
        """Get all agent memories"""
        if self._redis:
            try:
                keys = await self._redis.keys(f"{self.key_prefix}*")
                for key in keys:
                    agent_id = key.replace(self.key_prefix, "")
                    if agent_id not in self._local_cache:
                        data = await self._redis.get(key)
                        if data:
                            self._local_cache[agent_id] = AgentMemory.from_dict(json.loads(data))
            except Exception as e:
                logger.error(f"Error loading all memories: {e}")

        return self._local_cache

    async def get_team_summary(self) -> Dict[str, Any]:
        """Get summary of entire team's performance"""
        memories = await self.get_all_memories()

        if not memories:
            return {
                "total_agents": 0,
                "team_win_rate": 0,
                "team_total_pnl": 0,
                "best_performer": None,
                "needs_improvement": None
            }

        total_trades = sum(m.total_trades for m in memories.values())
        total_wins = sum(m.winning_trades for m in memories.values())
        total_pnl = sum(m.total_pnl for m in memories.values())

        # Find best and worst performers
        sorted_by_pnl = sorted(memories.values(), key=lambda m: m.total_pnl, reverse=True)

        return {
            "total_agents": len(memories),
            "team_total_trades": total_trades,
            "team_win_rate": total_wins / total_trades if total_trades > 0 else 0,
            "team_total_pnl": total_pnl,
            "best_performer": sorted_by_pnl[0].agent_name if sorted_by_pnl else None,
            "needs_improvement": sorted_by_pnl[-1].agent_name if len(sorted_by_pnl) > 1 else None
        }

    async def clear_all_memories(self):
        """Clear all agent memories (for testing)"""
        self._local_cache.clear()
        if self._redis:
            try:
                keys = await self._redis.keys(f"{self.key_prefix}*")
                if keys:
                    await self._redis.delete(*keys)
            except Exception as e:
                logger.error(f"Error clearing memories: {e}")


# ============================================
# Prediction Storage and Reflection Generation
# ============================================

class PredictionStore:
    """
    Store and manage Agent prediction records
    Used for generating reflections when closing positions
    """

    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._local_cache: Dict[str, List[AgentPrediction]] = {}  # trade_id -> predictions
        self.key_prefix = "trading:predictions:"

    async def connect(self):
        """Connect to Redis"""
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("PredictionStore connected to Redis")
        except Exception as e:
            logger.warning(f"PredictionStore failed to connect to Redis: {e}. Using local cache.")
            self._redis = None

    async def save_prediction(self, prediction: AgentPrediction):
        """Save an Agent's prediction"""
        trade_id = prediction.trade_id

        # Add to local cache
        if trade_id not in self._local_cache:
            self._local_cache[trade_id] = []
        self._local_cache[trade_id].append(prediction)

        # Save to Redis
        if self._redis:
            try:
                key = f"{self.key_prefix}{trade_id}"
                predictions_data = [p.to_dict() for p in self._local_cache[trade_id]]
                await self._redis.set(key, json.dumps(predictions_data))
                # Set expiration: 7 days
                await self._redis.expire(key, 7 * 24 * 3600)
            except Exception as e:
                logger.error(f"Error saving prediction to Redis: {e}")

    async def get_predictions(self, trade_id: str) -> List[AgentPrediction]:
        """Get all Agent predictions for a trade"""
        # Check local cache first
        if trade_id in self._local_cache:
            return self._local_cache[trade_id]

        # Load from Redis
        if self._redis:
            try:
                key = f"{self.key_prefix}{trade_id}"
                data = await self._redis.get(key)
                if data:
                    predictions_data = json.loads(data)
                    predictions = [AgentPrediction.from_dict(p) for p in predictions_data]
                    self._local_cache[trade_id] = predictions
                    return predictions
            except Exception as e:
                logger.error(f"Error loading predictions from Redis: {e}")

        return []

    async def clear_predictions(self, trade_id: str):
        """Clear prediction records for a trade (optionally called after closing)"""
        if trade_id in self._local_cache:
            del self._local_cache[trade_id]

        if self._redis:
            try:
                key = f"{self.key_prefix}{trade_id}"
                await self._redis.delete(key)
            except Exception as e:
                logger.error(f"Error clearing predictions: {e}")


class ReflectionGenerator:
    """
    Reflection Generator
    Uses LLM to generate trade reflections for each Agent
    """

    def __init__(self, llm_client=None):
        self._llm_client = llm_client

    def set_llm_client(self, llm_client):
        """Set LLM client"""
        self._llm_client = llm_client

    async def generate_reflection(
        self,
        prediction: AgentPrediction,
        trade_result: Dict[str, Any]
    ) -> TradeReflection:
        """
        Generate trade reflection for a single Agent

        Args:
            prediction: Agent's original prediction
            trade_result: Trade result {entry_price, exit_price, pnl, direction, reason, holding_hours}
        """
        entry_price = trade_result.get('entry_price', 0)
        exit_price = trade_result.get('exit_price', 0)
        pnl = trade_result.get('pnl', 0)
        direction = trade_result.get('direction', 'long')
        close_reason = trade_result.get('reason', 'manual')
        holding_hours = trade_result.get('holding_hours', 0)

        # Calculate pnl percentage
        pnl_percent = 0
        if entry_price > 0:
            if direction == 'long':
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100

        # Determine if prediction was correct
        prediction_correct = False
        if prediction.direction == direction:
            # Agent predicted same direction as actual trade
            prediction_correct = pnl > 0  # Profit means prediction was correct
        elif prediction.direction == "hold":
            # Agent suggested hold, but position was opened anyway
            prediction_correct = pnl < 0  # Loss means should have listened to Agent
        else:
            # Agent predicted opposite direction to actual trade
            prediction_correct = pnl < 0  # Loss means should have listened to Agent

        # Try to generate detailed reflection using LLM
        reflection_data = await self._generate_llm_reflection(
            prediction, trade_result, prediction_correct
        )

        # Create reflection record with enhanced structured fields
        return TradeReflection(
            trade_id=prediction.trade_id,
            agent_id=prediction.agent_id,
            agent_name=prediction.agent_name,
            timestamp=datetime.now(),
            entry_price=entry_price,
            exit_price=exit_price,
            direction=direction,
            pnl=pnl,
            pnl_percent=pnl_percent,
            holding_duration_hours=holding_hours,
            close_reason=close_reason,
            original_prediction=prediction.direction,
            prediction_was_correct=prediction_correct,
            # Original reflection fields
            reflection_summary=reflection_data.get('summary', ''),
            what_went_well=reflection_data.get('what_went_well', []),
            what_went_wrong=reflection_data.get('what_went_wrong', []),
            lessons_learned=reflection_data.get('lessons_learned', []),
            next_time_action=reflection_data.get('next_time_action', ''),
            # NEW: Enhanced structured fields
            market_condition=reflection_data.get('market_condition', ''),
            volatility_level=reflection_data.get('volatility_level', ''),
            entry_timing=reflection_data.get('entry_timing', ''),
            exit_timing=reflection_data.get('exit_timing', ''),
            risk_taken=reflection_data.get('risk_taken', ''),
            pattern_tags=reflection_data.get('pattern_tags', []),
            key_indicators_used=reflection_data.get('key_indicators_used', []),
        )

    async def _generate_llm_reflection(
        self,
        prediction: AgentPrediction,
        trade_result: Dict[str, Any],
        prediction_correct: bool
    ) -> Dict[str, Any]:
        """Generate detailed reflection using LLM (falls back to rules if fails)"""

        # If no LLM client, use rule-based generation
        if not self._llm_client:
            return self._generate_rule_based_reflection(
                prediction, trade_result, prediction_correct
            )

        try:
            direction_text = {"long": "Long", "short": "Short", "hold": "Hold"}.get(
                prediction.direction, prediction.direction
            )
            pnl = trade_result.get('pnl', 0)
            entry_price = trade_result.get('entry_price', 0)
            exit_price = trade_result.get('exit_price', 0)

            prompt = f"""You are {prediction.agent_name}, please reflect on this trade:

## Your Prediction at the Time
- Direction: {direction_text}
- Confidence: {prediction.confidence}%
- Reasoning: {prediction.reasoning}
- Key Factors: {', '.join(prediction.key_factors) if prediction.key_factors else 'None'}
- Price at Time: ${prediction.market_price:,.2f}

## Actual Result
- Entry Price: ${entry_price:,.2f}
- Exit Price: ${exit_price:,.2f}
- P&L: ${pnl:+,.2f}
- Close Reason: {trade_result.get('reason', 'manual')}
- Holding Duration: {trade_result.get('holding_hours', 0):.1f} hours

## Analysis Tasks

1. **Market Condition Assessment**: What was the market doing during this trade?
   - Market type: trending_up / trending_down / ranging / volatile / calm
   - Volatility: high / normal / low

2. **Trade Quality Evaluation**:
   - Entry timing: excellent / good / neutral / poor / terrible
   - Exit timing: excellent / good / neutral / poor / terrible
   - Risk level: appropriate / aggressive / conservative

3. **Pattern Recognition**: What patterns or setups were involved?

4. **Your prediction was {'correct' if prediction_correct else 'incorrect'}** - Why?

5. **What lessons did you learn?** List 1-2 specific actionable lessons

Please respond in JSON format without markdown code block markers:
{{
    "summary": "One sentence summarizing this trade outcome",
    "market_condition": "trending_up|trending_down|ranging|volatile|calm",
    "volatility_level": "high|normal|low",
    "entry_timing": "excellent|good|neutral|poor|terrible",
    "exit_timing": "excellent|good|neutral|poor|terrible",
    "risk_taken": "appropriate|aggressive|conservative",
    "pattern_tags": ["pattern1", "pattern2"],
    "key_indicators_used": ["indicator1", "indicator2"],
    "what_went_well": ["thing done right 1"],
    "what_went_wrong": ["thing done wrong 1"],
    "lessons_learned": ["lesson 1", "lesson 2"],
    "next_time_action": "One sentence action for similar situations"
}}"""

            # Call LLM
            messages = [
                {"role": "system", "content": "You are a trading reflection assistant, helping analyze trading successes and failures. Please respond concisely, each lesson no more than 30 words."},
                {"role": "user", "content": prompt}
            ]

            response = await self._llm_client._call_llm(messages)

            # Parse response
            content = ""
            if isinstance(response, dict):
                if "choices" in response:
                    try:
                        content = response["choices"][0]["message"]["content"]
                    except (KeyError, IndexError):
                        pass
                if not content:
                    content = response.get("content", response.get("response", ""))
            else:
                content = str(response)

            # Try to parse JSON
            if content:
                # Remove possible markdown code block markers
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1] if "\n" in content else content
                if content.endswith("```"):
                    content = content.rsplit("```", 1)[0]
                content = content.strip()

                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse LLM reflection response as JSON")

        except Exception as e:
            logger.error(f"Error generating LLM reflection: {e}")

        # Fallback to rule-based generation
        return self._generate_rule_based_reflection(
            prediction, trade_result, prediction_correct
        )

    def _generate_rule_based_reflection(
        self,
        prediction: AgentPrediction,
        trade_result: Dict[str, Any],
        prediction_correct: bool
    ) -> Dict[str, Any]:
        """Generate simple reflection using rules (fallback when LLM fails)"""
        pnl = trade_result.get('pnl', 0)
        direction_text = {"long": "Long", "short": "Short", "hold": "Hold"}.get(
            prediction.direction, prediction.direction
        )

        if pnl > 0:
            # Profit
            summary = f"Trade profit ${pnl:.2f}, {'prediction correct' if prediction_correct else 'opposite prediction but still profitable'}"
            what_went_well = [f"Direction judgment {'correct' if prediction_correct else 'market gave opportunity'}"]
            what_went_wrong = []
            lessons = ["Maintain current analysis method"]
            next_action = "Continue using current strategy"
        else:
            # Loss
            summary = f"Trade loss ${abs(pnl):.2f}, needs reflection"
            what_went_well = []
            what_went_wrong = [f"{'Direction judgment wrong' if not prediction_correct else 'Direction correct but poor entry timing'}"]
            if prediction.confidence > 70:
                lessons = ["High confidence predictions can also be wrong, need more confirmation"]
            else:
                lessons = ["Should reduce position or hold when low confidence"]
            next_action = "Be more cautious next time, wait for clearer signals"

        return {
            "summary": summary,
            "what_went_well": what_went_well,
            "what_went_wrong": what_went_wrong,
            "lessons_learned": lessons,
            "next_time_action": next_action,
            # NEW: Default structured fields for rule-based fallback
            "market_condition": "unknown",
            "volatility_level": "normal",
            "entry_timing": "neutral" if pnl > 0 else "poor",
            "exit_timing": "neutral",
            "risk_taken": "appropriate" if abs(pnl) < 100 else ("aggressive" if pnl < 0 else "appropriate"),
            "pattern_tags": [],
            "key_indicators_used": [],
        }


# Singleton instances
_memory_store: Optional[AgentMemoryStore] = None
_prediction_store: Optional[PredictionStore] = None
_reflection_generator: Optional[ReflectionGenerator] = None


async def get_memory_store() -> AgentMemoryStore:
    """Get or create memory store singleton"""
    global _memory_store
    if _memory_store is None:
        _memory_store = AgentMemoryStore()
        await _memory_store.connect()
    return _memory_store


async def get_prediction_store() -> PredictionStore:
    """Get or create prediction store singleton"""
    global _prediction_store
    if _prediction_store is None:
        _prediction_store = PredictionStore()
        await _prediction_store.connect()
    return _prediction_store


def get_reflection_generator() -> ReflectionGenerator:
    """Get or create reflection generator singleton"""
    global _reflection_generator
    if _reflection_generator is None:
        _reflection_generator = ReflectionGenerator()
    return _reflection_generator


async def record_agent_predictions(
    trade_id: str,
    votes: Dict[str, Dict[str, Any]],
    market_price: float = 0.0
):
    """
    Record all Agent predictions

    Args:
        trade_id: Trade ID (usually position ID)
        votes: Agent vote results {agent_name: {direction, confidence, reasoning}}
        market_price: Market price at the time
    """
    store = await get_prediction_store()

    for agent_name, vote in votes.items():
        prediction = AgentPrediction(
            agent_id=agent_name,
            agent_name=agent_name,
            trade_id=trade_id,
            timestamp=datetime.now(),
            direction=vote.get('direction', 'hold'),
            confidence=vote.get('confidence', 0),
            reasoning=vote.get('reasoning', ''),
            key_factors=vote.get('key_factors', []),
            market_price=market_price,
            market_snapshot=vote.get('market_snapshot', {})
        )
        await store.save_prediction(prediction)

    logger.info(f"Recorded {len(votes)} agent predictions for trade {trade_id}")


async def generate_trade_reflections(
    trade_id: str,
    trade_result: Dict[str, Any],
    llm_client=None
) -> List[TradeReflection]:
    """
    Generate reflections for all Agents after closing position

    Args:
        trade_id: Trade ID
        trade_result: Trade result {entry_price, exit_price, pnl, direction, reason, holding_hours}
        llm_client: LLM client for generating reflections (optional)

    Returns:
        List of TradeReflection for each agent
    """
    prediction_store = await get_prediction_store()
    memory_store = await get_memory_store()
    generator = get_reflection_generator()

    if llm_client:
        generator.set_llm_client(llm_client)

    # Get all predictions for this trade
    predictions = await prediction_store.get_predictions(trade_id)

    if not predictions:
        logger.warning(f"No predictions found for trade {trade_id}")
        return []

    reflections = []

    for prediction in predictions:
        try:
            # Generate reflection
            reflection = await generator.generate_reflection(prediction, trade_result)
            reflections.append(reflection)

            # Update Agent memory
            memory = await memory_store.get_memory(prediction.agent_id, prediction.agent_name)
            memory.add_reflection(reflection)
            await memory_store.save_memory(memory)

            logger.info(f"Generated reflection for {prediction.agent_name}: "
                       f"{'correct' if reflection.prediction_was_correct else 'incorrect'}, "
                       f"PnL=${reflection.pnl:.2f}")

        except Exception as e:
            logger.error(f"Error generating reflection for {prediction.agent_name}: {e}")

    # Clear prediction records (optional, can also keep for historical analysis)
    # await prediction_store.clear_predictions(trade_id)

    return reflections
