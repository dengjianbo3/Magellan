"""
Trigger Agent - LLM 驱动的触发器代理

使用 LLM 深度分析新闻和指标，决定是否触发主分析。
复用现有的 LLMHelper 进行 LLM 调用。
"""

import asyncio
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Tuple, Dict, List, Optional

# 支持独立运行和作为模块导入
try:
    from .news_crawler import NewsCrawler, NewsItem
    from .ta_calculator import TACalculator, TAData
    from .prompts import build_trigger_prompt
except ImportError:
    from news_crawler import NewsCrawler, NewsItem
    from ta_calculator import TACalculator, TAData
    from prompts import build_trigger_prompt

# 复用现有的 LLMHelper
try:
    from app.core.llm_helper import LLMHelper
except ImportError:
    # 独立运行时的回退
    LLMHelper = None

logger = logging.getLogger(__name__)


@dataclass
class TriggerContext:
    """触发上下文 - 传递给主分析"""
    should_trigger: bool
    trigger_time: str
    
    # LLM 分析结果
    urgency: str = "low"  # high / medium / low
    confidence: int = 0   # 0-100
    reasoning: str = ""
    key_events: List[str] = field(default_factory=list)
    
    # 市场数据
    current_price: float = 0.0
    price_change_15m: float = 0.0
    price_change_1h: float = 0.0
    rsi_15m: float = 50.0
    news_count: int = 0
    
    # 原始 LLM 响应
    llm_response: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "should_trigger": self.should_trigger,
            "trigger_time": self.trigger_time,
            "urgency": self.urgency,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "key_events": self.key_events,
            "current_price": self.current_price,
            "price_change_15m": self.price_change_15m,
            "price_change_1h": self.price_change_1h,
            "rsi_15m": self.rsi_15m,
            "news_count": self.news_count
        }


