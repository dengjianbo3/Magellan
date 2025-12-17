"""
Consensus Phase

Phase 4: Leader summarizes discussion and builds consensus.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .base import PhaseExecutor, PhaseContext, PhaseResult
from ...domain.vote import VoteSummary

logger = logging.getLogger(__name__)


class ConsensusPhase(PhaseExecutor):
    """
    Phase 4: Consensus Building
    
    The Roundtable Leader summarizes all expert opinions
    and formulates a unified trading strategy.
    """
    
    phase_name = "Consensus Building"
    phase_number = 4
    
    LEADER_ID = "Leader"
    
    async def execute(self, context: PhaseContext) -> PhaseResult:
        """Execute consensus building phase."""
        start_time = datetime.now()
        self._log_phase_start(context)
        
        agent = self._get_agent(self.LEADER_ID)
        if not agent:
            # Try alternative ID
            agent = self._get_agent("RoundtableLeader")
        
        if not agent:
            logger.error("Leader agent not found")
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                error="Leader agent not found",
                duration_seconds=0
            )
        
        try:
            prompt = self._build_leader_prompt(context)
            response = await self._run_agent_with_timeout(
                agent, 
                prompt,
                timeout_seconds=90  # Leader needs more time
            )
            
            if response:
                context.leader_summary = response
                
                self._add_message(
                    context,
                    agent_id=self.LEADER_ID,
                    agent_name="Roundtable Leader",
                    content=response,
                    message_type="leader_summary"
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                result = PhaseResult(
                    phase_name=self.phase_name,
                    success=True,
                    data={
                        "summary": response,
                        "vote_analysis": self._analyze_votes(context)
                    },
                    duration_seconds=duration
                )
            else:
                result = PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    error="Leader provided no response",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
                
        except Exception as e:
            logger.error(f"Consensus phase error: {e}")
            result = PhaseResult(
                phase_name=self.phase_name,
                success=False,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        self._log_phase_end(result)
        return result
    
    def _build_leader_prompt(self, context: PhaseContext) -> str:
        """Build leader summary prompt."""
        position = context.position_context
        vote_summary = VoteSummary(context.votes)
        
        # Format analysis results
        analysis_text = context.get_analysis_summary()
        
        # Format votes with details
        vote_details = "\n".join([
            f"- **{v.agent_name}**: {v.direction.value} "
            f"(Confidence: {v.confidence}%, Leverage: {v.leverage}x)\n"
            f"  Reasoning: {v.reasoning[:200]}..." if len(v.reasoning) > 200 else 
            f"- **{v.agent_name}**: {v.direction.value} "
            f"(Confidence: {v.confidence}%, Leverage: {v.leverage}x)\n"
            f"  Reasoning: {v.reasoning}"
            for v in context.votes
        ])
        
        # Risk assessment if available
        risk_text = ""
        if context.risk_assessment:
            risk_text = f"\n\n## Risk Assessment\n{context.risk_assessment[:500]}"
        
        # Decision guidance
        guidance = self._get_decision_guidance(position, vote_summary)
        
        return f"""You are the Roundtable Leader. Summarize the meeting discussion and provide strategic guidance.

## Current Position
{position.to_summary()}

## Expert Analysis Summary
{analysis_text}

## Expert Votes
{vote_details}

## Vote Statistics
- Long Votes: {vote_summary.long_count}
- Short Votes: {vote_summary.short_count}
- Hold Votes: {vote_summary.hold_count}
- Close Votes: {vote_summary.close_count}
- Average Confidence: {vote_summary.avg_confidence:.0f}%
- Consensus Direction: {vote_summary.consensus_direction.value}
- Consensus Strength: {vote_summary.consensus_strength:.0%}
{risk_text}

{guidance}

## Your Task

Provide a comprehensive meeting summary that:
1. Synthesizes all expert opinions
2. Highlights key agreements and disagreements
3. Identifies the main factors driving the consensus
4. Provides strategic recommendations
5. Notes any important caveats or risks

**Format your summary as:**

### Meeting Summary
[Synthesize expert opinions]

### Key Findings
[Main analysis points]

### Consensus View
[Direction and rationale]

### Recommended Action
[What the TradeExecutor should consider]

### Risk Factors
[Important risks to monitor]"""
    
    def _get_decision_guidance(self, position: PositionContext, summary: VoteSummary) -> str:
        """Generate decision guidance based on consensus."""
        consensus = summary.consensus_direction.value
        strength = summary.consensus_strength
        
        if strength < 0.5:
            return """## Decision Guidance
**Weak Consensus**: Experts are divided. Consider HOLD unless there are compelling reasons to act."""
        
        if not position.has_position:
            return f"""## Decision Guidance
**No Current Position**: Consensus points to {consensus.upper()}.
Consider whether the confidence level ({summary.avg_confidence:.0f}%) justifies opening a position."""
        
        current_dir = position.direction.upper()
        if consensus.upper() == current_dir or consensus.upper() == f"ADD_{current_dir}":
            return f"""## Decision Guidance
**Aligned with Position**: Consensus supports current {current_dir} position.
Consider adding to position if confidence is high enough."""
        
        return f"""## Decision Guidance
**Conflicting Signal**: Consensus ({consensus.upper()}) differs from current {current_dir} position.
Carefully evaluate whether to close, hold, or reverse."""
    
    def _analyze_votes(self, context: PhaseContext) -> Dict[str, Any]:
        """Analyze vote distribution."""
        vote_summary = VoteSummary(context.votes)
        
        return {
            "total_votes": len(context.votes),
            "long_count": vote_summary.long_count,
            "short_count": vote_summary.short_count,
            "hold_count": vote_summary.hold_count,
            "close_count": vote_summary.close_count,
            "consensus_direction": vote_summary.consensus_direction.value,
            "consensus_strength": vote_summary.consensus_strength,
            "avg_confidence": vote_summary.avg_confidence,
            "avg_leverage": vote_summary.avg_leverage,
            "is_unanimous": vote_summary.consensus_strength == 1.0
        }
