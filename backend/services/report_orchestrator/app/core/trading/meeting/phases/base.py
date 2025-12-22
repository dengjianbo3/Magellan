"""
PhaseExecutor Base Class

Abstract base class for all meeting phase implementations.
Provides common functionality for phase execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
import logging

from ..config import MeetingConfig
from ...domain.position import PositionContext
from ...domain.vote import AgentVote

logger = logging.getLogger(__name__)


@dataclass
class PhaseContext:
    """
    Context passed to each phase during execution.
    
    Contains all shared state needed across phases.
    """
    # Configuration
    config: MeetingConfig
    
    # Current position state
    position_context: PositionContext
    
    # Meeting state
    meeting_id: str = ""
    trigger_reason: str = "scheduled"
    
    # Accumulated data from previous phases
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    votes: List[AgentVote] = field(default_factory=list)
    risk_assessment: Optional[str] = None
    leader_summary: Optional[str] = None
    
    # Message history
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    
    def add_message(
        self,
        agent_id: str,
        agent_name: str,
        content: str,
        message_type: str = "message"
    ):
        """Add a message to the conversation history."""
        self.messages.append({
            "agent_id": agent_id,
            "agent_name": agent_name,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_analysis_summary(self) -> str:
        """Get formatted summary of analysis results."""
        if not self.analysis_results:
            return "No analysis results yet."
        
        lines = ["## Analysis Summary\n"]
        for agent_id, result in self.analysis_results.items():
            lines.append(f"### {agent_id}")
            if isinstance(result, dict):
                lines.append(result.get("summary", str(result)))
            else:
                lines.append(str(result)[:500])  # Truncate long results
            lines.append("")
        
        return "\n".join(lines)
    
    def get_vote_summary_text(self) -> str:
        """Get formatted summary of votes."""
        if not self.votes:
            return "No votes recorded yet."
        
        lines = ["## Expert Votes\n"]
        for vote in self.votes:
            lines.append(
                f"- **{vote.agent_name}**: {vote.direction.value} "
                f"(confidence: {vote.confidence}%, leverage: {vote.leverage}x)"
            )
        
        return "\n".join(lines)


@dataclass
class PhaseResult:
    """
    Result from a phase execution.
    """
    phase_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0.0
    
    @property
    def is_error(self) -> bool:
        return not self.success or self.error is not None


class PhaseExecutor(ABC):
    """
    Abstract base class for meeting phase executors.
    
    Each phase (Analysis, Signal, Risk, Consensus, Execution) should
    inherit from this class and implement the execute method.
    """
    
    # Phase identification
    phase_name: str = "base"
    phase_number: int = 0
    
    def __init__(
        self,
        agents: Dict[str, Any],
        llm_gateway: Any,  # ILLMGateway
        config: MeetingConfig,
        on_message: Optional[Callable] = None
    ):
        """
        Initialize phase executor.
        
        Args:
            agents: Dict of agent_id -> agent instance
            llm_gateway: LLM gateway for model calls
            config: Meeting configuration
            on_message: Callback for message events
        """
        self.agents = agents
        self.llm = llm_gateway
        self.config = config
        self.on_message = on_message
        self.logger = logging.getLogger(f"{__name__}.{self.phase_name}")
    
    @abstractmethod
    async def execute(self, context: PhaseContext) -> PhaseResult:
        """
        Execute this phase.
        
        Args:
            context: Phase context with shared state
            
        Returns:
            PhaseResult with execution outcome
        """
        pass
    
    def _get_agent(self, agent_id: str) -> Optional[Any]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def _add_message(
        self,
        context: PhaseContext,
        agent_id: str,
        agent_name: str,
        content: str,
        message_type: str = "message"
    ):
        """Add message to context and trigger callback."""
        context.add_message(agent_id, agent_name, content, message_type)
        
        if self.on_message:
            try:
                self.on_message({
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "content": content,
                    "message_type": message_type,
                    "phase": self.phase_name
                })
            except Exception as e:
                self.logger.warning(f"Message callback error: {e}")
    
    def _log_phase_start(self, context: PhaseContext):
        """Log phase start."""
        self.logger.info(
            f"Starting {self.phase_name} phase for meeting {context.meeting_id}"
        )
        self._add_message(
            context,
            agent_id="system",
            agent_name="System",
            content=f"## Phase {self.phase_number}: {self.phase_name}",
            message_type="phase"
        )
    
    def _log_phase_end(self, result: PhaseResult):
        """Log phase completion."""
        status = "completed" if result.success else "failed"
        self.logger.info(
            f"{self.phase_name} phase {status} in {result.duration_seconds:.2f}s"
        )
    
    async def _run_agent_with_timeout(
        self,
        agent: Any,
        prompt: str,
        timeout_seconds: Optional[int] = None
    ) -> Optional[str]:
        """
        Run agent with timeout.
        
        Args:
            agent: Agent instance
            prompt: Prompt to send
            timeout_seconds: Timeout (defaults to config)
            
        Returns:
            Agent response or None on timeout
        """
        import asyncio
        
        timeout = timeout_seconds or self.config.agent_timeout
        
        try:
            # Check if agent has async run method
            if hasattr(agent, 'run') and asyncio.iscoroutinefunction(agent.run):
                result = await asyncio.wait_for(
                    agent.run(prompt),
                    timeout=timeout
                )
            elif hasattr(agent, 'run'):
                # Wrap sync method
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, agent.run, prompt),
                    timeout=timeout
                )
            else:
                self.logger.warning(f"Agent {agent} has no run method")
                return None
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Agent timeout after {timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"Agent execution error: {e}")
            return None