class TriggerAgent:
    """
    LLM 驱动的触发器代理
    
    使用 LLM 深度分析新闻和指标，决定是否触发主分析。
    复用项目现有的 LLMHelper 进行 LLM 调用。
    """
    
    def __init__(
        self,
        news_crawler: Optional[NewsCrawler] = None,
        ta_calculator: Optional[TACalculator] = None,
        llm_helper: Optional["LLMHelper"] = None,
        llm_gateway_url: str = "http://llm_gateway:8003",
        confidence_threshold: int = None
    ):
        self.news_crawler = news_crawler or NewsCrawler()
        self.ta_calculator = ta_calculator or TACalculator()
        
        # 复用现有的 LLMHelper
        if llm_helper:
            self.llm_helper = llm_helper
        elif LLMHelper:
            self.llm_helper = LLMHelper(llm_gateway_url=llm_gateway_url, timeout=30)
        else:
            self.llm_helper = None  # 独立运行模式
        
        # 从环境变量读取配置
        self.confidence_threshold = confidence_threshold or int(
            os.getenv("TRIGGER_CONFIDENCE_THRESHOLD", "70")
        )
        
        self._last_check_time: Optional[datetime] = None
        self._last_context: Optional[TriggerContext] = None
    
    async def check(self) -> Tuple[bool, TriggerContext]:
        """
        使用 LLM 分析并决定是否触发主分析
        
        Returns:
            (should_trigger, context)
        """
        start_time = datetime.now()
        logger.info("[TriggerAgent] Starting LLM-based check...")
        
        try:
            # 1. 并行收集数据
            news_task = self.news_crawler.fetch_latest()
            ta_task = self.ta_calculator.calculate()
            
            news_items, ta_data = await asyncio.gather(
                news_task,
                ta_task,
                return_exceptions=True
            )
            
            # 处理异常
            if isinstance(news_items, Exception):
                logger.warning(f"[TriggerAgent] News fetch failed: {news_items}")
                news_items = []
            
            if isinstance(ta_data, Exception):
                logger.warning(f"[TriggerAgent] TA calculation failed: {ta_data}")
                ta_data = TAData()
            
            # 2. 构建 Prompt
            news_dicts = [{"source": n.source, "title": n.title} for n in news_items]
            ta_dict = ta_data.to_dict() if hasattr(ta_data, 'to_dict') else {
                "current_price": ta_data.current_price,
                "price_change_15m": ta_data.price_change_15m,
                "price_change_1h": ta_data.price_change_1h,
                "rsi_15m": ta_data.rsi_15m,
                "macd_crossover": ta_data.macd_crossover,
                "volume_spike": ta_data.volume_spike,
                "trend_15m": ta_data.trend_15m,
                "trend_1h": ta_data.trend_1h,
                "trend_4h": ta_data.trend_4h
            }
            
            prompt = build_trigger_prompt(news_dicts, ta_dict)
            
            # 3. 调用 LLM (使用现有的 LLMHelper)
            logger.info("[TriggerAgent] Calling LLM for analysis...")
            
            if self.llm_helper:
                # 使用现有 LLMHelper
                llm_result = await self.llm_helper.call(
                    prompt=prompt,
                    response_format="json"
                )
            else:
                # Mock 模式 (独立运行测试)
                llm_result = await self._mock_llm_call(prompt, ta_dict)
            
            # 4. 解析 LLM 输出
            should_trigger = llm_result.get("should_trigger", False)
            urgency = llm_result.get("urgency", "low")
            confidence = llm_result.get("confidence", 0)
            reasoning = llm_result.get("reasoning", "")
            key_events = llm_result.get("key_events", [])
            
            # 检查是否有错误
            if "error" in llm_result:
                logger.warning(f"[TriggerAgent] LLM error: {llm_result.get('error')}")
                should_trigger = False
            
            # 额外检查置信度阈值
            if should_trigger and confidence < self.confidence_threshold:
                logger.info(
                    f"[TriggerAgent] LLM says trigger but confidence {confidence} < threshold {self.confidence_threshold}"
                )
                should_trigger = False
            
            # 5. 构建上下文
            context = TriggerContext(
                should_trigger=should_trigger,
                trigger_time=datetime.now().isoformat(),
                urgency=urgency,
                confidence=confidence,
                reasoning=reasoning,
                key_events=key_events,
                current_price=ta_data.current_price,
                price_change_15m=ta_data.price_change_15m,
                price_change_1h=ta_data.price_change_1h,
                rsi_15m=ta_data.rsi_15m,
                news_count=len(news_items),
                llm_response=llm_result
            )
            
            # 记录
            self._last_check_time = datetime.now()
            self._last_context = context
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"[TriggerAgent] LLM check completed in {elapsed:.2f}s, "
                f"Trigger={should_trigger}, Confidence={confidence}, Urgency={urgency}"
            )
            
            return should_trigger, context
            
        except Exception as e:
            logger.error(f"[TriggerAgent] Check failed: {e}")
            # 返回安全默认值
            return False, TriggerContext(
                should_trigger=False,
                trigger_time=datetime.now().isoformat(),
                reasoning=f"Error: {str(e)}"
            )
    
    async def _mock_llm_call(self, prompt: str, ta_dict: Dict) -> Dict:
        """Mock LLM 调用 (独立运行测试用)"""
        import re
        import random
        
        # 只提取新闻部分
        news_section = ""
        news_match = re.search(r'### 最新新闻.*?\n(.*?)###', prompt, re.DOTALL)
        if news_match:
            news_section = news_match.group(1).lower()
        
        # 检测高影响力词
        high_impact_words = ["sec approve", "etf approve", "fed rate", "hack", "exploit", 
                            "halving", "lawsuit", "crash", "surge"]
        high_impact_count = sum(1 for w in high_impact_words if w in news_section)
        
        price_change = abs(ta_dict.get("price_change_15m", 0))
        rsi = ta_dict.get("rsi_15m", 50)
        
        should_trigger = high_impact_count >= 1 or price_change >= 1.5 or rsi <= 25 or rsi >= 75
        
        if should_trigger:
            return {
                "should_trigger": True,
                "urgency": "high" if high_impact_count >= 1 else "medium",
                "confidence": min(60 + high_impact_count * 15, 95),
                "reasoning": f"检测到{high_impact_count}条高影响力新闻，建议进行深度分析。",
                "key_events": ["市场重大事件"]
            }
        else:
            return {
                "should_trigger": False,
                "urgency": "low",
                "confidence": random.randint(20, 40),
                "reasoning": f"市场平稳：价格变化{price_change:.2f}%，RSI={rsi:.1f}在正常范围。",
                "key_events": []
            }
    
    def get_last_check(self) -> Optional[TriggerContext]:
        """获取上次检查结果"""
        return self._last_context
    
    def get_status(self) -> Dict:
        """获取代理状态"""
        return {
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "last_trigger": self._last_context.should_trigger if self._last_context else None,
            "last_confidence": self._last_context.confidence if self._last_context else None,
            "confidence_threshold": self.confidence_threshold
        }
