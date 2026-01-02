# TriggerAgent Module
# LLM-driven market trigger for conditional main analysis
# 
# 注意: LLM 调用复用项目现有的 LLMHelper (app/core/llm_helper.py)
# 不需要额外的 LLM 配置

from .agent import TriggerAgent, TriggerContext
from .scheduler import TriggerScheduler
from .lock import TriggerLock
from .news_crawler import NewsCrawler, NewsItem
from .ta_calculator import TACalculator, TAData
from .prompts import build_trigger_prompt

__all__ = [
    "TriggerAgent",
    "TriggerContext",
    "TriggerScheduler",
    "TriggerLock",
    "NewsCrawler",
    "NewsItem",
    "TACalculator",
    "TAData",
    "build_trigger_prompt"
]
