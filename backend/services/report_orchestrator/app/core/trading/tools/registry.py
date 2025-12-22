"""
Tool Registry

Central registry for managing and discovering trading tools.
"""

import logging
from typing import Dict, List, Optional, Type, Any

from .base import BaseTool, ToolCategory

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for trading tools.
    
    Manages tool registration, discovery, and instantiation.
    Implements singleton pattern for global access.
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __init__(self):
        """Initialize the registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            cat: [] for cat in ToolCategory
        }
    
    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool instance.
        
        Args:
            tool: Tool instance to register
        """
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, replacing")
        
        self._tools[tool.name] = tool
        
        # Track by category
        if tool.name not in self._categories[tool.category]:
            self._categories[tool.category].append(tool.name)
        
        logger.debug(f"Registered tool: {tool.name} ({tool.category.value})")
    
    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class for lazy instantiation.
        
        Args:
            tool_class: Tool class to register
        """
        # Create temporary instance to get name
        temp = tool_class()
        self._tool_classes[temp.name] = tool_class
        
        # Track by category
        if temp.name not in self._categories[temp.category]:
            self._categories[temp.category].append(temp.name)
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        # Check registered instances
        if name in self._tools:
            return self._tools[name]
        
        # Check registered classes (lazy instantiation)
        if name in self._tool_classes:
            tool = self._tool_classes[name]()
            self._tools[name] = tool
            return tool
        
        return None
    
    def get_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Get all tools in a category.
        
        Args:
            category: Tool category
            
        Returns:
            List of tools in that category
        """
        tool_names = self._categories.get(category, [])
        return [self.get(name) for name in tool_names if self.get(name)]
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(set(list(self._tools.keys()) + list(self._tool_classes.keys())))
    
    def list_by_category(self) -> Dict[str, List[str]]:
        """List tools organized by category."""
        return {
            cat.value: names 
            for cat, names in self._categories.items()
            if names
        }
    
    def get_schemas(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get OpenAI function calling schemas for tools.
        
        Args:
            tool_names: Optional list of specific tools (all if None)
            
        Returns:
            List of schema dicts
        """
        names = tool_names or self.list_tools()
        schemas = []
        
        for name in names:
            tool = self.get(name)
            if tool:
                schemas.append(tool.get_schema())
        
        return schemas
    
    def get_for_agent(self, agent_type: str) -> List[BaseTool]:
        """
        Get appropriate tools for an agent type.
        
        Args:
            agent_type: Agent type identifier
            
        Returns:
            List of tools suitable for that agent
        """
        # Default tool mappings by agent type
        agent_tools = {
            "TechnicalAnalyst": [
                ToolCategory.MARKET,
                ToolCategory.ANALYSIS
            ],
            "MacroEconomist": [
                ToolCategory.SEARCH,
                ToolCategory.MARKET
            ],
            "SentimentAnalyst": [
                ToolCategory.SEARCH,
                ToolCategory.MARKET
            ],
            "QuantStrategist": [
                ToolCategory.MARKET,
                ToolCategory.ANALYSIS
            ],
            "RiskAssessor": [
                ToolCategory.MARKET,
                ToolCategory.ACCOUNT
            ],
            "Leader": [],  # Leader uses no direct tools
            "TradeExecutor": [
                ToolCategory.EXECUTION,
                ToolCategory.ACCOUNT,
                ToolCategory.MARKET
            ]
        }
        
        categories = agent_tools.get(agent_type, [ToolCategory.MARKET])
        tools = []
        
        for category in categories:
            tools.extend(self.get_by_category(category))
        
        return tools
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._tool_classes.clear()
        self._categories = {cat: [] for cat in ToolCategory}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self.list_tools()),
            "by_category": {
                cat.value: len(names) 
                for cat, names in self._categories.items()
            },
            "tool_stats": [
                tool.get_stats() 
                for tool in self._tools.values()
            ]
        }


# Module-level convenience function
def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return ToolRegistry.get_instance()
