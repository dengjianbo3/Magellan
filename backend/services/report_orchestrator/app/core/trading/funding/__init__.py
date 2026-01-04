"""
Funding Fee Awareness Module

This module provides comprehensive funding fee tracking and cost analysis
for perpetual contract trading. It helps traders understand the true cost
of holding positions and make informed decisions.

Modules:
- data_service: OKX API integration for funding rate data
- calculator: Cost calculation and break-even analysis
- entry_timing: Settlement-aware entry timing control
- holding_manager: Dynamic holding time recommendations
- impact_monitor: Force-close on excessive funding impact
- context_provider: Agent prompt injection for funding awareness
- config: Configuration management
"""

from .config import FundingConfig, get_funding_config
from .models import (
    FundingRate,
    FundingBill,
    HoldingCostEstimate,
    TruePnL,
    FundingDirection,
    RateTrend,
    TradeViability,
    EntryAction,
    EntryDecision,
    HoldingAdvice,
    HoldingAlertLevel
)
from .data_service import FundingDataService, get_funding_data_service
from .calculator import FundingCostCalculator, get_funding_calculator
from .entry_timing import EntryTimingController, get_entry_timing_controller
from .holding_manager import HoldingTimeManager, get_holding_time_manager
from .impact_monitor import FundingImpactMonitor, FundingImpact, get_funding_impact_monitor
from .context_provider import FundingContextProvider, get_funding_context_provider

__all__ = [
    # Config
    'FundingConfig',
    'get_funding_config',
    
    # Models
    'FundingRate',
    'FundingBill',
    'HoldingCostEstimate',
    'TruePnL',
    'FundingDirection',
    'RateTrend',
    'TradeViability',
    'EntryAction',
    'EntryDecision',
    'HoldingAdvice',
    'HoldingAlertLevel',
    
    # Services
    'FundingDataService',
    'get_funding_data_service',
    'FundingCostCalculator',
    'get_funding_calculator',
    'EntryTimingController',
    'get_entry_timing_controller',
    'HoldingTimeManager',
    'get_holding_time_manager',
    'FundingImpactMonitor',
    'FundingImpact',
    'get_funding_impact_monitor',
    'FundingContextProvider',
    'get_funding_context_provider',
]

