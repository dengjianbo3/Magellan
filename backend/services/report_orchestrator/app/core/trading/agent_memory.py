"""
Agent Memory System

Stores and retrieves agent trading experiences for learning and improvement.
Each agent maintains its own memory of past trades, predictions, and lessons learned.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
import redis.asyncio as redis

logger = logging.getLogger(__name__)


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

    def get_context_for_prompt(self) -> str:
        """Generate context string for agent's system prompt"""
        context_parts = [
            f"## 你的交易历史统计",
            f"- 总交易次数: {self.total_trades}",
            f"- 胜率: {self.win_rate*100:.1f}%",
            f"- 总盈亏: ${self.total_pnl:,.2f}",
            f"- 平均盈亏: ${self.average_pnl:,.2f}",
            f"- 当前连胜: {self.consecutive_wins}次" if self.consecutive_wins > 0 else f"- 当前连败: {self.consecutive_losses}次",
        ]

        if self.lessons_learned:
            context_parts.append("\n## 你学到的经验教训")
            for lesson in self.lessons_learned[-5:]:  # Last 5 lessons
                context_parts.append(f"- {lesson}")

        if self.strengths:
            context_parts.append("\n## 你的优势")
            for s in self.strengths[:3]:
                context_parts.append(f"- {s}")

        if self.weaknesses:
            context_parts.append("\n## 你需要改进的地方")
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
            memory.strengths.append("整体胜率较高")
        if memory.max_consecutive_wins > 5:
            memory.strengths.append("能够保持连续盈利")
        if memory.average_pnl > 0:
            memory.strengths.append("平均每笔交易盈利")

        # Analyze weaknesses
        if memory.max_consecutive_losses > 3:
            memory.weaknesses.append("需要注意连续亏损的风险控制")
        if memory.win_rate < 0.4:
            memory.weaknesses.append("胜率偏低，需要提高判断准确性")
        if memory.worst_trade_pnl < -500:
            memory.weaknesses.append("存在较大单笔亏损，需要更严格的止损")

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


# Singleton instance
_memory_store: Optional[AgentMemoryStore] = None


async def get_memory_store() -> AgentMemoryStore:
    """Get or create memory store singleton"""
    global _memory_store
    if _memory_store is None:
        _memory_store = AgentMemoryStore()
        await _memory_store.connect()
    return _memory_store
