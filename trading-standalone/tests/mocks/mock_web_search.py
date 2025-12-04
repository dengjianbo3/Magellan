"""
Mock Web Search Service - 模拟网络搜索服务

避免真实的Tavily API调用，使用预定义新闻数据。
"""

import pytest
from typing import List, Dict, Any
from datetime import datetime, timedelta


class MockWebSearchService:
    """Mock网络搜索服务"""
    
    def __init__(self, news_data: List[Dict] = None):
        """
        Args:
            news_data: 预定义的新闻数据列表
        """
        self.news_data = news_data or self._get_default_news()
        self.call_count = 0
        self.search_history = []
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """模拟搜索"""
        self.call_count += 1
        self.search_history.append({
            "query": query,
            "max_results": max_results,
            "timestamp": datetime.now().isoformat()
        })
        
        # 根据查询返回相关新闻
        results = self._filter_news(query)
        return results[:max_results]
    
    def _filter_news(self, query: str) -> List[Dict]:
        """根据查询过滤新闻"""
        query_lower = query.lower()
        
        # 简单的关键词匹配
        filtered = []
        for news in self.news_data:
            if any(keyword in query_lower for keyword in ["btc", "bitcoin", "加密", "crypto"]):
                filtered.append(news)
        
        return filtered if filtered else self.news_data
    
    def _get_default_news(self) -> List[Dict]:
        """默认新闻数据"""
        return [
            {
                "title": "Bitcoin Surges Past $100K Amid Institutional Adoption",
                "url": "https://example.com/news1",
                "content": "Bitcoin reached a new all-time high today as major institutions continue to adopt cryptocurrency...",
                "published_date": (datetime.now() - timedelta(hours=2)).isoformat(),
                "source": "CryptoNews",
                "sentiment": "positive"
            },
            {
                "title": "Federal Reserve Signals Pause in Rate Hikes",
                "url": "https://example.com/news2",
                "content": "The Federal Reserve indicated it may pause interest rate increases, providing relief to risk assets...",
                "published_date": (datetime.now() - timedelta(hours=5)).isoformat(),
                "source": "FinancialTimes",
                "sentiment": "positive"
            },
            {
                "title": "Crypto Market Shows Strong Momentum",
                "url": "https://example.com/news3",
                "content": "Trading volumes surge as retail and institutional investors show renewed interest in digital assets...",
                "published_date": (datetime.now() - timedelta(hours=8)).isoformat(),
                "source": "Bloomberg",
                "sentiment": "positive"
            }
        ]
    
    def set_news(self, news_data: List[Dict]):
        """设置新闻数据"""
        self.news_data = news_data
    
    def add_news(self, news: Dict):
        """添加单条新闻"""
        self.news_data.append(news)
    
    def reset(self):
        """重置状态"""
        self.call_count = 0
        self.search_history = []


# ==================== 预定义新闻场景 ====================

@pytest.fixture
def news_bullish():
    """看涨新闻"""
    return [
        {
            "title": "Bitcoin Breaks Record High on Strong Institutional Demand",
            "content": "Bitcoin surged to unprecedented levels today as major financial institutions announced significant cryptocurrency investments...",
            "sentiment": "very_positive",
            "published_date": datetime.now().isoformat(),
        },
        {
            "title": "SEC Approves Multiple Bitcoin ETFs",
            "content": "The Securities and Exchange Commission approved several Bitcoin ETF applications, marking a major regulatory milestone...",
            "sentiment": "very_positive",
            "published_date": (datetime.now() - timedelta(hours=1)).isoformat(),
        },
        {
            "title": "Major Bank Launches Bitcoin Trading Services",
            "content": "One of the world's largest banks announced it will offer Bitcoin trading to its millions of customers...",
            "sentiment": "positive",
            "published_date": (datetime.now() - timedelta(hours=3)).isoformat(),
        },
        {
            "title": "Inflation Data Shows Cooling Trend",
            "content": "Latest inflation figures came in below expectations, boosting confidence in risk assets including crypto...",
            "sentiment": "positive",
            "published_date": (datetime.now() - timedelta(hours=6)).isoformat(),
        }
    ]


@pytest.fixture
def news_bearish():
    """看跌新闻"""
    return [
        {
            "title": "Regulatory Crackdown Looms for Cryptocurrency Exchanges",
            "content": "Government officials signal stricter regulations on crypto trading platforms following recent concerns...",
            "sentiment": "very_negative",
            "published_date": datetime.now().isoformat(),
        },
        {
            "title": "Major Exchange Reports Security Breach",
            "content": "A leading cryptocurrency exchange confirmed a security incident affecting thousands of user accounts...",
            "sentiment": "very_negative",
            "published_date": (datetime.now() - timedelta(hours=2)).isoformat(),
        },
        {
            "title": "Federal Reserve Maintains Hawkish Stance",
            "content": "Fed chair reiterates commitment to higher interest rates, pressuring risk assets including Bitcoin...",
            "sentiment": "negative",
            "published_date": (datetime.now() - timedelta(hours=4)).isoformat(),
        },
        {
            "title": "Economic Recession Fears Mount",
            "content": "Leading indicators point to potential economic downturn, dampening investor appetite for crypto...",
            "sentiment": "negative",
            "published_date": (datetime.now() - timedelta(hours=7)).isoformat(),
        }
    ]


