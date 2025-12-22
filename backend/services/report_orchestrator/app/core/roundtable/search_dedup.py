"""
Search Deduplication - 会话级语义去重
同一会话内相似查询复用结果，减少重复搜索

策略：
- 使用简单字符串相似度（无需安装额外模型）
- 相似度>85%且5分钟内 → 复用结果
- 每个会话独立缓存
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class SearchDedup:
    """
    会话级搜索去重
    
    使用字符串相似度检测相似查询，复用近期结果
    """
    
    def __init__(
        self, 
        similarity_threshold: float = 0.85,
        dedup_window_minutes: int = 5
    ):
        """
        Args:
            similarity_threshold: 相似度阈值 (0-1)
            dedup_window_minutes: 去重时间窗口（分钟）
        """
        self.similarity_threshold = similarity_threshold
        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        
        # 会话缓存: session_id -> [(query, result, timestamp), ...]
        self._session_cache: Dict[str, List[tuple]] = {}
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """计算两个查询的相似度"""
        # 规范化
        q1 = query1.lower().strip()
        q2 = query2.lower().strip()
        
        # 使用 SequenceMatcher 计算相似度
        return SequenceMatcher(None, q1, q2).ratio()
    
    def _clean_expired(self, session_id: str):
        """清理过期的缓存条目"""
        if session_id not in self._session_cache:
            return
        
        now = datetime.now()
        self._session_cache[session_id] = [
            (q, r, t) for q, r, t in self._session_cache[session_id]
            if now - t < self.dedup_window
        ]
    
    def find_similar(
        self, 
        query: str, 
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        查找会话中的相似查询结果
        
        Args:
            query: 当前查询
            session_id: 会话ID
        
        Returns:
            相似查询的结果，不存在返回None
        """
        # 清理过期
        self._clean_expired(session_id)
        
        if session_id not in self._session_cache:
            return None
        
        for cached_query, result, timestamp in self._session_cache[session_id]:
            similarity = self._calculate_similarity(query, cached_query)
            
            if similarity >= self.similarity_threshold:
                logger.info(
                    f"[SearchDedup] Found similar query ({similarity:.2%}): "
                    f"'{query[:30]}...' ~ '{cached_query[:30]}...'"
                )
                # 标记为复用结果
                return {
                    **result,
                    "_dedup": True,
                    "_dedup_original_query": cached_query,
                    "_dedup_similarity": similarity
                }
        
        return None
    
    def add(
        self, 
        query: str, 
        session_id: str, 
        result: Dict[str, Any]
    ):
        """
        添加查询结果到会话缓存
        
        Args:
            query: 查询
            session_id: 会话ID
            result: 搜索结果
        """
        if session_id not in self._session_cache:
            self._session_cache[session_id] = []
        
        self._session_cache[session_id].append(
            (query, result, datetime.now())
        )
        
        # 限制每个会话最多50条记录
        if len(self._session_cache[session_id]) > 50:
            self._session_cache[session_id] = self._session_cache[session_id][-50:]
        
        logger.debug(f"[SearchDedup] Added to session cache: '{query[:30]}...'")
    
    def clear_session(self, session_id: str):
        """清除会话缓存"""
        if session_id in self._session_cache:
            del self._session_cache[session_id]
            logger.info(f"[SearchDedup] Cleared session: {session_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_sessions = len(self._session_cache)
        total_entries = sum(len(v) for v in self._session_cache.values())
        
        return {
            "active_sessions": total_sessions,
            "total_cached_entries": total_entries,
            "similarity_threshold": self.similarity_threshold,
            "dedup_window_minutes": self.dedup_window.total_seconds() / 60
        }


# 全局去重器实例
_dedup: Optional[SearchDedup] = None

def get_search_dedup() -> SearchDedup:
    """获取全局SearchDedup实例"""
    global _dedup
    if _dedup is None:
        _dedup = SearchDedup()
    return _dedup
