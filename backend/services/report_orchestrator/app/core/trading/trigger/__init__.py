# TriggerAgent Module
# LLM-driven market trigger for conditional main analysis
# 
# 三层触发架构：
#   Layer 1: FastMonitor (硬条件，无LLM)
#   Layer 2: TriggerAgent (LLM分析)
#   Layer 3: Full Analysis (完整分析)

from .agent import TriggerAgent, TriggerContext
from .scheduler import TriggerScheduler
from .lock import TriggerLock
from .news_crawler import NewsCrawler, NewsItem
from .ta_calculator import TACalculator, TAData
from .fast_monitor import FastMonitor, FastTriggerResult, FastMonitorConfig
from .prompts import build_trigger_prompt

__all__ = [
    # Layer 2: LLM-based trigger
    "TriggerAgent",
    "TriggerContext",
    # Scheduler
    "TriggerScheduler",
    "TriggerLock",
    # Data providers
    "NewsCrawler",
    "NewsItem",
    "TACalculator",
    "TAData",
    # Layer 1: Fast monitor (new)
    "FastMonitor",
    "FastTriggerResult", 
    "FastMonitorConfig",
    # Utilities
    "build_trigger_prompt"
]

