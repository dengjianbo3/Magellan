"""
MeetingRunner

Main orchestrator for trading meeting execution.
Coordinates phase execution and manages meeting state.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Type

from .config import MeetingConfig
from .phases.base import PhaseExecutor, PhaseContext, PhaseResult
from .phases.analysis import MarketAnalysisPhase
from .phases.signal import SignalGenerationPhase
from .phases.risk import RiskAssessmentPhase
from .phases.consensus import ConsensusPhase
from ..domain.position import PositionContext
from ..domain.signal import TradingSignal
from ..domain.vote import VoteSummary

logger = logging.getLogger(__name__)


class MeetingRunner:
    """
    Orchestrates the trading meeting process.
    
    Runs through phases sequentially:
    1. Market Analysis - Agents gather data
    2. Signal Generation - Agents provide votes
    3. Risk Assessment - Evaluate risks
    4. Consensus Building - Leader summarizes
    5. Execution - TradeExecutor acts (handled externally)
    """
    
    # Default phase sequence
    DEFAULT_PHASES: List[Type[PhaseExecutor]] = [
        MarketAnalysisPhase,
        SignalGenerationPhase,
        RiskAssessmentPhase,
        ConsensusPhase,
    ]
    
    def __init__(
        self,
        agents: Dict[str, Any],
        llm_gateway: Any = None,
        config: Optional[MeetingConfig] = None,
        phases: Optional[List[Type[PhaseExecutor]]] = None,
        on_message: Optional[Callable] = None,
        on_signal: Optional[Callable] = None
    ):
        """
        Initialize meeting runner.
        
        Args:
            agents: Dict of agent_id -> agent instance
            llm_gateway: LLM gateway for model calls
            config: Meeting configuration
            phases: Custom phase list (optional)
            on_message: Callback for message events
            on_signal: Callback for signal generation
        """
        self.agents = agents
        self.llm = llm_gateway
        self.config = config or MeetingConfig()
        self.phase_classes = phases or self.DEFAULT_PHASES
        self.on_message = on_message
        self.on_signal = on_signal
        
        # Meeting state
        self._meeting_id: str = ""
        self._context: Optional[PhaseContext] = None
        self._results: List[PhaseResult] = []
        self._final_signal: Optional[TradingSignal] = None
        
        self.logger = logging.getLogger(f"{__name__}.MeetingRunner")
    
    @property
    def meeting_id(self) -> str:
        return self._meeting_id
    
    @property
    def final_signal(self) -> Optional[TradingSignal]:
        return self._final_signal
    
    @property
    def context(self) -> Optional[PhaseContext]:
        return self._context
    
    @property
    def phase_results(self) -> List[PhaseResult]:
        return self._results.copy()
    
    async def run(
        self,
        position_context: Optional[PositionContext] = None,
        trigger_reason: str = "scheduled"
    ) -> Optional[TradingSignal]:
        """
        Run the complete meeting.
        
        Args:
            position_context: Current position state
            trigger_reason: Why meeting was triggered
            
        Returns:
            TradingSignal with consensus decision
        """
        start_time = datetime.now()
        self._meeting_id = f"meeting_{uuid.uuid4().hex[:8]}"
        self._results = []
        self._final_signal = None
        
        self.logger.info(f"Starting meeting {self._meeting_id} (reason: {trigger_reason})")
        
        # Initialize context
        self._context = PhaseContext(
            config=self.config,
            position_context=position_context or PositionContext(),
            meeting_id=self._meeting_id,
            trigger_reason=trigger_reason
        )
        
        # Create phase executors
        phases = self._create_phases()
        
        # Execute phases sequentially
        for phase in phases:
            try:
                result = await phase.execute(self._context)
                self._results.append(result)
                
                if result.is_error:
                    self.logger.warning(
                        f"Phase {result.phase_name} had issues: {result.error}"
                    )
                    # Continue anyway - phases are designed to be fault-tolerant
                    
            except Exception as e:
                self.logger.error(f"Phase {phase.phase_name} failed: {e}")
                self._results.append(PhaseResult(
                    phase_name=phase.phase_name,
                    success=False,
                    error=str(e)
                ))
        
        # Build final signal from consensus
        self._final_signal = self._build_signal()
        
        # Trigger signal callback
        if self._final_signal and self.on_signal:
            try:
                self.on_signal(self._final_signal)
            except Exception as e:
                self.logger.warning(f"Signal callback error: {e}")
        
        # Log summary
        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(
            f"Meeting {self._meeting_id} completed in {duration:.1f}s - "
            f"Signal: {self._final_signal.direction.value if self._final_signal else 'None'}"
        )
        
        return self._final_signal
    
    def _create_phases(self) -> List[PhaseExecutor]:
        """Create phase executor instances."""
        return [
            phase_class(
                agents=self.agents,
                llm_gateway=self.llm,
                config=self.config,
                on_message=self.on_message
            )
            for phase_class in self.phase_classes
        ]
    
    def _build_signal(self) -> TradingSignal:
        """Build trading signal from meeting results."""
        if not self._context:
            return TradingSignal.hold_signal("No context available")
        
        votes = self._context.votes
        if not votes:
            return TradingSignal.hold_signal("No votes recorded")
        
        # Get current price
        entry_price = self._context.position_context.current_price
        if entry_price <= 0:
            # Try to get from config or use placeholder
            entry_price = 0.0
        
        # Build from vote summary
        summary = VoteSummary(votes)
        
        signal = TradingSignal.from_vote_summary(
            summary=summary,
            entry_price=entry_price,
            symbol=self.config.symbol,
            leader_summary=self._context.leader_summary or "",
            meeting_id=self._meeting_id,
            trigger_reason=self._context.trigger_reason
        )
        
        return signal
    
    def get_meeting_summary(self) -> Dict[str, Any]:
        """Get summary of meeting execution."""
        return {
            "meeting_id": self._meeting_id,
            "phases_completed": len(self._results),
            "phases_succeeded": sum(1 for r in self._results if r.success),
            "total_duration": sum(r.duration_seconds for r in self._results),
            "signal": self._final_signal.to_dict() if self._final_signal else None,
            "phase_results": [
                {
                    "name": r.phase_name,
                    "success": r.success,
                    "duration": r.duration_seconds,
                    "error": r.error
                }
                for r in self._results
            ]
        }
