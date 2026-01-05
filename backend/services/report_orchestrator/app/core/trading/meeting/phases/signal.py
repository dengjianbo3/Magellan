"""
Signal Generation Phase

Phase 2: Each analyst provides their trading vote.
"""

from datetime import datetime
from typing import List
import logging

from .base import PhaseExecutor, PhaseContext, PhaseResult
from ...domain.vote import AgentVote, VoteSummary
from ...parsers.vote_parser import VoteParser

logger = logging.getLogger(__name__)


class SignalGenerationPhase(PhaseExecutor):
    """
    Phase 2: Signal Generation
    
    Each analyst agent provides their trading recommendation
    in structured JSON format.
    """
    
    phase_name = "Signal Generation"
    phase_number = 2
    
    # Agents that vote in this phase
    VOTING_AGENTS = [
        "TechnicalAnalyst",
        "MacroEconomist",
        "SentimentAnalyst", 
        "QuantStrategist"
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vote_parser = VoteParser()
    
    async def execute(self, context: PhaseContext) -> PhaseResult:
        """Execute signal generation phase."""
        start_time = datetime.now()
        self._log_phase_start(context)
        
        votes: List[AgentVote] = []
        errors = []
        
        for agent_id in self.VOTING_AGENTS:
            agent = self._get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found, skipping")
                continue
            
            try:
                # Build vote prompt
                prompt = self._build_vote_prompt(agent_id, context)
                response = await self._run_agent_with_timeout(agent, prompt)
                
                if response:
                    # Parse vote from response
                    parse_result = self.vote_parser.parse(response)
                    
                    if parse_result.success and parse_result.vote:
                        agent_vote = AgentVote(
                            agent_id=agent_id,
                            agent_name=getattr(agent, 'name', agent_id),
                            vote=parse_result.vote,
                            raw_response=response,
                            parse_method=parse_result.method
                        )
                        votes.append(agent_vote)
                        
                        # Log the vote
                        self._add_message(
                            context,
                            agent_id=agent_id,
                            agent_name=agent_vote.agent_name,
                            content=f"Vote: {agent_vote.direction.value} "
                                   f"(confidence: {agent_vote.confidence}%)",
                            message_type="vote"
                        )
                    else:
                        errors.append(f"{agent_id}: Parse failed - {parse_result.error}")
                else:
                    errors.append(f"{agent_id}: No response")
                    
            except Exception as e:
                logger.error(f"Error getting vote from {agent_id}: {e}")
                errors.append(f"{agent_id}: {str(e)}")
        
        # Store votes in context
        context.votes = votes
        
        # Calculate summary
        summary = VoteSummary(votes)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = PhaseResult(
            phase_name=self.phase_name,
            success=len(votes) >= 2,  # Need at least 2 votes
            data={
                "vote_count": len(votes),
                "votes": [v.to_dict() for v in votes],
                "summary": {
                    "long_count": summary.long_count,
                    "short_count": summary.short_count,
                    "hold_count": summary.hold_count,
                    "avg_confidence": summary.avg_confidence,
                    "consensus_direction": summary.consensus_direction.value,
                    "consensus_strength": summary.consensus_strength
                },
                "errors": errors
            },
            error="; ".join(errors) if errors and len(votes) < 2 else None,
            duration_seconds=duration
        )
        
        self._log_phase_end(result)
        return result
    
    def _build_vote_prompt(self, agent_id: str, context: PhaseContext) -> str:
        """Build voting prompt for agent."""
        symbol = context.config.symbol
        position = context.position_context
        decision_options = self._get_decision_options(position)
        
        # Get agent's own analysis if available
        agent_analysis = ""
        if agent_id in context.analysis_results:
            analysis = context.analysis_results[agent_id]
            if isinstance(analysis, dict):
                agent_analysis = f"\n\nYour previous analysis:\n{analysis.get('summary', '')}"
        
        # Build the vote JSON template - IMPORTANT: Use placeholder to avoid bias
        # Get dynamic ranges from config
        max_leverage = context.config.max_leverage if hasattr(context.config, 'max_leverage') else 20
        min_sl = context.config.min_stop_loss_percent if hasattr(context.config, 'min_stop_loss_percent') else 0.5
        max_sl = context.config.max_stop_loss_percent if hasattr(context.config, 'max_stop_loss_percent') else 10.0
        
        vote_template = f'''{{
  "direction": "<your_vote>",
  "confidence": <0-100>,
  "leverage": <1-{max_leverage}>,
  "take_profit_percent": <1-20>,
  "stop_loss_percent": <{min_sl}-{max_sl}>,
  "reasoning": "<brief explanation>"
}}'''
        
        return f"""Based on your market analysis, provide your trading recommendation for {symbol}.

{position.to_summary()}
{agent_analysis}

{decision_options}

**Output your vote as JSON:**
```json
{vote_template}
```

**Direction Options** (choose ONE):
- "short" - Open/add short position (bearish)
- "long" - Open/add long position (bullish)  
- "hold" - Wait, no action
- "close" - Close current position

**IMPORTANT**:
- Base your vote ONLY on your analysis, not on others' opinions
- Be specific about confidence (0-100) based on signal strength
- Consider risk/reward in your leverage and TP/SL suggestions
- Provide clear reasoning for your vote"""
    
    def _get_decision_options(self, position: PositionContext) -> str:
        """Generate decision options based on position state."""
        if not position.has_position:
            return """**Available Actions**:
- SHORT: Open a short position (if bearish)
- LONG: Open a long position (if bullish)
- HOLD: Wait for better opportunity"""
        
        direction = position.direction.upper()
        opposite = "LONG" if direction == "SHORT" else "SHORT"
        
        return f"""**Current Position**: {direction}
**Available Actions**:
- {opposite}: Suggest closing current position and reversing
- CLOSE: Close current position and stay flat
- ADD_{direction}: Add to current {direction} position
- HOLD: Maintain current position"""
