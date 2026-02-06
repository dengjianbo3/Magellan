"""
Trigger Scorer - 触发评分系统

纯规则评分，不使用 LLM。
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Dict

# 支持独立运行和作为模块导入
try:
    from .news_crawler import NewsItem
    from .ta_calculator import TAData
except ImportError:
    from news_crawler import NewsItem
    from ta_calculator import TAData

logger = logging.getLogger(__name__)


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


def _get_env_int(key: str, default: int) -> int:
    """Get int from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


@dataclass
class TriggerScore:
    """触发分数"""
    news_score: int = 0
    price_score: int = 0
    ta_score: int = 0
    total: int = 0
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        self.total = self.news_score + self.price_score + self.ta_score
    
    def to_dict(self) -> Dict:
        return {
            "news_score": self.news_score,
            "price_score": self.price_score,
            "ta_score": self.ta_score,
            "total": self.total,
            "details": self.details
        }


class TriggerScorer:
    """
    触发评分器 - 纯规则，无 LLM
    
    评分维度:
    - 新闻影响: 0-40 分
    - 价格波动: 0-30 分
    - 技术信号: 0-30 分
    
    满分: 100 分
    触发阈值: 可配置 (默认 60 分)
    """
    
    def __init__(
        self,
        price_change_15m_threshold: float = None,
        price_change_1h_threshold: float = None,
        rsi_low: int = None,
        rsi_high: int = None,
        trigger_threshold: int = None
    ):
        # Read from env vars with defaults
        self.price_change_15m_threshold = price_change_15m_threshold or _get_env_float("SCORER_PRICE_CHANGE_15M", 1.5)
        self.price_change_1h_threshold = price_change_1h_threshold or _get_env_float("SCORER_PRICE_CHANGE_1H", 3.0)
        self.rsi_low = rsi_low or _get_env_int("SCORER_RSI_LOW", 25)
        self.rsi_high = rsi_high or _get_env_int("SCORER_RSI_HIGH", 75)
        self.trigger_threshold = trigger_threshold or _get_env_int("SCORER_TRIGGER_THRESHOLD", 60)
    
    def calculate(
        self,
        news_items: List[NewsItem],
        ta_data: TAData
    ) -> TriggerScore:
        """
        计算触发分数
        
        Args:
            news_items: 新闻列表
            ta_data: 技术分析数据
        
        Returns:
            TriggerScore 对象
        """
        details = {}
        
        # 1. 新闻分数 (0-40)
        news_score, news_details = self._calculate_news_score(news_items)
        details["news"] = news_details
        
        # 2. 价格分数 (0-30)
        price_score, price_details = self._calculate_price_score(ta_data)
        details["price"] = price_details
        
        # 3. 技术分数 (0-30)
        ta_score, ta_details = self._calculate_ta_score(ta_data)
        details["ta"] = ta_details
        
        score = TriggerScore(
            news_score=news_score,
            price_score=price_score,
            ta_score=ta_score,
            details=details
        )
        
        logger.info(
            f"[Scorer] News={news_score}, Price={price_score}, TA={ta_score}, "
            f"Total={score.total}, Threshold={self.trigger_threshold}"
        )
        
        return score
    
    def should_trigger(self, score: TriggerScore) -> bool:
        """判断是否应该触发"""
        return score.total >= self.trigger_threshold
    
    def _calculate_news_score(self, news_items: List[NewsItem]) -> tuple:
        """
        计算新闻分数
        
        - 有高影响力新闻: 基础 20 分
        - 每条信号新闻: +10 分 (最多 +20)
        - 最高: 40 分
        """
        details = {
            "total_news": len(news_items),
            "signal_news": 0,
            "high_impact_titles": []
        }
        
        if not news_items:
            return 0, details
        
        # 统计信号新闻
        signal_news = [n for n in news_items if n.has_signal_keyword]
        details["signal_news"] = len(signal_news)
        
        if not signal_news:
            return 0, details
        
        # 基础分 20 + 每条信号新闻 +10 (最多 +20)
        score = 20 + min(len(signal_news) * 10, 20)
        
        # 记录高影响力标题
        details["high_impact_titles"] = [n.title for n in signal_news[:3]]
        
        return min(score, 40), details
    
    def _calculate_price_score(self, ta_data: TAData) -> tuple:
        """
        计算价格波动分数
        
        - 15分钟变化 >= 1.5%: 15 分
        - 1小时变化 >= 3.0%: 15 分
        - 最高: 30 分
        """
        details = {
            "price_change_15m": ta_data.price_change_15m,
            "price_change_1h": ta_data.price_change_1h,
            "triggers": []
        }
        
        score = 0
        
        if abs(ta_data.price_change_15m) >= self.price_change_15m_threshold:
            score += 15
            details["triggers"].append(f"15m change: {ta_data.price_change_15m}%")
        
        if abs(ta_data.price_change_1h) >= self.price_change_1h_threshold:
            score += 15
            details["triggers"].append(f"1h change: {ta_data.price_change_1h}%")
        
        return min(score, 30), details
    
    def _calculate_ta_score(self, ta_data: TAData) -> tuple:
        """
        计算技术分析分数
        
        - RSI 极值 (< 25 或 > 75): 10 分
        - MACD 交叉: 10 分
        - 成交量异常: 5 分
        - 多周期趋势一致: 5 分
        - 最高: 30 分
        """
        details = {
            "rsi_15m": ta_data.rsi_15m,
            "macd_crossover": ta_data.macd_crossover,
            "volume_spike": ta_data.volume_spike,
            "trend_alignment": f"{ta_data.trend_15m}/{ta_data.trend_1h}/{ta_data.trend_4h}",
            "triggers": []
        }
        
        score = 0
        
        # RSI 极值
        if ta_data.rsi_15m < self.rsi_low or ta_data.rsi_15m > self.rsi_high:
            score += 10
            details["triggers"].append(f"RSI extreme: {ta_data.rsi_15m}")
        
        # MACD 交叉
        if ta_data.macd_crossover:
            score += 10
            details["triggers"].append("MACD crossover")
        
        # 成交量异常
        if ta_data.volume_spike:
            score += 5
            details["triggers"].append("Volume spike")
        
        # 多周期趋势一致
        if ta_data.trend_15m == ta_data.trend_1h == ta_data.trend_4h and ta_data.trend_15m != "neutral":
            score += 5
            details["triggers"].append(f"Trend alignment: {ta_data.trend_15m}")
        
        return min(score, 30), details


# 测试入口
if __name__ == "__main__":
    from .news_crawler import NewsItem
    from .ta_calculator import TAData
    
    # 模拟数据
    news = [
        NewsItem(title="SEC Approves Bitcoin ETF", source="CoinDesk", url="", has_signal_keyword=True),
        NewsItem(title="Bitcoin price analysis", source="Decrypt", url="", has_signal_keyword=False),
    ]
    
    ta = TAData(
        rsi_15m=28,
        macd_crossover=True,
        volume_spike=True,
        price_change_15m=2.5,
        price_change_1h=4.2,
        trend_15m="bullish",
        trend_1h="bullish",
        trend_4h="neutral"
    )
    
    scorer = TriggerScorer()
    score = scorer.calculate(news, ta)
    
    print(f"\nTotal Score: {score.total}")
    print(f"Should Trigger: {scorer.should_trigger(score)}")
    print(f"Details: {score.details}")
