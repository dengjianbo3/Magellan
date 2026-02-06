"""
Dynamic Tool Loader

Load tools dynamically based on agent role to minimize token usage.
Based on 2025 Context Engineering best practices.

Key strategies:
1. Base tools always loaded (essential)
2. Role-specific tools loaded on demand
3. Lazy initialization to reduce memory
4. Tool schema caching
"""

import logging
from typing import Dict, List, Optional, Set
from .tool import Tool

logger = logging.getLogger(__name__)


# Tool registry mapping tool names to their lazy loaders
TOOL_REGISTRY = {
    # Base tools (always available)
    "web_search": lambda: __import_web_search_tool(),
    
    # Technical analysis tools
    "get_kline": lambda: __import_trading_tools("BTCKlineTool"),
    "get_technical_indicators": lambda: __import_trading_tools("TechnicalIndicatorsTool"),
    "get_btc_price": lambda: __import_trading_tools("BTCPriceTool"),
    
    # On-chain tools
    "get_fear_greed_index": lambda: __import_onchain_tools("FearGreedIndexTool"),
    "get_defi_tvl": lambda: __import_onchain_tools("DefiLlamaTVLTool"),
    "get_onchain_data": lambda: __import_onchain_tools("OnchainDataTool"),
    
    # Market data tools
    "yahoo_finance": lambda: __import_market_tools("YahooFinanceTool"),
    "akshare": lambda: __import_market_tools("AkShareTool"),
    
    # MCP tools
    "tavily_search": lambda: __import_mcp_tools("TavilySearchTool"),
    "public_data": lambda: __import_mcp_tools("PublicDataTool"),
}

# Agent role to tool mapping (P2 Context Engineering)
AGENT_TOOL_PROFILES = {
    # Trading analysts
    "TechnicalAnalyst": {
        "base": ["web_search"],
        "specialized": ["get_kline", "get_technical_indicators", "get_btc_price"],
        "optional": []
    },
    "MacroEconomist": {
        "base": ["web_search"],
        "specialized": [],
        "optional": ["yahoo_finance"]
    },
    "SentimentAnalyst": {
        "base": ["web_search"],
        "specialized": ["get_fear_greed_index"],
        "optional": []
    },
    "OnchainAnalyst": {
        "base": ["web_search"],
        "specialized": ["get_fear_greed_index", "get_defi_tvl", "get_onchain_data"],
        "optional": []
    },
    "QuantStrategist": {
        "base": ["web_search"],
        "specialized": ["get_kline", "get_technical_indicators"],
        "optional": []
    },
    
    # Decision agents (Leader, RiskAssessor, TradeExecutor)
    "Leader": {
        "base": ["web_search"],
        "specialized": [],
        "optional": []
    },
    "RiskAssessor": {
        "base": ["web_search"],
        "specialized": ["get_btc_price"],
        "optional": []
    },
    "TradeExecutor": {
        "base": [],  # Trade executor uses OKX client, not these tools
        "specialized": [],
        "optional": []
    },
}


def __import_web_search_tool():
    """Lazy import web search tool"""
    from .web_search_tool import WebSearchTool
    return WebSearchTool()


def __import_trading_tools(class_name: str):
    """Lazy import trading tools"""
    # These are typically in trading module
    if class_name == "BTCKlineTool":
        from ..trading.trading_tools import BTCKlineTool
        return BTCKlineTool()
    elif class_name == "TechnicalIndicatorsTool":
        from ..trading.trading_tools import TechnicalIndicatorsTool
        return TechnicalIndicatorsTool()
    elif class_name == "BTCPriceTool":
        from ..trading.trading_tools import BTCPriceTool
        return BTCPriceTool()
    raise ValueError(f"Unknown trading tool: {class_name}")


def __import_onchain_tools(class_name: str):
    """Lazy import on-chain tools"""
    from .onchain_tools import FearGreedIndexTool, DefiLlamaTVLTool, OnchainDataTool
    tools = {
        "FearGreedIndexTool": FearGreedIndexTool,
        "DefiLlamaTVLTool": DefiLlamaTVLTool,
        "OnchainDataTool": OnchainDataTool
    }
    if class_name in tools:
        return tools[class_name]()
    raise ValueError(f"Unknown onchain tool: {class_name}")


def __import_market_tools(class_name: str):
    """Lazy import market data tools"""
    if class_name == "YahooFinanceTool":
        from .yahoo_finance_tool import YahooFinanceTool
        return YahooFinanceTool()
    elif class_name == "AkShareTool":
        from .akshare_tool import AkShareTool
        return AkShareTool()
    raise ValueError(f"Unknown market tool: {class_name}")


