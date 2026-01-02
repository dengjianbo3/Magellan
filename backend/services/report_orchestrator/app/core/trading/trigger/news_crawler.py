"""
News Crawler - 定向新闻爬虫

爬取主流加密货币新闻网站，提取 BTC 相关新闻。
"""

import asyncio
import aiohttp
import logging
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    source: str
    url: str
    published_at: Optional[datetime] = None
    has_signal_keyword: bool = False
    impact_score: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "has_signal_keyword": self.has_signal_keyword,
            "impact_score": self.impact_score
        }


# 信号关键词 (高影响力)
SIGNAL_KEYWORDS = [
    # 监管
    "SEC", "ETF", "Fed", "regulation", "ban", "approve", "lawsuit",
    # 安全
    "hack", "exploit", "breach", "stolen", "attack",
    # 技术
    "halving", "fork", "upgrade", "BIP", "lightning",
    # 市场
    "whale", "Mt.Gox", "exchange", "bankrupt", "liquidation",
    # 政治
    "Trump", "Biden", "Gensler", "Congress", "White House"
]

# 噪音关键词 (忽略)
NOISE_KEYWORDS = [
    "price prediction", "will reach", "target price",
    "rumor", "speculation", "unconfirmed",
    "meme", "NFT", "airdrop", "giveaway"
]


