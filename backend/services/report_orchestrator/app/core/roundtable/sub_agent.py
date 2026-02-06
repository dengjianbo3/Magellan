"""
Sub-Agent Architecture

Implement specialized sub-agents for deep research tasks.
Based on 2025 Context Engineering: Context Quarantine pattern from Manus AI.

Key benefits:
1. Each sub-agent has isolated context window
2. Main agent only receives compressed results
3. Enables parallel deep research
4. Prevents context rot in coordinator
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SubAgentResult:
    """Result from a sub-agent execution"""
    agent_name: str
    task: str
    conclusion: str
    key_findings: List[str]
    confidence: int  # 0-10
    sources: List[str]
    tokens_used: int  # Estimated
    execution_time_ms: int
    success: bool
    error: Optional[str] = None
    
    def to_compact_dict(self) -> Dict[str, Any]:
        """Return compact representation for main agent context"""
        return {
            "agent": self.agent_name,
            "conclusion": self.conclusion[:300],
            "confidence": self.confidence,
            "findings": self.key_findings[:3],  # Top 3 only
            "success": self.success
        }


class SubAgent:
    """
    Sub-agent for isolated deep research tasks.
    
    Context Engineering benefits:
    - Isolated context window (~20K tokens)
    - Returns compressed results (~500 tokens)
    - Main agent stays focused
    
    Usage:
        sub_agent = SubAgent(
            name="DeepResearch",
            tools=tools,
            llm_service=llm_service
        )
        
        result = await sub_agent.execute(
            "Analyze BTC on-chain metrics for the past week"
        )
        
        # Use compact result in main context
        compact = result.to_compact_dict()
    """
    
    MAX_STEPS = 20
    MAX_CONTEXT_TOKENS = 20000
    
    def __init__(
        self, 
        name: str,
        tools: List[Any] = None,
        llm_service: Any = None,
        system_prompt: str = None
    ):
        """
        Args:
            name: Sub-agent identifier
            tools: List of Tool instances available to this sub-agent
            llm_service: LLM service for generating responses
            system_prompt: Custom system prompt (optional)
        """
        self.name = name
        self.tools = {t.name: t for t in (tools or [])}
        self.llm_service = llm_service
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        self._execution_count = 0
        self._total_tokens = 0
    
    def _default_system_prompt(self) -> str:
        from datetime import datetime
        current_time = datetime.now()
        
        return f"""## ⏰ CURRENT TIME
**Current Date/Time**: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)
**Today's Date**: {current_time.strftime('%B %d, %Y')}

You are {self.name}, a specialized research sub-agent.

Your task is to gather and analyze information thoroughly, then provide a concise summary.

⚠️ **TIME-SENSITIVE RESEARCH**: Always focus on the MOST RECENT information. 
When searching, specify time ranges like "last 24 hours", "today", or "this week".

PROCESS:
1. Break down the research task into steps
2. Use available tools to gather RECENT data (specify time ranges!)
3. Analyze findings critically
4. Synthesize into clear conclusions

OUTPUT FORMAT:
After completing research, output JSON:
{{
    "conclusion": "One paragraph summary of findings",
    "key_findings": ["Finding 1", "Finding 2", ...],
    "confidence": 0-10,
    "sources": ["Source 1", ...]
}}

Be thorough but efficient. Focus on actionable insights from CURRENT data."""

    async def execute(self, task: str, context: Dict[str, Any] = None) -> SubAgentResult:
        """
        Execute sub-agent research task.
        
        Args:
            task: Research task description
            context: Optional additional context
            
        Returns:
            SubAgentResult with findings
        """
        start_time = datetime.now()
        self._execution_count += 1
        
        logger.info(f"[SubAgent:{self.name}] Starting task: {task[:50]}...")
        
        # Build isolated context
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._build_task_prompt(task, context)}
        ]
        
        try:
            # Execute research loop (simplified for now)
            if self.llm_service:
                result = await self._execute_with_llm(messages, task)
            else:
                result = await self._execute_mock(task)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return SubAgentResult(
                agent_name=self.name,
                task=task[:100],
                conclusion=result.get("conclusion", "Research completed"),
                key_findings=result.get("key_findings", [])[:5],
                confidence=result.get("confidence", 5),
                sources=result.get("sources", [])[:5],
                tokens_used=result.get("tokens", 500),
                execution_time_ms=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"[SubAgent:{self.name}] Execution failed: {e}")
            return SubAgentResult(
                agent_name=self.name,
                task=task[:100],
                conclusion="",
                key_findings=[],
                confidence=0,
                sources=[],
                tokens_used=0,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                success=False,
                error=str(e)
            )
    
    def _build_task_prompt(self, task: str, context: Dict[str, Any] = None) -> str:
        """Build the task prompt with available tools"""
        tool_list = ", ".join(self.tools.keys()) if self.tools else "None"
        
        prompt = f"""# Research Task
{task}

# Available Tools
{tool_list}

