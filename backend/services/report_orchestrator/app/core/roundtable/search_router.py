"""
Search Router - 统一搜索路由器 (Plan C 重构版)

三层搜索架构:
- normal:   DuckDuckGo (免费) → Serper → Tavily
- critical: Serper (高性价比) → Tavily
- realtime: Tavily (最佳质量，不缓存)
"""
import logging
from typing import Any, Dict, Optional, List
from enum import Enum

from ..auth import get_current_user_id

logger = logging.getLogger(__name__)


class SearchPriority(Enum):
    """搜索优先级"""
    REALTIME = "realtime"   # 实时数据：股价、突发新闻 → Tavily
    CRITICAL = "critical"   # 关键决策：投资分析核心 → Serper
    NORMAL = "normal"       # 一般信息：公司背景 → DuckDuckGo


class SearchRouter:
    """
    搜索路由器 (Plan C 架构)
    
    三层路由:
    - normal → DuckDuckGo → Serper → Tavily
    - critical → Serper → Tavily
    - realtime → Tavily only
    """
    
    def __init__(self):
        self._tavily_tool = None
        self._serper_tool = None
        self._ddg_tool = None
        self._cache = None
        self._dedup = None
    
    @property
    def tavily_tool(self):
        """Lazy load Tavily tool"""
        if self._tavily_tool is None:
            from .mcp_tools import TavilySearchTool
            self._tavily_tool = TavilySearchTool()
        return self._tavily_tool
    
    @property
    def serper_tool(self):
        """Lazy load Serper tool"""
        if self._serper_tool is None:
            from .serper_tool import SerperSearchTool
            self._serper_tool = SerperSearchTool()
        return self._serper_tool
    
    @property
    def ddg_tool(self):
        """Lazy load DuckDuckGo tool"""
        if self._ddg_tool is None:
            from .duckduckgo_tool import DuckDuckGoSearchTool
            self._ddg_tool = DuckDuckGoSearchTool()
        return self._ddg_tool
    
    @property
    def cache(self):
        """Lazy load SearchCache"""
        if self._cache is None:
            try:
                from .search_cache import SearchCache
                self._cache = SearchCache()
            except Exception as e:
                logger.warning(f"SearchCache not available: {e}")
                self._cache = None
        return self._cache
    
    @property
    def dedup(self):
        """Lazy load SearchDedup"""
        if self._dedup is None:
            try:
                from .search_dedup import SearchDedup
                self._dedup = SearchDedup()
            except Exception as e:
                logger.warning(f"SearchDedup not available: {e}")
                self._dedup = None
        return self._dedup
    
    def _get_priority(self, priority_str: Optional[str]) -> SearchPriority:
        """解析优先级字符串"""
        if priority_str is None:
            return SearchPriority.NORMAL
        
        priority_str = priority_str.lower().strip()
        try:
            return SearchPriority(priority_str)
        except ValueError:
            return SearchPriority.NORMAL

    def _normalize_results(self, results: Any) -> List[Dict[str, Any]]:
        """Normalize heterogeneous provider payloads into one stable result schema."""
        if not isinstance(results, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict):
                continue

            title = item.get("title") or ""
            url = item.get("url") or item.get("href") or item.get("link") or ""
            content = item.get("content") or item.get("body") or item.get("snippet") or ""
            published_date = item.get("published_date") or item.get("date")
            score = item.get("score")
            if not isinstance(score, (int, float)):
                score = 0.0

            normalized.append({
                "title": title,
                "url": url,
                "content": content,
                "published_date": published_date,
                "score": float(score),
                # Backward-compatible aliases for existing callers/tools.
                "body": content,
                "date": published_date,
            })
        return normalized

    def _normalize_result_contract(self, query: str, result: Any) -> Dict[str, Any]:
        """Ensure router output keeps one contract regardless of provider/cache age."""
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": "invalid_result_type",
                "summary": f"Search failed for '{query}': invalid provider result",
                "results": [],
                "query": query,
            }

        normalized = dict(result)
        normalized_results = self._normalize_results(normalized.get("results", []))
        normalized["results"] = normalized_results
        normalized["query"] = normalized.get("query") or query

        if normalized.get("success") and not normalized.get("summary"):
            normalized["summary"] = f"Found {len(normalized_results)} results for '{query}'."

        return normalized

    def _build_search_context(self, **kwargs) -> Dict[str, Any]:
        """Context partition for cache/dedup so different intents do not contaminate each other."""
        user_scope = kwargs.get("user_id") or get_current_user_id()
        return {
            "topic": kwargs.get("topic", "general"),
            "time_range": kwargs.get("time_range"),
            "days": kwargs.get("days"),
            "max_results": kwargs.get("max_results", 5),
            "user_scope": str(user_scope or ""),
        }
    
    async def search(
        self,
        query: str,
        priority: str = "normal",
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        统一搜索接口 (Plan C 三层路由)
        
        路由规则:
        - normal:   DDG → Serper → Tavily
        - critical: Serper → Tavily
        - realtime: Tavily only (不缓存)
        """
        prio = self._get_priority(priority)
        search_context = self._build_search_context(**kwargs)
        
        logger.info(f"[SearchRouter] Query: '{query[:50]}...' Priority: {prio.value}")
        
        # 0. 会话级语义去重
        if session_id and self.dedup:
            deduped = self.dedup.find_similar(query, session_id, context=search_context)
            if deduped:
                logger.info(f"[SearchRouter] Dedup HIT for '{query[:30]}...'")
                return self._normalize_result_contract(query, deduped)
        
        # 1. 检查缓存（realtime不查缓存）
        if prio != SearchPriority.REALTIME and self.cache:
            cached = await self.cache.get(query, priority, search_params=search_context)
            if cached:
                logger.info(f"[SearchRouter] Cache HIT for '{query[:30]}...'")
                cached["from_cache"] = True
                return self._normalize_result_contract(query, cached)
        
        # 2. 根据优先级路由
        result = None
        source = None
        
        if prio == SearchPriority.REALTIME:
            # realtime → Tavily only (最高质量)
            result = await self._search_with_tavily(query, **kwargs)
            source = "tavily"
            
        elif prio == SearchPriority.CRITICAL:
            # critical → Serper → Tavily
            result = await self._search_with_serper(query, **kwargs)
            source = "serper"
            
            if not result.get("success") or result.get("fallback_needed"):
                logger.warning(f"[SearchRouter] Serper failed, falling back to Tavily")
                result = await self._search_with_tavily(query, **kwargs)
                source = "tavily_fallback"
                
        else:  # NORMAL
            # normal → DDG → Serper → Tavily
            result = await self._search_with_ddg(query, **kwargs)
            source = "duckduckgo"
            
            if not result.get("success") or result.get("fallback_needed"):
                logger.warning(f"[SearchRouter] DuckDuckGo failed, trying Serper...")
                result = await self._search_with_serper(query, **kwargs)
                source = "serper_fallback"
                
                if not result.get("success") or result.get("fallback_needed"):
                    logger.warning(f"[SearchRouter] Serper failed, falling back to Tavily")
                    result = await self._search_with_tavily(query, **kwargs)
                    source = "tavily_fallback"

        result = self._normalize_result_contract(query, result)
        result["routed_source"] = source
        result["priority"] = prio.value
        
        # 3. 写入缓存（realtime不缓存）
        if prio != SearchPriority.REALTIME and self.cache and result.get("success"):
            await self.cache.set(query, priority, result, search_params=search_context)
            logger.info(f"[SearchRouter] Cached result for '{query[:30]}...'")
        
        # 4. 添加到会话去重缓存
        if session_id and self.dedup and result.get("success"):
            self.dedup.add(query, session_id, result, context=search_context)
        
        return result
    
    async def _search_with_tavily(self, query: str, **kwargs) -> Dict[str, Any]:
        """使用Tavily搜索 (最高质量，通过MCP)"""
        try:
            result = await self.tavily_tool.execute(query, **kwargs)
            return result
        except Exception as e:
            logger.error(f"[SearchRouter] Tavily search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"Tavily search failed: {e}"
            }
    
    async def _search_with_serper(self, query: str, **kwargs) -> Dict[str, Any]:
        """使用Serper搜索 (Google结果，高性价比)"""
        try:
            serper_kwargs = {
                "max_results": kwargs.get("max_results", 5),
                "search_type": "news" if kwargs.get("topic") == "news" else "text"
            }
            result = await self.serper_tool.execute(query, **serper_kwargs)
            return result
        except Exception as e:
            logger.error(f"[SearchRouter] Serper search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"Serper search failed: {e}",
                "fallback_needed": True
            }
    
    async def _search_with_ddg(self, query: str, **kwargs) -> Dict[str, Any]:
        """使用DuckDuckGo搜索 (免费)"""
        try:
            ddg_kwargs = {
                "max_results": kwargs.get("max_results", 5),
                "search_type": "news" if kwargs.get("topic") == "news" else "text"
            }
            
            time_range = kwargs.get("time_range")
            if time_range:
                time_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
                ddg_kwargs["time_range"] = time_map.get(time_range, time_range)
            
            result = await self.ddg_tool.execute(query, **ddg_kwargs)
            return result
        except Exception as e:
            logger.error(f"[SearchRouter] DuckDuckGo search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"DuckDuckGo search failed: {e}",
                "fallback_needed": True
            }


# 全局路由器实例
_router: Optional[SearchRouter] = None

def get_search_router() -> SearchRouter:
    """获取全局SearchRouter实例"""
    global _router
    if _router is None:
        _router = SearchRouter()
    return _router


async def unified_search(
    query: str,
    priority: str = "normal",
    **kwargs
) -> Dict[str, Any]:
    """
    统一搜索函数（便捷接口）
    
    Args:
        query: 搜索查询
        priority: "realtime" / "critical" / "normal"
        **kwargs: 其他参数
    
    Returns:
        搜索结果
    """
    router = get_search_router()
    return await router.search(query, priority, **kwargs)
