"""
Cycle Search Cache - 周期内搜索结果共享

在单个分析周期内跨 Agent 共享搜索结果，避免重复调用 Tavily API。

Context Engineering P0 策略：
- Agent 1 搜索 "Bitcoin news today" → 缓存结果
- Agent 2 搜索 "BTC news today" → 语义匹配，复用结果
- 周期结束后清空缓存
"""

import hashlib
import logging
import re
from typing import Any, Dict, Optional, Callable, Set
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class CycleSearchCache:
    """
    单个分析周期内的搜索结果共享缓存
    
    特点：
    1. 精确匹配：完全相同的查询直接复用
    2. 语义相似匹配：80% 相似度的查询考虑复用
    3. 周期内有效：分析周期结束后自动清空
    4. 统计功能：跟踪命中率和节省的调用次数
    """
    
    SIMILARITY_THRESHOLD = 0.75  # 语义相似度阈值
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}  # query -> result
        self._normalized_index: Dict[str, str] = {}  # normalized_query -> original_query
        self._stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "api_calls_saved": 0
        }
        self._cycle_id: Optional[str] = None
        self._start_time: Optional[datetime] = None
    
    def start_cycle(self, cycle_id: str = None):
        """开始新的分析周期，清空缓存"""
        self._cache.clear()
        self._normalized_index.clear()
        self._cycle_id = cycle_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._start_time = datetime.now()
        logger.info(f"[CycleSearchCache] Started new cycle: {self._cycle_id}")
    
    def end_cycle(self) -> Dict[str, Any]:
        """结束分析周期，返回统计信息"""
        stats = self.get_stats()
        logger.info(
            f"[CycleSearchCache] Cycle {self._cycle_id} ended. "
            f"Hits: {stats['total_hits']}, Misses: {stats['misses']}, "
            f"API calls saved: {stats['api_calls_saved']}"
        )
        return stats
    
    def _normalize_query(self, query: str) -> str:
        """规范化查询字符串用于匹配"""
        # 转小写
        normalized = query.lower().strip()
        # 移除多余空格
        normalized = re.sub(r'\s+', ' ', normalized)
        # 移除常见停用词
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        words = normalized.split()
        words = [w for w in words if w not in stop_words]
        return ' '.join(words)
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """计算两个查询的相似度 (0-1)"""
        norm1 = self._normalize_query(query1)
        norm2 = self._normalize_query(query2)
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _find_similar_query(self, query: str) -> Optional[str]:
        """查找语义相似的已缓存查询"""
        if not self._cache:
            return None
        
        normalized = self._normalize_query(query)
        
        # 先检查规范化后的精确匹配
        if normalized in self._normalized_index:
            return self._normalized_index[normalized]
        
        # 语义相似匹配
        best_match = None
        best_score = 0
        
        for cached_query in self._cache.keys():
            score = self._calculate_similarity(query, cached_query)
            if score > best_score and score >= self.SIMILARITY_THRESHOLD:
                best_match = cached_query
                best_score = score
        
        if best_match:
            logger.debug(
                f"[CycleSearchCache] Semantic match: '{query[:50]}...' ≈ '{best_match[:50]}...' "
                f"(similarity: {best_score:.2f})"
            )
        
        return best_match
    
    async def get_or_search(
        self, 
        query: str, 
        search_fn: Callable,
        **search_params
    ) -> Dict[str, Any]:
        """
        获取缓存结果或执行搜索
        
        Args:
            query: 搜索查询
            search_fn: 搜索函数 (async)
            **search_params: 搜索参数
        
        Returns:
            搜索结果 (来自缓存或新搜索)
        """
        # 1. 精确匹配
        if query in self._cache:
            self._stats["exact_hits"] += 1
            self._stats["api_calls_saved"] += 1
            logger.info(f"[CycleSearchCache] EXACT HIT: '{query[:50]}...'")
            result = self._cache[query].copy()
            result["_cache_status"] = "exact_hit"
            return result
        
        # 2. 语义相似匹配
        similar_query = self._find_similar_query(query)
        if similar_query:
            self._stats["semantic_hits"] += 1
            self._stats["api_calls_saved"] += 1
            logger.info(f"[CycleSearchCache] SEMANTIC HIT: '{query[:50]}...' → reusing '{similar_query[:50]}...'")
            result = self._cache[similar_query].copy()
            result["_cache_status"] = "semantic_hit"
            result["_original_query"] = similar_query
            return result
        
        # 3. 缓存未命中，执行搜索
        self._stats["misses"] += 1
        logger.info(f"[CycleSearchCache] MISS: '{query[:50]}...' - calling API")
        
        result = await search_fn(query, **search_params)
        
        # 4. 缓存结果
        if result and isinstance(result, dict):
            result["_cached_at"] = datetime.now().isoformat()
            result["_cache_status"] = "fresh"
            self._cache[query] = result
            self._normalized_index[self._normalize_query(query)] = query
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_hits = self._stats["exact_hits"] + self._stats["semantic_hits"]
        total_requests = total_hits + self._stats["misses"]
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cycle_id": self._cycle_id,
            "exact_hits": self._stats["exact_hits"],
            "semantic_hits": self._stats["semantic_hits"],
            "total_hits": total_hits,
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "api_calls_saved": self._stats["api_calls_saved"],
            "cached_queries": len(self._cache),
            "duration": str(datetime.now() - self._start_time) if self._start_time else None
        }
    
    def get_cached_queries(self) -> Set[str]:
        """获取所有已缓存的查询"""
        return set(self._cache.keys())


# 全局实例 (周期内共享)
_cycle_search_cache: Optional[CycleSearchCache] = None


def get_cycle_search_cache() -> CycleSearchCache:
    """获取周期搜索缓存的全局实例"""
    global _cycle_search_cache
    if _cycle_search_cache is None:
        _cycle_search_cache = CycleSearchCache()
    return _cycle_search_cache


def reset_cycle_search_cache():
    """重置全局缓存实例 (用于测试)"""
    global _cycle_search_cache
    _cycle_search_cache = None