class NewsCrawler:
    """
    定向新闻爬虫
    
    爬取目标:
    - CoinTelegraph (工作正常)
    - Bitcoin Magazine (替代 CoinDesk)
    - The Block (替代 Decrypt)
    """
    
    SOURCES = [
        {
            "name": "CoinTelegraph",
            "url": "https://cointelegraph.com/tags/bitcoin",
            "article_selector": "article, div.post-card-inline, li.posts-listing__item",
            "title_selector": "span.post-card-inline__title, h2, a.post-card-inline__title-link",
            "link_selector": "a[href*='/news/']"
        },
        {
            "name": "BitcoinMagazine",
            "url": "https://bitcoinmagazine.com/markets",
            "article_selector": "h3.entry-title",  # 直接选择标题
            "title_selector": "a",
            "link_selector": "a"
        },
        {
            "name": "Decrypt",
            "url": "https://decrypt.co/news",
            "article_selector": "div",  # 占位，使用 JSON 提取
            "title_selector": "h2",
            "link_selector": "a",
            "use_json": True
        }
    ]
    
    def __init__(self, timeout: int = 10, max_age_minutes: int = 60):
        self.timeout = timeout
        self.max_age_minutes = max_age_minutes
        self._seen_urls: Set[str] = set()
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    
    async def fetch_latest(self) -> List[NewsItem]:
        """获取最新新闻"""
        all_news = []
        
        async with aiohttp.ClientSession(
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            tasks = [self._fetch_source(session, source) for source in self.SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch {self.SOURCES[i]['name']}: {result}")
                else:
                    all_news.extend(result)
        
        # 去重
        unique_news = self._dedupe(all_news)
        
        # 计算影响分数
        for news in unique_news:
            self._calculate_impact(news)
        
        # 按影响分数排序
        unique_news.sort(key=lambda x: x.impact_score, reverse=True)
        
        logger.info(f"[NewsCrawler] Fetched {len(unique_news)} unique news items")
        return unique_news
    
    async def _fetch_source(self, session: aiohttp.ClientSession, source: Dict) -> List[NewsItem]:
        """从单个来源获取新闻"""
        try:
            async with session.get(source["url"]) as response:
                if response.status != 200:
                    logger.warning(f"{source['name']} returned {response.status}")
                    return []
                
                html = await response.text()
                
                # Decrypt 使用 Next.js JSON 嵌入
                if source.get("use_json"):
                    return self._parse_json_embedded(html, source)
                
                return self._parse_html(html, source)
                
        except Exception as e:
            logger.error(f"Error fetching {source['name']}: {e}")
            return []
    
    def _parse_json_embedded(self, html: str, source: Dict) -> List[NewsItem]:
        """从嵌入的 JSON 中提取新闻 (Next.js 页面)"""
        import json
        import re
        
        news_items = []
        
        try:
            # 查找 __NEXT_DATA__ JSON
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if not match:
                logger.debug(f"[{source['name']}] No __NEXT_DATA__ found")
                return self._parse_html(html, source)  # 回退到 HTML 解析
            
            data = json.loads(match.group(1))
            
            # 遍历可能的路径提取文章
            articles = []
            
            # Decrypt 的结构
            props = data.get("props", {}).get("pageProps", {})
            dehydrated = props.get("dehydratedState", {}).get("queries", [])
            
            for query in dehydrated:
                state = query.get("state", {}).get("data", {})
                pages = state.get("pages", [])
                for page in pages:
                    items = page.get("data", [])
                    articles.extend(items)
            
            # 提取标题和 URL
            for article in articles[:15]:
                title = article.get("title", "") or article.get("name", "")
                slug = article.get("slug", "") or article.get("path", "")
                
                if title and len(title) > 10:
                    url = f"https://decrypt.co/{slug}" if slug else ""
                    news_items.append(NewsItem(
                        title=title,
                        source=source["name"],
                        url=url,
                        published_at=datetime.now()
                    ))
            
            logger.debug(f"[{source['name']}] Parsed {len(news_items)} articles from JSON")
            
        except Exception as e:
            logger.debug(f"[{source['name']}] JSON parse error: {e}")
            return self._parse_html(html, source)
        
        return news_items
    
    def _parse_html(self, html: str, source: Dict) -> List[NewsItem]:
        """解析 HTML 提取新闻"""
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # 找到文章容器
        articles = soup.select(source["article_selector"])[:10]  # 最多 10 条
        
        for article in articles:
            try:
                # 提取标题
                title_elem = article.select_one(source["title_selector"])
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                if not title or len(title) < 10:
                    continue
                
                # 提取链接
                link_elem = article.select_one(source["link_selector"])
                url = ""
                if link_elem and link_elem.get("href"):
                    url = link_elem["href"]
                    if url.startswith("/"):
                        # 相对路径转绝对路径
                        base = source["url"].split("/")[0:3]
                        url = "/".join(base) + url
                
                news_items.append(NewsItem(
                    title=title,
                    source=source["name"],
                    url=url,
                    published_at=datetime.now()  # 爬取时间作为发布时间
                ))
                
            except Exception as e:
                logger.debug(f"Error parsing article: {e}")
                continue
        
        logger.debug(f"[{source['name']}] Parsed {len(news_items)} articles")
        return news_items
    
    def _dedupe(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """去重"""
        unique = []
        seen_titles = set()
        
        for news in news_items:
            # 简化标题用于比较
            normalized = news.title.lower().strip()
            if normalized not in seen_titles and news.url not in self._seen_urls:
                seen_titles.add(normalized)
                self._seen_urls.add(news.url)
                unique.append(news)
        
        return unique
    
    def _calculate_impact(self, news: NewsItem):
        """计算新闻影响分数"""
        title_lower = news.title.lower()
        
        # 信号关键词匹配
        signal_matches = sum(1 for kw in SIGNAL_KEYWORDS if kw.lower() in title_lower)
        if signal_matches > 0:
            news.has_signal_keyword = True
            news.impact_score = min(signal_matches * 15, 40)
        
        # 噪音关键词扣分
        if any(kw.lower() in title_lower for kw in NOISE_KEYWORDS):
            news.impact_score = max(news.impact_score - 20, 0)
            news.has_signal_keyword = False
    
    def clear_cache(self):
        """清除已见 URL 缓存"""
        self._seen_urls.clear()


# 测试入口
if __name__ == "__main__":
    async def test():
        crawler = NewsCrawler()
        news = await crawler.fetch_latest()
        
        print(f"\n=== Fetched {len(news)} news items ===\n")
        for item in news[:10]:
            print(f"[{item.source}] {item.title}")
            print(f"  Impact: {item.impact_score}, Signal: {item.has_signal_keyword}")
            print(f"  URL: {item.url}\n")
    
    asyncio.run(test())
