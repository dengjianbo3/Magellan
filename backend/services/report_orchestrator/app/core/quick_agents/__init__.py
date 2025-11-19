"""
Quick Agents - 快速判断模式专用的轻量级Agent
"""
# Early Stage Investment Agents (早期投资)
from .team_quick_agent import TeamQuickAgent
from .market_quick_agent import MarketQuickAgent
from .red_flag_agent import RedFlagAgent

# Growth Stage Investment Agents (成长期投资)
from .financial_health_agent import FinancialHealthAgent
from .growth_potential_agent import GrowthPotentialAgent
from .market_position_agent import MarketPositionAgent

# Public Market Investment Agents (公开市场投资)
from .valuation_quick_agent import ValuationQuickAgent
from .fundamentals_agent import FundamentalsAgent
from .technical_analysis_agent import TechnicalAnalysisAgent

# Alternative Investment Agents (另类投资)
from .tech_foundation_agent import TechFoundationAgent
from .tokenomics_agent import TokenomicsAgent
from .community_activity_agent import CommunityActivityAgent

# Industry Research Agents (行业研究)
from .market_size_agent import MarketSizeAgent
from .competition_landscape_agent import CompetitionLandscapeAgent
from .trend_analysis_agent import TrendAnalysisAgent
from .opportunity_scan_agent import OpportunityScanAgent
from .industry_researcher_agent import IndustryResearcherAgent

__all__ = [
    # Early Stage
    "TeamQuickAgent",
    "MarketQuickAgent",
    "RedFlagAgent",
    # Growth Stage
    "FinancialHealthAgent",
    "GrowthPotentialAgent",
    "MarketPositionAgent",
    # Public Market
    "ValuationQuickAgent",
    "FundamentalsAgent",
    "TechnicalAnalysisAgent",
    # Alternative Investment
    "TechFoundationAgent",
    "TokenomicsAgent",
    "CommunityActivityAgent",
    # Industry Research
    "MarketSizeAgent",
    "CompetitionLandscapeAgent",
    "TrendAnalysisAgent",
    "OpportunityScanAgent",
    "IndustryResearcherAgent",
]
