"""
Reflection Module

Implements the Reflexion pattern for learning from trade outcomes.
"""

from .engine import (
    ReflectionEngine,
    ReflectionMemory,
    AgentWeightAdjuster,
    TradeReflection
)

__all__ = [
    'ReflectionEngine',
    'ReflectionMemory', 
    'AgentWeightAdjuster',
    'TradeReflection'
]
