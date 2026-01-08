"""
Agent Batch Configuration

Defines which agents run together in parallel batches,
organized by their external API dependencies to avoid rate limiting.

Batch Strategy:
- Batch 1: Fast agents (no external search, only cached market data)
- Batch 2: Tavily-dependent agents (news search, macro data)
- Batch 3: Mixed API agents (on-chain, quantitative)
"""

from typing import List, Dict

# Agent Batches - organized by API dependency
# Agents in the same batch run in parallel
# Batches run sequentially with delays between them
AGENT_BATCHES: List[List[str]] = [
    # Batch 1: Technical Analysis (uses cached OKX data only)
    # Fastest - no external API calls needed
    ["TechnicalAnalyst"],
    
    # Batch 2: News & Macro (Tavily search - rate limited)
    # These agents use web search heavily
    ["MacroEconomist", "SentimentAnalyst"],
    
    # Batch 3: On-chain & Quant (mixed APIs)
    # On-chain uses blockchain APIs, Quant uses various data sources
    ["OnchainAnalyst", "QuantStrategist"],
]

# Agent to batch mapping for quick lookup
_AGENT_TO_BATCH: Dict[str, int] = {}
for batch_idx, batch in enumerate(AGENT_BATCHES):
    for agent_id in batch:
        _AGENT_TO_BATCH[agent_id] = batch_idx


def get_agent_batch(batch_index: int) -> List[str]:
    """
    Get agents in a specific batch.
    
    Args:
        batch_index: 0-indexed batch number
        
    Returns:
        List of agent IDs in that batch
    """
    if 0 <= batch_index < len(AGENT_BATCHES):
        return AGENT_BATCHES[batch_index]
    return []


def get_batch_for_agent(agent_id: str) -> int:
    """
    Get the batch index for an agent.
    
    Args:
        agent_id: Agent identifier (e.g., "TechnicalAnalyst")
        
    Returns:
        Batch index (0-indexed), or -1 if not found
    """
    return _AGENT_TO_BATCH.get(agent_id, -1)


def get_all_voting_agents() -> List[str]:
    """Get flat list of all voting agents in batch order."""
    agents = []
    for batch in AGENT_BATCHES:
        agents.extend(batch)
    return agents


# API-specific rate limit hints
API_RATE_LIMITS = {
    "tavily": {
        "requests_per_second": 3,  # Conservative for free tier
        "agents": ["MacroEconomist", "SentimentAnalyst", "FundamentalAnalyst"],
    },
    "gemini": {
        "requests_per_minute": 15,  # Free tier limit
        "agents": ["all"],  # All agents use LLM
    },
    "deepseek": {
        "requests_per_minute": 1000,  # Generous limit
        "agents": ["all"],
    },
    "glassnode": {
        "requests_per_minute": 10,
        "agents": ["OnchainAnalyst"],
    },
}
