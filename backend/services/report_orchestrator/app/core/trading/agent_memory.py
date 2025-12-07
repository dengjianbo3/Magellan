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
# 新增: Agent 预测记录
# ============================================

@dataclass
class AgentPrediction:
    """单个 Agent 在一次交易中的预测记录"""
    agent_id: str           # Agent ID
    agent_name: str         # Agent 名称
    trade_id: str           # 交易 ID（关联到具体交易）
    timestamp: datetime     # 预测时间

    # 预测内容
    direction: str          # 预测方向: "long" / "short" / "hold"
    confidence: int         # 置信度: 0-100
    reasoning: str          # 预测理由
    key_factors: List[str] = field(default_factory=list)  # 关键因素

    # 市场状态快照
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
# 新增: 交易反思记录
# ============================================

@dataclass
class TradeReflection:
    """平仓后的交易反思"""
    trade_id: str
    agent_id: str
    agent_name: str
    timestamp: datetime

    # 交易结果
    entry_price: float
    exit_price: float
    direction: str
    pnl: float
    pnl_percent: float
    holding_duration_hours: float = 0.0
    close_reason: str = ""       # "tp" / "sl" / "manual" / "reverse"

    # 预测 vs 结果
    original_prediction: str = ""  # 原始预测方向
    prediction_was_correct: bool = False

    # LLM 生成的反思内容
    reflection_summary: str = ""           # 整体反思总结
    what_went_well: List[str] = field(default_factory=list)
    what_went_wrong: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    next_time_action: str = ""  # 下次遇到类似情况的行动建议

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
        """Generate short summary for prompt injection"""
        emoji = "✅" if self.pnl > 0 else "❌"
        direction_text = "Long" if self.direction == "long" else "Short" if self.direction == "short" else "Hold"

        summary = f"{emoji} Last trade: {direction_text} BTC, "
        if self.pnl > 0:
            summary += f"Profit ${self.pnl:.2f} (+{self.pnl_percent:.1f}%)"
        else:
            summary += f"Loss ${abs(self.pnl):.2f} ({self.pnl_percent:.1f}%)"

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

    # 🆕 新增: 反思相关字段
    recent_reflections: List[Dict] = field(default_factory=list)  # 最近的反思记录
    last_trade_summary: str = ""  # 上次交易的简短总结
    current_focus: str = ""       # 当前需要注意的重点
    common_mistakes: List[str] = field(default_factory=list)  # 常犯的错误

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
        """添加一次交易反思，同时更新交易统计"""
        # 保存反思记录
        self.recent_reflections.append(reflection.to_dict())
        # 只保留最近 10 次
        if len(self.recent_reflections) > 10:
            self.recent_reflections = self.recent_reflections[-10:]

        # 更新上次交易总结
        self.last_trade_summary = reflection.get_summary_for_prompt()

        # 🆕 更新交易统计
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

        # 更新胜率和平均盈亏
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        self.average_pnl = self.total_pnl / self.total_trades if self.total_trades > 0 else 0

        # 更新最佳/最差交易
        self.best_trade_pnl = max(self.best_trade_pnl, reflection.pnl)
        self.worst_trade_pnl = min(self.worst_trade_pnl, reflection.pnl)

        # 累积教训
        for lesson in reflection.lessons_learned:
            if lesson and lesson not in self.lessons_learned:
                self.lessons_learned.append(lesson)
        # 只保留最近 20 条
        if len(self.lessons_learned) > 20:
            self.lessons_learned = self.lessons_learned[-20:]

        # 更新当前关注点
        if reflection.next_time_action:
            self.current_focus = reflection.next_time_action

        # 如果亏损，记录错误
        if reflection.pnl < 0 and reflection.what_went_wrong:
            for mistake in reflection.what_went_wrong:
                if mistake and mistake not in self.common_mistakes:
                    self.common_mistakes.append(mistake)
            # 只保留最近 10 个错误
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
# 预测记录存储和反思生成
# ============================================

