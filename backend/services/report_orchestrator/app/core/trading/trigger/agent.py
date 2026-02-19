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
from typing import Tuple, Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.trading.paper_trader import PaperTrader

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
    from app.core.trading.trading_config import get_infra_config
    from app.core.trading.constants import TRIGGER, RETRY
    from app.core.trading.exceptions import (
        TriggerError, NewsServiceError, TechnicalAnalysisError, LLMError
    )
except ImportError:
    # 独立运行时的回退
    LLMHelper = None
    get_infra_config = None
    TRIGGER = None
    RETRY = None
    # Define fallback exceptions
    TriggerError = Exception
    NewsServiceError = Exception
    TechnicalAnalysisError = Exception
    LLMError = Exception

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
    
    # 仓位数据 (新增)
    has_position: bool = False
    position_direction: str = "none"  # long / short / none
    position_pnl_percent: float = 0.0
    position_size_usd: float = 0.0
    
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
            "news_count": self.news_count,
            "has_position": self.has_position,
            "position_direction": self.position_direction,
            "position_pnl_percent": self.position_pnl_percent
        }


class TriggerAgent:
    """
    LLM 驱动的触发器代理

    使用 LLM 深度分析新闻和指标，决定是否触发主分析。
    复用项目现有的 LLMHelper 进行 LLM 调用。

    Attributes:
        news_crawler: 新闻爬虫实例
        ta_calculator: 技术分析计算器实例
        paper_trader: 模拟交易器实例 (用于获取仓位信息)
        llm_helper: LLM 调用助手
        confidence_threshold: 触发置信度阈值 (0-100)
    """

    def __init__(
        self,
        news_crawler: Optional[NewsCrawler] = None,
        ta_calculator: Optional[TACalculator] = None,
        llm_helper: Optional["LLMHelper"] = None,
        paper_trader: Optional["PaperTrader"] = None,
        llm_gateway_url: Optional[str] = None,
        confidence_threshold: Optional[int] = None
    ):
        """
        初始化触发器代理。

        Args:
            news_crawler: 新闻爬虫实例，默认创建新实例
            ta_calculator: 技术分析计算器，默认创建新实例
            llm_helper: LLM 调用助手，默认根据环境自动创建
            paper_trader: 模拟交易器，用于获取当前仓位信息
            llm_gateway_url: LLM 网关 URL，默认从配置读取
            confidence_threshold: 触发置信度阈值 (0-100)，默认从环境变量读取
        """
        self.news_crawler = news_crawler or NewsCrawler()
        self.ta_calculator = ta_calculator or TACalculator()
        self.paper_trader = paper_trader

        # 复用现有的 LLMHelper
        if llm_helper:
            self.llm_helper = llm_helper
        elif LLMHelper:
            gateway_url = llm_gateway_url or (get_infra_config().llm_gateway_url if get_infra_config else "http://llm_gateway:8003")
            llm_timeout = RETRY.LLM_TIMEOUT if RETRY else 60
            self.llm_helper = LLMHelper(llm_gateway_url=gateway_url, timeout=llm_timeout)
        else:
            self.llm_helper = None  # 独立运行模式

        # 从环境变量读取配置
        default_threshold = TRIGGER.DEFAULT_CONFIDENCE_THRESHOLD if TRIGGER else 70
        self.confidence_threshold = confidence_threshold or int(
            os.getenv("TRIGGER_CONFIDENCE_THRESHOLD", str(default_threshold))
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
            news_items, ta_data = await self._gather_market_data()

            # 2. 获取仓位数据
            position_data = await self._get_position_data()

            # 3. 构建 Prompt 并调用 LLM
            ta_dict = self._build_ta_dict(ta_data)
            news_dicts = [{"source": n.source, "title": n.title} for n in news_items]
            prompt = build_trigger_prompt(news_dicts, ta_dict, position_data)

            llm_result = await self._call_llm(prompt, ta_dict)

            # 4. 解析结果并构建上下文
            should_trigger, context = self._build_context(
                llm_result, ta_data, news_items, position_data
            )

            # 记录
            self._last_check_time = datetime.now()
            self._last_context = context

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"[TriggerAgent] LLM check completed in {elapsed:.2f}s, "
                f"Trigger={should_trigger}, Confidence={context.confidence}, Urgency={context.urgency}"
            )

            return should_trigger, context

        except LLMError as e:
            logger.error(f"[TriggerAgent] LLM analysis failed: {e}")
            return False, TriggerContext(
                should_trigger=False,
                trigger_time=datetime.now().isoformat(),
                reasoning=f"LLM Error: {str(e)}"
            )
        except TriggerError as e:
            logger.error(f"[TriggerAgent] Trigger system error: {e}")
            return False, TriggerContext(
                should_trigger=False,
                trigger_time=datetime.now().isoformat(),
                reasoning=f"Trigger Error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[TriggerAgent] Unexpected error: {e}")
            return False, TriggerContext(
                should_trigger=False,
                trigger_time=datetime.now().isoformat(),
                reasoning=f"Unexpected Error: {str(e)}"
            )

    async def _gather_market_data(self) -> Tuple[List, TAData]:
        """并行收集新闻和技术分析数据"""
        news_task = self.news_crawler.fetch_latest()
        ta_task = self.ta_calculator.calculate()

        news_items, ta_data = await asyncio.gather(
            news_task,
            ta_task,
            return_exceptions=True
        )

        # 处理异常 - 使用具体异常类型进行日志记录
        if isinstance(news_items, Exception):
            if isinstance(news_items, NewsServiceError):
                logger.warning(f"[TriggerAgent] News service error: {news_items}")
            else:
                logger.warning(f"[TriggerAgent] News fetch failed: {news_items}")
            news_items = []

        if isinstance(ta_data, Exception):
            if isinstance(ta_data, TechnicalAnalysisError):
                logger.warning(f"[TriggerAgent] TA calculation error: {ta_data}")
            else:
                logger.warning(f"[TriggerAgent] TA calculation failed: {ta_data}")
            ta_data = TAData()

        return news_items, ta_data

    async def _get_position_data(self) -> Dict:
        """获取当前仓位数据"""
        position_data = {
            "has_position": False,
            "direction": "none",
            "pnl_percent": 0.0,
            "size_usd": 0.0
        }

        if self.paper_trader:
            try:
                position = await self.paper_trader.get_position()
                if position and position.get("direction") and position.get("direction") != "none":
                    position_data = {
                        "has_position": True,
                        "direction": position.get("direction", "none"),
                        "pnl_percent": position.get("profit_loss_percent", 0.0),
                        "size_usd": position.get("position_value", 0.0)
                    }
                    logger.info(f"[TriggerAgent] Position: {position_data['direction']}, PnL: {position_data['pnl_percent']:.2f}%")
            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"[TriggerAgent] Position fetch network error: {e}")
            except Exception as e:
                logger.warning(f"[TriggerAgent] Position fetch failed: {type(e).__name__}: {e}")

        return position_data

    def _build_ta_dict(self, ta_data: TAData) -> Dict:
        """构建技术分析字典"""
        if hasattr(ta_data, 'to_dict'):
            return ta_data.to_dict()
        return {
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

    async def _call_llm(self, prompt: str, ta_dict: Dict) -> Dict:
        """调用 LLM 进行分析"""
        logger.info("[TriggerAgent] Calling LLM for analysis...")

        if self.llm_helper:
            return await self.llm_helper.call(
                prompt=prompt,
                response_format="json"
            )
        else:
            # Mock 模式 (独立运行测试)
            return await self._mock_llm_call(prompt, ta_dict)

    def _build_context(
        self,
        llm_result: Dict,
        ta_data: TAData,
        news_items: List,
        position_data: Dict
    ) -> Tuple[bool, TriggerContext]:
        """解析 LLM 结果并构建触发上下文"""
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
            has_position=position_data.get("has_position", False),
            position_direction=position_data.get("direction", "none"),
            position_pnl_percent=position_data.get("pnl_percent", 0.0),
            position_size_usd=position_data.get("size_usd", 0.0),
            llm_response=llm_result
        )

        return should_trigger, context
    
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

        # Use constants with env var fallback
        rsi_low = TRIGGER.RSI_LOW_THRESHOLD if TRIGGER else int(os.getenv("SCORER_RSI_LOW", "25"))
        rsi_high = TRIGGER.RSI_HIGH_THRESHOLD if TRIGGER else int(os.getenv("SCORER_RSI_HIGH", "75"))
        price_threshold = TRIGGER.PRICE_CHANGE_THRESHOLD if TRIGGER else float(os.getenv("SCORER_PRICE_CHANGE_15M", "1.5"))

        should_trigger = high_impact_count >= 1 or price_change >= price_threshold or rsi <= rsi_low or rsi >= rsi_high

        if should_trigger:
            base_conf = TRIGGER.BASE_CONFIDENCE if TRIGGER else 60
            conf_per_event = TRIGGER.CONFIDENCE_PER_EVENT if TRIGGER else 15
            max_conf = TRIGGER.MAX_CONFIDENCE if TRIGGER else 95
            return {
                "should_trigger": True,
                "urgency": "high" if high_impact_count >= 1 else "medium",
                "confidence": min(base_conf + high_impact_count * conf_per_event, max_conf),
                "reasoning": f"检测到{high_impact_count}条高影响力新闻，建议进行深度分析。",
                "key_events": ["市场重大事件"]
            }
        else:
            low_min = TRIGGER.LOW_CONFIDENCE_MIN if TRIGGER else 20
            low_max = TRIGGER.LOW_CONFIDENCE_MAX if TRIGGER else 40
            return {
                "should_trigger": False,
                "urgency": "low",
                "confidence": random.randint(low_min, low_max),
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