# Instructions
1. Plan your research approach
2. Execute necessary tool calls
3. Synthesize findings
4. Output JSON summary"""
        
        if context:
            prompt += f"\n\n# Additional Context\n{json.dumps(context, indent=2)[:500]}"
        
        return prompt
    
    async def _execute_with_llm(self, messages: List[Dict], task: str) -> Dict[str, Any]:
        """Execute with actual LLM"""
        # Multi-step execution loop
        for step in range(self.MAX_STEPS):
            response = await self.llm_service.generate(
                messages=messages,
                temperature=0.3
            )
            
            # Check if response contains final JSON
            try:
                if "{" in response and "conclusion" in response:
                    start = response.find("{")
                    end = response.rfind("}") + 1
                    return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
            
            # Add response to context and continue
            messages.append({"role": "assistant", "content": response})
        
        # Fallback if no structured output
        return {
            "conclusion": "Research completed but no structured output generated",
            "key_findings": [],
            "confidence": 3,
            "sources": [],
            "tokens": 1000
        }
    
    async def _execute_mock(self, task: str) -> Dict[str, Any]:
        """Mock execution for testing"""
        await asyncio.sleep(0.1)  # Simulate processing
        
        return {
            "conclusion": f"Mock research completed for: {task[:50]}",
            "key_findings": [
                "Finding 1: Data point observed",
                "Finding 2: Pattern detected"
            ],
            "confidence": 6,
            "sources": ["mock_source_1", "mock_source_2"],
            "tokens": 300
        }


class DeepResearchAgent(SubAgent):
    """
    Specialized sub-agent for in-depth market research.
    
    Handles complex research tasks that require many tool calls.
    """
    
    def __init__(self, tools: List[Any] = None, llm_service: Any = None):
        system_prompt = """You are DeepResearch, a specialized market research agent.

Your expertise:
- Comprehensive market analysis
- Multi-source data correlation
- Trend identification and forecasting

RESEARCH METHODOLOGY:
1. Gather current market data (prices, volumes, sentiment)
2. Analyze on-chain metrics if available
3. Review recent news and events
4. Identify patterns and anomalies
5. Synthesize actionable insights

OUTPUT: Provide structured JSON with conclusion, key_findings, confidence (0-10), and sources."""
        
        super().__init__(
            name="DeepResearch",
            tools=tools,
            llm_service=llm_service,
            system_prompt=system_prompt
        )


class NewsAnalysisAgent(SubAgent):
    """
    Specialized sub-agent for news and sentiment analysis.
    """
    
    def __init__(self, tools: List[Any] = None, llm_service: Any = None):
        system_prompt = """You are NewsAnalysis, a specialized news and sentiment analysis agent.

Your expertise:
- News impact assessment
- Sentiment trend tracking
- Market-moving event identification

ANALYSIS APPROACH:
1. Gather recent news from multiple sources
2. Assess sentiment (positive/negative/neutral)
3. Identify market-moving events
4. Predict potential market impact
5. Provide actionable takeaways

OUTPUT: Provide structured JSON with conclusion, key_findings, confidence (0-10), and sources."""
        
        super().__init__(
            name="NewsAnalysis",
            tools=tools,
            llm_service=llm_service,
            system_prompt=system_prompt
        )


class SubAgentOrchestrator:
    """
    Orchestrate multiple sub-agents for parallel research.
    
    Usage:
        orchestrator = SubAgentOrchestrator(llm_service)
        
        results = await orchestrator.research(
            "Analyze BTC market conditions",
            agents=["DeepResearch", "NewsAnalysis"]
        )
    """
    
    AVAILABLE_AGENTS = {
        "DeepResearch": DeepResearchAgent,
        "NewsAnalysis": NewsAnalysisAgent,
    }
    
    def __init__(self, llm_service: Any = None, tools: List[Any] = None):
        self.llm_service = llm_service
        self.tools = tools or []
        self._agents: Dict[str, SubAgent] = {}
    
    def _get_or_create_agent(self, agent_name: str) -> Optional[SubAgent]:
        """Get or create sub-agent by name"""
        if agent_name in self._agents:
            return self._agents[agent_name]
        
        agent_class = self.AVAILABLE_AGENTS.get(agent_name)
        if not agent_class:
            logger.warning(f"[Orchestrator] Unknown agent: {agent_name}")
            return None
        
        agent = agent_class(tools=self.tools, llm_service=self.llm_service)
        self._agents[agent_name] = agent
        return agent
    
    async def research(
        self, 
        task: str, 
        agents: List[str] = None,
        context: Dict[str, Any] = None
    ) -> List[SubAgentResult]:
        """
        Execute research with multiple sub-agents in parallel.
        
        Args:
            task: Research task
            agents: List of agent names to use
            context: Shared context
            
        Returns:
            List of SubAgentResult from each agent
        """
        agent_names = agents or ["DeepResearch"]
        
        # Create tasks for parallel execution
        tasks = []
        for name in agent_names:
            agent = self._get_or_create_agent(name)
            if agent:
                tasks.append(agent.execute(task, context))
        
        if not tasks:
            logger.warning("[Orchestrator] No agents available")
            return []
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed = []
        for r in results:
            if isinstance(r, SubAgentResult):
                processed.append(r)
            elif isinstance(r, Exception):
                logger.error(f"[Orchestrator] Agent failed: {r}")
        
        logger.info(f"[Orchestrator] Completed {len(processed)}/{len(agent_names)} agents")
        return processed
    
    def get_compact_results(self, results: List[SubAgentResult]) -> List[Dict[str, Any]]:
        """Get compact representations for main agent context"""
        return [r.to_compact_dict() for r in results if r.success]