@pytest.fixture
def news_neutral():
    """中性新闻"""
    return [
        {
            "title": "Bitcoin Trading Volume Remains Steady",
            "content": "Cryptocurrency markets show stable trading volumes as investors await further market signals...",
            "sentiment": "neutral",
            "published_date": datetime.now().isoformat(),
        },
        {
            "title": "Analysts Divided on Bitcoin Price Direction",
            "content": "Market experts offer conflicting predictions for Bitcoin's short-term price movement...",
            "sentiment": "neutral",
            "published_date": (datetime.now() - timedelta(hours=3)).isoformat(),
        },
        {
            "title": "Crypto Market Consolidates After Recent Moves",
            "content": "Bitcoin and other cryptocurrencies enter consolidation phase following previous price action...",
            "sentiment": "neutral",
            "published_date": (datetime.now() - timedelta(hours=6)).isoformat(),
        }
    ]


@pytest.fixture
def news_mixed():
    """混合新闻（有利有弊）"""
    return [
        {
            "title": "Bitcoin Adoption Grows Despite Regulatory Uncertainty",
            "content": "While regulations remain unclear, more businesses are accepting Bitcoin as payment...",
            "sentiment": "mixed",
            "published_date": datetime.now().isoformat(),
        },
        {
            "title": "Crypto Market Volatile Amid Economic Data",
            "content": "Mixed economic signals cause Bitcoin to fluctuate between gains and losses...",
            "sentiment": "mixed",
            "published_date": (datetime.now() - timedelta(hours=2)).isoformat(),
        }
    ]


# ==================== Fixtures ====================

@pytest.fixture
def mock_web_search():
    """基础Mock搜索服务"""
    return MockWebSearchService()


@pytest.fixture
def mock_web_search_bullish(news_bullish):
    """看涨新闻搜索服务"""
    return MockWebSearchService(news_data=news_bullish)


@pytest.fixture
def mock_web_search_bearish(news_bearish):
    """看跌新闻搜索服务"""
    return MockWebSearchService(news_data=news_bearish)


@pytest.fixture
def mock_web_search_neutral(news_neutral):
    """中性新闻搜索服务"""
    return MockWebSearchService(news_data=news_neutral)


@pytest.fixture
def mock_web_search_mixed(news_mixed):
    """混合新闻搜索服务"""
    return MockWebSearchService(news_data=news_mixed)


# ==================== Patch Functions ====================

@pytest.fixture
def patch_web_search(mocker, mock_web_search):
    """Patch Tavily搜索服务"""
    async def mock_tavily_search(query: str, max_results: int = 5):
        return await mock_web_search.search(query, max_results)
    
    # Patch tavily_search function
    mocker.patch(
        "app.core.trading.trading_tools.tavily_search",
        side_effect=mock_tavily_search
    )
    
    return mock_web_search


@pytest.fixture
def patch_web_search_api(mocker):
    """Patch Tavily API HTTP调用"""
    import aioresponses
    
    with aioresponses.aioresponses() as m:
        m.post(
            "https://api.tavily.com/search",
            payload={
                "results": [
                    {
                        "title": "Mock News Title",
                        "url": "https://example.com/news",
                        "content": "Mock news content...",
                        "score": 0.9
                    }
                ]
            },
            repeat=True
        )
        yield m


# ==================== 辅助函数 ====================

def create_news_article(
    title: str,
    sentiment: str = "neutral",
    hours_ago: int = 1
) -> Dict:
    """
    创建新闻文章
    
    Args:
        title: 新闻标题
        sentiment: 情绪 (positive, negative, neutral, mixed)
        hours_ago: 发布时间（几小时前）
    
    Returns:
        新闻字典
    """
    return {
        "title": title,
        "url": f"https://example.com/news/{abs(hash(title))}",
        "content": f"Content for {title}. This is a mock news article created for testing purposes.",
        "published_date": (datetime.now() - timedelta(hours=hours_ago)).isoformat(),
        "source": "MockNewsSource",
        "sentiment": sentiment
    }


@pytest.fixture
def news_article_builder():
    """新闻文章构建器"""
    return create_news_article


def create_news_batch(
    count: int,
    sentiment: str = "neutral",
    topic: str = "Bitcoin"
) -> List[Dict]:
    """
    批量创建新闻
    
    Args:
        count: 数量
        sentiment: 情绪
        topic: 主题
    
    Returns:
        新闻列表
    """
    news_list = []
    for i in range(count):
        news_list.append(create_news_article(
            title=f"{topic} News #{i+1} - {sentiment} outlook",
            sentiment=sentiment,
            hours_ago=i+1
        ))
    return news_list


@pytest.fixture
def news_batch_builder():
    """新闻批量构建器"""
    return create_news_batch
