"""
Rate-Limited Parallel Executor

Provides controlled parallel execution of trading agents with:
- Semaphore-based concurrency control
- Configurable batch delays
- Per-agent timeout protection
- Fallback vote generation on failure

Usage:
    executor = RateLimitedExecutor(config)
    votes = await executor.execute_agents_parallel(agents, prompt, context)
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable, Awaitable
from datetime import datetime

from app.core.observability.logging import get_logger
from app.core.observability.metrics import agent_latency
from .batch_config import AGENT_BATCHES, get_batch_for_agent

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate-limited execution."""
    
    # Concurrency control
    max_concurrent_agents: int = 2
    
    # Timing - increased timeout because each agent makes 5-6 tool calls
    batch_delay_seconds: float = 0.5
    agent_timeout_seconds: float = 120.0  # Increased from 90s for full agent execution
    
    # API-specific limits
    tavily_requests_per_second: int = 3
    llm_requests_per_second: int = 5
    
    # Retry settings
    max_retries: int = 1
    retry_delay_seconds: float = 1.0


# Default configuration
DEFAULT_CONFIG = RateLimitConfig()


@dataclass
class AgentResult:
    """Result from a single agent execution."""
    agent_id: str
    agent_name: str
    success: bool
    vote: Optional[Any] = None  # AgentVote type
    error: Optional[str] = None
    duration_ms: float = 0.0
    is_fallback: bool = False


class RateLimitedExecutor:
    """
    Executes agents in parallel with rate limiting.
    
    Features:
    - Batch-based parallel execution
    - Semaphore for concurrency control
    - Timeout protection per agent
    - Automatic fallback vote on failure
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_agents)
        self._execution_times: Dict[str, List[float]] = {}
    
    async def execute_batch(
        self,
        agents: List[Any],  # List of Agent objects
        prompt: str,
        run_agent_func: Callable[..., Awaitable[str]],
        parse_vote_func: Callable[..., Any],
    ) -> List[AgentResult]:
        """
        Execute a batch of agents in parallel.
        
        Args:
            agents: List of Agent objects to execute
            prompt: The prompt to send to each agent
            run_agent_func: Function to run an agent (async)
            parse_vote_func: Function to parse agent response into vote
            
        Returns:
            List of AgentResult for each agent
        """
        if not agents:
            return []
        
        logger.info("batch_execution_started",
            agent_count=len(agents),
            agent_ids=[a.id if hasattr(a, 'id') else str(a) for a in agents]
        )
        
        # Create tasks for all agents in batch
        tasks = [
            self._execute_single_agent(agent, prompt, run_agent_func, parse_vote_func)
            for agent in agents
        ]
        
        # Execute all with gather (respects semaphore inside)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                agent_id = agent.id if hasattr(agent, 'id') else str(agent)
                agent_name = agent.name if hasattr(agent, 'name') else agent_id
                logger.error("agent_execution_exception",
                    agent_id=agent_id,
                    error=str(result)
                )
                processed_results.append(AgentResult(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    success=False,
                    error=str(result),
                    is_fallback=True
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_single_agent(
        self,
        agent: Any,
        prompt: str,
        run_agent_func: Callable[..., Awaitable[str]],
        parse_vote_func: Callable[..., Any],
    ) -> AgentResult:
        """Execute a single agent with semaphore and timeout protection."""
        agent_id = agent.id if hasattr(agent, 'id') else str(agent)
        agent_name = agent.name if hasattr(agent, 'name') else agent_id
        
        start_time = time.time()
        
        async with self._semaphore:
            logger.info("agent_execution_started",
                agent_id=agent_id,
                agent_name=agent_name
            )
            
            try:
                # Execute with timeout
                response = await asyncio.wait_for(
                    run_agent_func(agent, prompt),
                    timeout=self.config.agent_timeout_seconds
                )
                
                # Parse the vote
                vote = parse_vote_func(agent_id, agent_name, response)
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Record metrics
                agent_latency.labels(agent_name=agent_name).observe(duration_ms / 1000)
                
                if vote:
                    logger.info("agent_execution_completed",
                        agent_id=agent_id,
                        agent_name=agent_name,
                        duration_ms=duration_ms,
                        direction=vote.direction if hasattr(vote, 'direction') else 'unknown'
                    )
                    return AgentResult(
                        agent_id=agent_id,
                        agent_name=agent_name,
                        success=True,
                        vote=vote,
                        duration_ms=duration_ms
                    )
                else:
                    logger.warning("agent_vote_parse_failed",
                        agent_id=agent_id,
                        agent_name=agent_name,
                        response_length=len(response) if response else 0
                    )
                    return AgentResult(
                        agent_id=agent_id,
                        agent_name=agent_name,
                        success=False,
                        error="Failed to parse vote",
                        duration_ms=duration_ms,
                        is_fallback=True
                    )
                    
            except asyncio.TimeoutError:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning("agent_execution_timeout",
                    agent_id=agent_id,
                    agent_name=agent_name,
                    timeout_seconds=self.config.agent_timeout_seconds
                )
                return AgentResult(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    success=False,
                    error=f"Timeout after {self.config.agent_timeout_seconds}s",
                    duration_ms=duration_ms,
                    is_fallback=True
                )
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error("agent_execution_failed",
                    agent_id=agent_id,
                    agent_name=agent_name,
                    error=str(e)
                )
                return AgentResult(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms,
                    is_fallback=True
                )
    
    async def execute_all_batches(
        self,
        get_agents_func: Callable[[str], Optional[Any]],
        prompt: str,
        run_agent_func: Callable[..., Awaitable[str]],
        parse_vote_func: Callable[..., Any],
    ) -> List[AgentResult]:
        """
        Execute all agent batches sequentially, agents within batch in parallel.
        
        Args:
            get_agents_func: Function to get agent by ID
            prompt: Prompt for all agents
            run_agent_func: Function to run an agent
            parse_vote_func: Function to parse vote from response
            
        Returns:
            List of all AgentResults
        """
        all_results = []
        total_start = time.time()
        
        for batch_idx, batch_agent_ids in enumerate(AGENT_BATCHES):
            logger.info("batch_started",
                batch_index=batch_idx,
                batch_size=len(batch_agent_ids),
                agent_ids=batch_agent_ids
            )
            
            # Get agent objects
            agents = []
            for agent_id in batch_agent_ids:
                agent = get_agents_func(agent_id)
                if agent:
                    agents.append(agent)
                else:
                    logger.warning("agent_not_found", agent_id=agent_id)
            
            if agents:
                # Execute batch
                batch_results = await self.execute_batch(
                    agents, prompt, run_agent_func, parse_vote_func
                )
                all_results.extend(batch_results)
            
            # Delay between batches (except after last batch)
            if batch_idx < len(AGENT_BATCHES) - 1:
                await asyncio.sleep(self.config.batch_delay_seconds)
        
        total_duration_ms = (time.time() - total_start) * 1000
        successful = sum(1 for r in all_results if r.success)
        
        logger.info("all_batches_completed",
            total_agents=len(all_results),
            successful=successful,
            failed=len(all_results) - successful,
            total_duration_ms=total_duration_ms
        )
        
        return all_results


# Singleton instance
_rate_limiter: Optional[RateLimitedExecutor] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimitedExecutor:
    """Get or create the singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimitedExecutor(config)
    return _rate_limiter
