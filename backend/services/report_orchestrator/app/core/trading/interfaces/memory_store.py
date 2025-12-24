"""
IMemoryStore Interface

Abstract base class for agent memory storage implementations.
Enables Redis storage or in-memory storage for testing.
"""

from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentPrediction:
    """Stores an agent's prediction for later reflection."""
    agent_id: str
    trade_id: str
    direction: str
    confidence: int
    leverage: int
    reasoning: str
    market_price: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentReflection:
    """Agent's reflection on a completed trade."""
    agent_id: str
    trade_id: str
    prediction: AgentPrediction
    actual_pnl: float
    actual_pnl_percent: float
    was_correct: bool
    lessons: List[str]
    focus_area: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentMemory:
    """
    Complete memory state for an agent.
    
    Tracks historical performance, lessons learned, and predictions.
    """
    agent_id: str
    
    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    
    # Learning
    lessons_learned: List[str] = field(default_factory=list)
    current_focus: str = ""
    last_trade_summary: str = ""
    
    # Recent history
    recent_predictions: List[AgentPrediction] = field(default_factory=list)
    recent_reflections: List[AgentReflection] = field(default_factory=list)
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def to_prompt_context(self) -> str:
        """Format memory for prompt injection."""
        lines = [
            "══════════════════════════════════════════",
            "📊 YOUR HISTORICAL PERFORMANCE",
            "══════════════════════════════════════════",
            f"Total Trades: {self.total_trades}",
            f"Win Rate: {self.win_rate:.1f}% ({self.winning_trades}W / {self.losing_trades}L)",
            f"Total P&L: ${self.total_pnl:+.2f}",
        ]
        
        if self.lessons_learned:
            lines.append("")
            lines.append("📚 LESSONS LEARNED:")
            for i, lesson in enumerate(self.lessons_learned[-5:], 1):
                lines.append(f"{i}. {lesson}")
        
        if self.current_focus:
            lines.append("")
            lines.append(f"🎯 CURRENT FOCUS: {self.current_focus}")
        
        if self.last_trade_summary:
            lines.append("")
            lines.append(f"📝 LAST TRADE: {self.last_trade_summary}")
        
        lines.append("══════════════════════════════════════════")
        return "\n".join(lines)


class IMemoryStore(ABC):
    """
    Abstract memory store interface.
    
    Provides persistence for agent memories, enabling learning
    across trading sessions.
    """
    
    @abstractmethod
    async def get_memory(self, agent_id: str) -> AgentMemory:
        """
        Get memory for an agent.
        
        Args:
            agent_id: Unique agent identifier
            
        Returns:
            AgentMemory (creates new if not exists)
        """
        pass
    
    @abstractmethod
    async def save_memory(self, memory: AgentMemory) -> None:
        """
        Save agent memory.
        
        Args:
            memory: AgentMemory to persist
        """
        pass
    
    @abstractmethod
    async def save_prediction(self, prediction: AgentPrediction) -> None:
        """
        Save a prediction for later reflection.
        
        Args:
            prediction: AgentPrediction to store
        """
        pass
    
    @abstractmethod
    async def get_predictions_for_trade(self, trade_id: str) -> List[AgentPrediction]:
        """
        Get all predictions for a specific trade.
        
        Args:
            trade_id: Trade identifier
            
        Returns:
            List of predictions from all agents
        """
        pass
    
    @abstractmethod
    async def save_reflection(self, reflection: AgentReflection) -> None:
        """
        Save an agent's reflection.
        
        Args:
            reflection: AgentReflection to store
        """
        pass
    
    @abstractmethod
    async def update_performance(
        self,
        agent_id: str,
        pnl: float,
        was_win: bool
    ) -> None:
        """
        Update agent's performance metrics.
        
        Args:
            agent_id: Agent identifier
            pnl: Profit/loss from trade
            was_win: Whether the trade was profitable
        """
        pass
    
    @abstractmethod
    async def add_lesson(self, agent_id: str, lesson: str) -> None:
        """
        Add a lesson learned to agent's memory.
        
        Args:
            agent_id: Agent identifier
            lesson: Lesson to remember
        """
        pass
