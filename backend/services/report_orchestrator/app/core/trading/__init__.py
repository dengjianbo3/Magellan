"""
Auto Trading System Module

This module provides automated trading capabilities based on the roundtable meeting system.
It enables periodic analysis of investment targets (like Bitcoin) and automatic trade execution.

Trading Backends:
- PaperTrader: Local simulation for testing (default)
- OKXClient: OKX Demo Trading API for realistic testing

Refactored Architecture (v2.0):
- Domain: Unified Position model
- Safety: Centralized SafetyGuard
- Reflection: ReflectionEngine for learning from trades
- Executor: ExecutorAgent (ReWOOAgent-based)
- Orchestration: LangGraph workflow (TradingGraph)
"""

# Trading Backends
from .paper_trader import PaperTrader, get_paper_trader
from .okx_client import OKXClient, get_okx_client

# Trading Components
from .trading_tools import TradingToolkit
from .trading_agents import create_trading_agents
from .trading_meeting import TradingMeeting
from .agent_memory import AgentMemory, AgentMemoryStore
from .scheduler import TradingScheduler

# Phase 1-4 Refactored Modules
from .domain import Position, PositionSource
from .safety import SafetyGuard, SafetyCheckResult, BlockReason
from .reflection import ReflectionEngine, TradeReflection, ReflectionMemory
from .executor_agent import ExecutorAgent
from .orchestration import TradingGraph, TradingState, create_initial_state
from .decision_store import TradingDecision, TradingDecisionStore, get_decision_store

__all__ = [
    # Trading Backends
    'PaperTrader',
    'get_paper_trader',
    'OKXClient',
    'get_okx_client',
    
    # Trading Components
    'TradingToolkit',
    'create_trading_agents',
    'TradingMeeting',
    'AgentMemory',
    'AgentMemoryStore',
    'TradingScheduler',
    
    # Domain Models (v2.0)
    'Position',
    'PositionSource',
    
    # Safety (v2.0)
    'SafetyGuard',
    'SafetyCheckResult',
    'BlockReason',
    
    # Reflection (v2.0)
    'ReflectionEngine',
    'TradeReflection',
    'ReflectionMemory',
    
    # Executor (v2.0)
    'ExecutorAgent',
    
    # Decision Storage (v2.0)
    'TradingDecision',
    'TradingDecisionStore',
    'get_decision_store',
    
    # Orchestration (v2.0)
    'TradingGraph',
    'TradingState',
    'create_initial_state',
]