class PredictionStore:
    """
    存储和管理 Agent 预测记录
    用于在平仓时生成反思
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
        """保存一个 Agent 的预测"""
        trade_id = prediction.trade_id

        # 添加到本地缓存
        if trade_id not in self._local_cache:
            self._local_cache[trade_id] = []
        self._local_cache[trade_id].append(prediction)

        # 保存到 Redis
        if self._redis:
            try:
                key = f"{self.key_prefix}{trade_id}"
                predictions_data = [p.to_dict() for p in self._local_cache[trade_id]]
                await self._redis.set(key, json.dumps(predictions_data))
                # 设置过期时间: 7天
                await self._redis.expire(key, 7 * 24 * 3600)
            except Exception as e:
                logger.error(f"Error saving prediction to Redis: {e}")

    async def get_predictions(self, trade_id: str) -> List[AgentPrediction]:
        """获取一笔交易的所有 Agent 预测"""
        # 先查本地缓存
        if trade_id in self._local_cache:
            return self._local_cache[trade_id]

        # 从 Redis 加载
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
        """清除一笔交易的预测记录（平仓后可选调用）"""
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
    反思生成器
    使用 LLM 为每个 Agent 生成交易反思
    """

    def __init__(self, llm_client=None):
        self._llm_client = llm_client

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    async def generate_reflection(
        self,
        prediction: AgentPrediction,
        trade_result: Dict[str, Any]
    ) -> TradeReflection:
        """
        为单个 Agent 生成交易反思

        Args:
            prediction: Agent 的原始预测
            trade_result: 交易结果 {entry_price, exit_price, pnl, direction, reason, holding_hours}
        """
        entry_price = trade_result.get('entry_price', 0)
        exit_price = trade_result.get('exit_price', 0)
        pnl = trade_result.get('pnl', 0)
        direction = trade_result.get('direction', 'long')
        close_reason = trade_result.get('reason', 'manual')
        holding_hours = trade_result.get('holding_hours', 0)

        # 计算盈亏百分比
        pnl_percent = 0
        if entry_price > 0:
            if direction == 'long':
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100

        # 判断预测是否正确
        prediction_correct = False
        if prediction.direction == direction:
            # Agent 预测方向与实际开仓方向一致
            prediction_correct = pnl > 0  # 盈利则预测正确
        elif prediction.direction == "hold":
            # Agent 建议观望，但还是开仓了
            prediction_correct = pnl < 0  # 亏损说明应该听 Agent 的
        else:
            # Agent 预测方向与实际开仓方向相反
            prediction_correct = pnl < 0  # 亏损说明应该听 Agent 的

        # 尝试使用 LLM 生成详细反思
        reflection_data = await self._generate_llm_reflection(
            prediction, trade_result, prediction_correct
        )

        # 创建反思记录
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
            reflection_summary=reflection_data.get('summary', ''),
            what_went_well=reflection_data.get('what_went_well', []),
            what_went_wrong=reflection_data.get('what_went_wrong', []),
            lessons_learned=reflection_data.get('lessons_learned', []),
            next_time_action=reflection_data.get('next_time_action', '')
        )

    async def _generate_llm_reflection(
        self,
        prediction: AgentPrediction,
        trade_result: Dict[str, Any],
        prediction_correct: bool
    ) -> Dict[str, Any]:
        """使用 LLM 生成详细反思（如果失败则使用规则生成）"""

        # 如果没有 LLM 客户端，使用规则生成
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

## Please Answer the Following Questions

1. **Your prediction was {'correct' if prediction_correct else 'incorrect'}** - Why?

2. **What judgments were correct?** List 1-2 points

3. **What judgments were wrong?** List 1-2 points

4. **What lessons did you learn?** List 1-2 specific actionable lessons

5. **What would you do differently next time?** One sentence summary

Please respond in JSON format, without markdown code block markers:
{{
    "summary": "One or two sentences summarizing the reflection",
    "what_went_well": ["thing done right 1", "thing done right 2"],
    "what_went_wrong": ["thing done wrong 1", "thing done wrong 2"],
    "lessons_learned": ["lesson 1", "lesson 2"],
    "next_time_action": "One sentence action recommendation for similar situations"
}}"""

            # Call LLM
            messages = [
                {"role": "system", "content": "You are a trading reflection assistant, helping analyze trading successes and failures. Please respond concisely, each lesson no more than 30 words."},
                {"role": "user", "content": prompt}
            ]

            response = await self._llm_client._call_llm(messages)

            # 解析响应
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

            # 尝试解析 JSON
            if content:
                # 移除可能的 markdown 代码块标记
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

        # 降级到规则生成
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
            "next_time_action": next_action
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
    记录所有 Agent 的预测

    Args:
        trade_id: 交易ID（通常是仓位ID）
        votes: Agent投票结果 {agent_name: {direction, confidence, reasoning}}
        market_price: 当时的市场价格
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
    平仓后生成所有 Agent 的反思

    Args:
        trade_id: 交易ID
        trade_result: 交易结果 {entry_price, exit_price, pnl, direction, reason, holding_hours}
        llm_client: 用于生成反思的 LLM 客户端（可选）

    Returns:
        List of TradeReflection for each agent
    """
    prediction_store = await get_prediction_store()
    memory_store = await get_memory_store()
    generator = get_reflection_generator()

    if llm_client:
        generator.set_llm_client(llm_client)

    # 获取这笔交易的所有预测
    predictions = await prediction_store.get_predictions(trade_id)

    if not predictions:
        logger.warning(f"No predictions found for trade {trade_id}")
        return []

    reflections = []

    for prediction in predictions:
        try:
            # 生成反思
            reflection = await generator.generate_reflection(prediction, trade_result)
            reflections.append(reflection)

            # 更新 Agent 记忆
            memory = await memory_store.get_memory(prediction.agent_id, prediction.agent_name)
            memory.add_reflection(reflection)
            await memory_store.save_memory(memory)

            logger.info(f"Generated reflection for {prediction.agent_name}: "
                       f"{'correct' if reflection.prediction_was_correct else 'incorrect'}, "
                       f"PnL=${reflection.pnl:.2f}")

        except Exception as e:
            logger.error(f"Error generating reflection for {prediction.agent_name}: {e}")

    # 清理预测记录（可选，也可以保留用于历史分析）
    # await prediction_store.clear_predictions(trade_id)

    return reflections