def __import_mcp_tools(class_name: str):
    """Lazy import MCP tools"""
    from . import mcp_tools
    tool_class = getattr(mcp_tools, class_name, None)
    if tool_class:
        return tool_class()
    raise ValueError(f"Unknown MCP tool: {class_name}")


class DynamicToolLoader:
    """
    Dynamic tool loader based on agent role.
    
    Context Engineering benefits:
    - Reduces tool schema tokens in context
    - Only loads necessary tools per agent
    - Caches instantiated tools for reuse
    
    Usage:
        loader = DynamicToolLoader()
        
        # Get tools for specific agent
        tools = loader.get_tools_for_agent("TechnicalAnalyst")
        
        # Get tools with custom additions
        tools = loader.get_tools_for_agent("OnchainAnalyst", extra_tools=["yahoo_finance"])
    """
    
    def __init__(self):
        self._tool_cache: Dict[str, Tool] = {}
        self._stats = {
            "tools_loaded": 0,
            "cache_hits": 0,
            "schema_tokens_saved": 0
        }
    
    def get_tools_for_agent(
        self, 
        agent_role: str, 
        extra_tools: List[str] = None,
        include_optional: bool = False
    ) -> List[Tool]:
        """
        Get tools appropriate for the given agent role.
        
        Args:
            agent_role: Agent role name (e.g., "TechnicalAnalyst")
            extra_tools: Additional tool names to include
            include_optional: Whether to include optional tools
            
        Returns:
            List of Tool instances
        """
        profile = AGENT_TOOL_PROFILES.get(agent_role, {
            "base": ["web_search"],
            "specialized": [],
            "optional": []
        })
        
        # Collect tool names
        tool_names: Set[str] = set()
        tool_names.update(profile.get("base", []))
        tool_names.update(profile.get("specialized", []))
        
        if include_optional:
            tool_names.update(profile.get("optional", []))
        
        if extra_tools:
            tool_names.update(extra_tools)
        
        # Load tools
        tools = []
        for name in tool_names:
            tool = self._get_or_create_tool(name)
            if tool:
                tools.append(tool)
        
        logger.info(f"[DynamicToolLoader] {agent_role}: loaded {len(tools)} tools")
        return tools
    
    def _get_or_create_tool(self, tool_name: str) -> Optional[Tool]:
        """Get tool from cache or create new instance"""
        # Check cache
        if tool_name in self._tool_cache:
            self._stats["cache_hits"] += 1
            return self._tool_cache[tool_name]
        
        # Get loader function
        loader = TOOL_REGISTRY.get(tool_name)
        if not loader:
            logger.warning(f"[DynamicToolLoader] Unknown tool: {tool_name}")
            return None
        
        # Create tool
        try:
            tool = loader()
            self._tool_cache[tool_name] = tool
            self._stats["tools_loaded"] += 1
            logger.debug(f"[DynamicToolLoader] Created tool: {tool_name}")
            return tool
        except Exception as e:
            logger.error(f"[DynamicToolLoader] Failed to create {tool_name}: {e}")
            return None
    
    def get_tool_count_for_agent(self, agent_role: str) -> Dict[str, int]:
        """Get tool count breakdown for an agent role"""
        profile = AGENT_TOOL_PROFILES.get(agent_role, {})
        return {
            "base": len(profile.get("base", [])),
            "specialized": len(profile.get("specialized", [])),
            "optional": len(profile.get("optional", [])),
            "total": len(profile.get("base", [])) + len(profile.get("specialized", []))
        }
    
    def estimate_token_savings(self, agent_role: str) -> int:
        """
        Estimate tokens saved by using dynamic loading vs full loading.
        
        Assumes:
        - Average tool schema: ~200 tokens
        - Full tool set: ~15 tools
        """
        full_tools = 15  # Approximate count of all tools
        agent_tools = self.get_tool_count_for_agent(agent_role)["total"]
        tokens_per_tool = 200
        
        saved = (full_tools - agent_tools) * tokens_per_tool
        return max(0, saved)
    
    def get_stats(self) -> Dict[str, int]:
        """Get loader statistics"""
        return self._stats.copy()
    
    def clear_cache(self):
        """Clear tool cache"""
        self._tool_cache.clear()


# Convenience function
def get_dynamic_tools(agent_role: str) -> List[Tool]:
    """Get tools for agent using dynamic loading"""
    loader = DynamicToolLoader()
    return loader.get_tools_for_agent(agent_role)


# Singleton instance
_loader_instance: Optional[DynamicToolLoader] = None


def get_tool_loader() -> DynamicToolLoader:
    """Get global tool loader instance"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DynamicToolLoader()
    return _loader_instance
