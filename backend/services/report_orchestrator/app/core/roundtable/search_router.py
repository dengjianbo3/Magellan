"""
Search Router - 统一搜索路由器
根据 priority 参数智能路由到不同搜索源

Priority:
- realtime: 实时数据，直接Tavily，不缓存
- critical: 关键数据，Tavily + 1小时缓存
- normal: 一般信息，DuckDuckGo + 动态TTL缓存
"""
import logging
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SearchPriority(Enum):
    """搜索优先级"""
    REALTIME = "realtime"   # 实时数据：股价、突发新闻
    CRITICAL = "critical"   # 关键决策：投资分析核心数据
    NORMAL = "normal"       # 一般信息：公司背景、历史


class SearchRouter:
    """
    搜索路由器
    
    功能：
    1. 根据 priority 参数路由到合适的搜索源
    2. 管理搜索缓存（集成 SearchCache）
    3. 处理 Fallback 逻辑
    """
    
    def __init__(self):
        self._tavily_tool = None
        self._ddg_tool = None
        self._cache = None
    
    @property
    def tavily_tool(self):
        """Lazy load Tavily tool"""
        if self._tavily_tool is None:
            from .mcp_tools import TavilySearchTool
            self._tavily_tool = TavilySearchTool()
        return self._tavily_tool
    
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
    
    def _get_priority(self, priority_str: Optional[str]) -> SearchPriority:
        """解析优先级字符串"""
        if priority_str is None:
            return SearchPriority.NORMAL
        
        priority_str = priority_str.lower().strip()
        try:
            return SearchPriority(priority_str)
        except ValueError:
            return SearchPriority.NORMAL
    
    async def search(
        self,
        query: str,
        priority: str = "normal",
        **kwargs
    ) -> Dict[str, Any]:
        """
        统一搜索接口
        
        Args:
            query: 搜索查询
            priority: 优先级 ("realtime", "critical", "normal")
            **kwargs: 其他搜索参数（max_results, topic, time_range等）
        
        Returns:
            搜索结果
        """
        prio = self._get_priority(priority)
        
        logger.info(f"[SearchRouter] Query: '{query[:50]}...' Priority: {prio.value}")
        
        # 1. 检查缓存（realtime不查缓存）
        if prio != SearchPriority.REALTIME and self.cache:
            cached = await self.cache.get(query, priority)
            if cached:
                logger.info(f"[SearchRouter] Cache HIT for '{query[:30]}...'")
                cached["from_cache"] = True
                return cached
        
        # 2. 根据优先级路由
        if prio in [SearchPriority.REALTIME, SearchPriority.CRITICAL]:
            # 高优先级 -> Tavily
            result = await self._search_with_tavily(query, **kwargs)
            source = "tavily"
        else:
            # 普通优先级 -> DuckDuckGo (失败则 Fallback Tavily)
            result = await self._search_with_ddg(query, **kwargs)
            source = "duckduckgo"
            
            # Fallback to Tavily if DuckDuckGo fails
            if not result.get("success") or result.get("fallback_needed"):
                logger.warning(f"[SearchRouter] DuckDuckGo failed, falling back to Tavily")
                result = await self._search_with_tavily(query, **kwargs)
                source = "tavily_fallback"
        
        result["routed_source"] = source
        result["priority"] = prio.value
        
        # 3. 写入缓存（realtime不缓存）
        if prio != SearchPriority.REALTIME and self.cache and result.get("success"):
            await self.cache.set(query, priority, result)
            logger.info(f"[SearchRouter] Cached result for '{query[:30]}...'")
        
        return result
    
    async def _search_with_tavily(self, query: str, **kwargs) -> Dict[str, Any]:
        """使用Tavily搜索"""
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
    
    async def _search_with_ddg(self, query: str, **kwargs) -> Dict[str, Any]:
        """使用DuckDuckGo搜索"""
        try:
            # 转换参数格式
            ddg_kwargs = {
                "max_results": kwargs.get("max_results", 5),
                "search_type": "news" if kwargs.get("topic") == "news" else "text"
            }
            
            # 时间范围转换
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
