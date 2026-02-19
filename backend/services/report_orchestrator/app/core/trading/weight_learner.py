"""
Agent Weight Self-Learning

Automatically adjusts agent voting weights based on historical accuracy.
Agents with higher prediction accuracy receive higher weights.

Phase 3.2 of the architecture evolution roadmap.

Weight Range: 0.5 - 2.0 (default: 1.0)
Learning Rate: 0.1 per trade outcome
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json

import redis.asyncio as redis
import logging

try:
    import structlog
except Exception:  # Optional in some local/dev test setups
    structlog = None

from .trading_config import get_weight_config, get_infra_config, WeightLearningConfig as ConfigWeightLearning
from app.core.auth import get_current_user_id

logger = structlog.get_logger(__name__) if structlog is not None else logging.getLogger(__name__)


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent."""
    agent_name: str
    current_weight: float = 1.0
    total_predictions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    last_updated: Optional[datetime] = None

    # Recent performance (last 20 trades)
    recent_correct: int = 0
    recent_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert performance metrics to dictionary format.

        Returns:
            Dict containing:
                - agent_name: Agent identifier
                - current_weight: Current voting weight (0.5-2.0)
                - total_predictions: Total number of predictions made
                - correct_predictions: Number of correct predictions
                - accuracy: Overall accuracy percentage
                - recent_accuracy: Accuracy over last 20 trades
                - last_updated: ISO timestamp of last update
        """
        return {
            "agent_name": self.agent_name,
            "current_weight": round(self.current_weight, 3),
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "accuracy": round(self.accuracy, 2),
            "recent_accuracy": round(self.recent_correct / max(1, self.recent_total) * 100, 1),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


# Alias for backward compatibility
WeightLearningConfig = ConfigWeightLearning


class AgentWeightLearner:
    """
    Learns and adjusts agent weights based on prediction accuracy.

    After each trade outcome, the system:
    1. Compares agent predictions to actual result
    2. Updates accuracy metrics
    3. Adjusts weights using exponential smoothing

    Now uses centralized configuration from trading_config.py.
    """

    REDIS_KEY_PREFIX_BASE = "agent_weights"
    REDIS_KEY_PERFORMANCE_BASE = "agent_performance"
    REDIS_KEY_HISTORY_BASE = "agent_history"

    def __init__(
        self,
        config: Optional[WeightLearningConfig] = None,
        redis_client: Optional[redis.Redis] = None,
        user_id: Optional[str] = None,
    ):
        # Use centralized config if not provided
        self.config = config or get_weight_config()
        self.user_id = get_current_user_id(user_id)
        self.redis = redis_client
        self._performance_cache: Dict[str, AgentPerformance] = {}

    @property
    def redis_key_prefix(self) -> str:
        return f"{self.REDIS_KEY_PREFIX_BASE}:{self.user_id}:"

    @property
    def redis_key_performance(self) -> str:
        return f"{self.REDIS_KEY_PERFORMANCE_BASE}:{self.user_id}:"

    @property
    def redis_key_history(self) -> str:
        return f"{self.REDIS_KEY_HISTORY_BASE}:{self.user_id}:"

    async def _ensure_redis(self) -> Optional[redis.Redis]:
        """Ensure Redis connection exists."""
        if self.redis is None:
            # Use centralized config for Redis URL
            redis_url = get_infra_config().redis_url
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                await self.redis.ping()
            except Exception as e:
                logger.warning("weight_learner_redis_connect_failed", error=str(e))
                return None
        return self.redis
    
    async def get_agent_weight(self, agent_name: str) -> float:
        """Get current weight for an agent."""
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.redis_key_prefix}{agent_name}"
                weight = await redis_client.get(key)
                if weight:
                    return float(weight)
        except Exception as e:
            logger.error("get_agent_weight_failed", agent=agent_name, error=str(e))
        
        return self.config.default_weight
    
    async def get_all_weights(self) -> Dict[str, float]:
        """Get weights for all agents."""
        agents = [
            "TechnicalAnalyst",
            "FundamentalAnalyst",
            "SentimentAnalyst",
            "OnchainAnalyst",
            "ContrarianAnalyst",
            "RiskManager",
        ]
        
        weights = {}
        for agent in agents:
            weights[agent] = await self.get_agent_weight(agent)
        
        return weights
    
    async def get_agent_performance(self, agent_name: str) -> AgentPerformance:
        """Get performance metrics for an agent."""
        # Check cache first
        if agent_name in self._performance_cache:
            return self._performance_cache[agent_name]
        
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.redis_key_performance}{agent_name}"
                data = await redis_client.get(key)
                if data:
                    perf_dict = json.loads(data)
                    performance = AgentPerformance(
                        agent_name=agent_name,
                        current_weight=perf_dict.get("current_weight", 1.0),
                        total_predictions=perf_dict.get("total_predictions", 0),
                        correct_predictions=perf_dict.get("correct_predictions", 0),
                        accuracy=perf_dict.get("accuracy", 0.0),
                        recent_correct=perf_dict.get("recent_correct", 0),
                        recent_total=perf_dict.get("recent_total", 0),
                        last_updated=datetime.fromisoformat(perf_dict["last_updated"]) 
                            if perf_dict.get("last_updated") else None,
                    )
                    self._performance_cache[agent_name] = performance
                    return performance
        except Exception as e:
            logger.error("get_agent_performance_failed", agent=agent_name, error=str(e))
        
        # Return default
        return AgentPerformance(agent_name=agent_name)
    
    async def record_trade_outcome(
        self,
        agent_predictions: Dict[str, str],  # agent_name -> prediction (long/short/hold)
        actual_outcome: str,  # "profitable" | "loss" | "neutral"
        trade_direction: str,  # The actual direction taken
    ) -> Dict[str, float]:
        """
        Record trade outcome and update agent weights.
        
        Args:
            agent_predictions: Each agent's vote/prediction
            actual_outcome: Whether the trade was profitable
            trade_direction: The direction that was actually traded
            
        Returns:
            Updated weights for all agents
        """
        updated_weights = {}
        
        for agent_name, prediction in agent_predictions.items():
            # Determine if prediction was correct
            prediction_correct = self._evaluate_prediction(
                prediction=prediction,
                trade_direction=trade_direction,
                outcome=actual_outcome
            )
            
            # Get current performance
            perf = await self.get_agent_performance(agent_name)
            
            # Update metrics
            perf.total_predictions += 1
            perf.recent_total = min(perf.recent_total + 1, self.config.recent_window)
            
            if prediction_correct:
                perf.correct_predictions += 1
                perf.recent_correct = min(perf.recent_correct + 1, self.config.recent_window)
            
            # Calculate accuracy
            perf.accuracy = (perf.correct_predictions / perf.total_predictions) * 100
            
            # Adjust weight if enough data
            if perf.total_predictions >= self.config.min_trades_for_adjustment:
                perf.current_weight = self._calculate_new_weight(perf)
            
            perf.last_updated = datetime.now()
            
            # Persist
            await self._save_performance(perf)
            
            updated_weights[agent_name] = perf.current_weight
            
            logger.info(
                "agent_weight_updated",
                agent=agent_name,
                prediction_correct=prediction_correct,
                new_weight=perf.current_weight,
                accuracy=perf.accuracy
            )
        
        return updated_weights
    
    def _evaluate_prediction(
        self,
        prediction: str,
        trade_direction: str,
        outcome: str
    ) -> bool:
        """
        Evaluate if an agent's prediction was correct.
        
        Rules:
        - If agent predicted same as trade direction and trade was profitable → correct
        - If agent predicted opposite and trade was loss → correct (they were right to warn)
        - If agent predicted hold and outcome was neutral → correct
        """
        pred_lower = prediction.lower()
        dir_lower = trade_direction.lower()
        
        # Agent agreed with trade direction
        if pred_lower in ["long", "open_long"] and dir_lower in ["long", "open_long"]:
            return outcome == "profitable"
        if pred_lower in ["short", "open_short"] and dir_lower in ["short", "open_short"]:
            return outcome == "profitable"
        
        # Agent disagreed (warned against trade)
        if pred_lower in ["short", "open_short"] and dir_lower in ["long", "open_long"]:
            return outcome == "loss"  # They were right to warn
        if pred_lower in ["long", "open_long"] and dir_lower in ["short", "open_short"]:
            return outcome == "loss"
        
        # Agent said hold
        if pred_lower in ["hold", "neutral"]:
            return outcome in ["neutral", "loss"]  # Conservative was correct if not profit
        
        return False
    
    def _calculate_new_weight(self, perf: AgentPerformance) -> float:
        """Calculate new weight based on performance."""
        # Use recent accuracy for more responsive adjustment
        recent_accuracy = perf.recent_correct / max(1, perf.recent_total)
        overall_accuracy = perf.accuracy / 100
        
        # Blend recent and overall (70% recent, 30% overall)
        blended_accuracy = 0.7 * recent_accuracy + 0.3 * overall_accuracy
        
        # Map accuracy to weight
        # 50% accuracy → weight 1.0 (neutral)
        # 70% accuracy → weight 1.4
        # 80% accuracy → weight 1.6
        # 30% accuracy → weight 0.6
        weight_adjustment = (blended_accuracy - 0.5) * 2  # -1 to +1
        
        new_weight = self.config.default_weight + weight_adjustment
        
        # Smooth transition using learning rate
        current = perf.current_weight
        new_weight = current + self.config.learning_rate * (new_weight - current)
        
        # Clamp to bounds
        return max(self.config.min_weight, min(self.config.max_weight, new_weight))
    
    async def _save_performance(self, perf: AgentPerformance) -> None:
        """Save performance to Redis."""
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                # Save performance
                perf_key = f"{self.redis_key_performance}{perf.agent_name}"
                await redis_client.set(perf_key, json.dumps({
                    "current_weight": perf.current_weight,
                    "total_predictions": perf.total_predictions,
                    "correct_predictions": perf.correct_predictions,
                    "accuracy": perf.accuracy,
                    "recent_correct": perf.recent_correct,
                    "recent_total": perf.recent_total,
                    "last_updated": perf.last_updated.isoformat() if perf.last_updated else None,
                }))
                
                # Save weight for quick access
                weight_key = f"{self.redis_key_prefix}{perf.agent_name}"
                await redis_client.set(weight_key, str(perf.current_weight))
                
                # Update cache
                self._performance_cache[perf.agent_name] = perf
                
        except Exception as e:
            logger.error("save_performance_failed", agent=perf.agent_name, error=str(e))
    
    async def reset_agent_weight(self, agent_name: str) -> float:
        """Reset an agent's weight to default."""
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                weight_key = f"{self.redis_key_prefix}{agent_name}"
                await redis_client.set(weight_key, str(self.config.default_weight))
                
                # Also reset performance (optional, keep history)
                perf = await self.get_agent_performance(agent_name)
                perf.current_weight = self.config.default_weight
                await self._save_performance(perf)
                
            logger.info("agent_weight_reset", agent=agent_name)
            return self.config.default_weight
        except Exception as e:
            logger.error("reset_agent_weight_failed", agent=agent_name, error=str(e))
            return self.config.default_weight
    
    async def get_all_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all agents."""
        agents = [
            "TechnicalAnalyst",
            "FundamentalAnalyst", 
            "SentimentAnalyst",
            "OnchainAnalyst",
            "ContrarianAnalyst",
            "RiskManager",
        ]
        
        result = {}
        for agent in agents:
            perf = await self.get_agent_performance(agent)
            result[agent] = perf.to_dict()
        
        return result


# Singleton instances scoped by user
_weight_learners: Dict[str, AgentWeightLearner] = {}


def get_weight_learner(user_id: Optional[str] = None) -> AgentWeightLearner:
    """Get AgentWeightLearner instance scoped by user."""
    scope = get_current_user_id(user_id)
    learner = _weight_learners.get(scope)
    if learner is None:
        learner = AgentWeightLearner(user_id=scope)
        _weight_learners[scope] = learner
    return learner


async def get_learned_weights(user_id: Optional[str] = None) -> Dict[str, float]:
    """Convenience function to get all agent weights."""
    learner = get_weight_learner(user_id)
    return await learner.get_all_weights()
