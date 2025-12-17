"""
Risk Assessment Phase

Phase 3: Risk Assessor evaluates position risks.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .base import PhaseExecutor, PhaseContext, PhaseResult
from ...domain.vote import VoteSummary

logger = logging.getLogger(__name__)


class RiskAssessmentPhase(PhaseExecutor):
    """
    Phase 3: Risk Assessment
    
    The Risk Assessor analyzes current and proposed positions
    for risk factors.
    """
    
    phase_name = "Risk Assessment"
    phase_number = 3
    
    RISK_ASSESSOR_ID = "RiskAssessor"
    
    async def execute(self, context: PhaseContext) -> PhaseResult:
        """Execute risk assessment phase."""
        start_time = datetime.now()
        self._log_phase_start(context)
        
        agent = self._get_agent(self.RISK_ASSESSOR_ID)
        if not agent:
            logger.warning("RiskAssessor not found, skipping phase")
            return PhaseResult(
                phase_name=self.phase_name,
                success=True,  # Not critical
                data={"skipped": True, "reason": "Agent not found"},
                duration_seconds=0
            )
        
        try:
            prompt = self._build_risk_prompt(context)
            response = await self._run_agent_with_timeout(agent, prompt)
            
            if response:
                context.risk_assessment = response
                
                self._add_message(
                    context,
                    agent_id=self.RISK_ASSESSOR_ID,
                    agent_name="Risk Assessor",
                    content=response,
                    message_type="risk_assessment"
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                result = PhaseResult(
                    phase_name=self.phase_name,
                    success=True,
                    data={
                        "assessment": response,
                        "summary": self._extract_risk_summary(response)
                    },
                    duration_seconds=duration
                )
            else:
                result = PhaseResult(
                    phase_name=self.phase_name,
                    success=True,  # Not critical
                    data={"skipped": True, "reason": "No response"},
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
                
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            result = PhaseResult(
                phase_name=self.phase_name,
                success=True,  # Not critical
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        self._log_phase_end(result)
        return result
    
    def _build_risk_prompt(self, context: PhaseContext) -> str:
        """Build risk assessment prompt."""
        position = context.position_context
        vote_summary = VoteSummary(context.votes)
        
        # Format votes
        vote_text = "\n".join([
            f"- {v.agent_name}: {v.direction.value} (conf: {v.confidence}%)"
            for v in context.votes
        ])
        
        consensus = vote_summary.consensus_direction.value
        strength = vote_summary.consensus_strength
        
        return f"""Evaluate the risk profile for the current situation.

## Current Position
{position.to_summary()}

## Expert Votes
{vote_text}

## Consensus
- Direction: {consensus}
- Strength: {strength:.0%}
- Average Confidence: {vote_summary.avg_confidence:.0f}%
- Suggested Leverage: {vote_summary.avg_leverage:.1f}x

## Your Risk Assessment Task

Analyze:
1. **Position Risk**: If we have a position, what are the current risks?
   - Distance to liquidation
   - Unrealized P&L exposure
   - Time in position

2. **Market Risk**: What external risks exist?
   - Volatility conditions
   - News/event risk
   - Liquidity concerns

3. **Execution Risk**: If we act on consensus, what risks?
   - Is the suggested leverage appropriate?
   - Are TP/SL levels reasonable?
   - Should position size be adjusted?

4. **Overall Risk Assessment**:
   - LOW / MEDIUM / HIGH
   - Key risk factors
   - Risk mitigation suggestions

Provide a concise risk assessment focusing on actionable insights."""
    
    def _extract_risk_summary(self, response: str) -> Dict[str, Any]:
        """Extract structured risk summary from response."""
        # Simple extraction - look for risk level keywords
        response_lower = response.lower()
        
        if "high risk" in response_lower or "high" in response_lower[:200]:
            risk_level = "HIGH"
        elif "low risk" in response_lower or "low" in response_lower[:200]:
            risk_level = "LOW"
        else:
            risk_level = "MEDIUM"
        
        return {
            "risk_level": risk_level,
            "summary": response[:300] if len(response) > 300 else response
        }
