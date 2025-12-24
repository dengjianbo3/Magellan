"""
Search Cache - 智能搜索缓存
基于Redis的搜索结果缓存，动态TTL策略

根据 priority 和查询类型决定缓存时间：
- realtime: 不缓存
- critical: 1小时
- normal: 根据查询内容 2-24小时
"""
import json
import hashlib
import logging
import os
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchCache:
    """
    搜索结果缓存
    
    使用Redis存储，支持：
    1. 动态TTL（根据priority和查询类型）
    2. 缓存命中率统计
    3. 查询指纹生成
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Args:
            redis_url: Redis连接URL，默认从环境变量获取
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379")
        self._redis = None
        self._stats = {"hits": 0, "misses": 0}
    
    @property
    def redis(self):
        """Lazy load Redis client"""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis
    
    def _generate_key(self, query: str, priority: str) -> str:
        """生成缓存key"""
        # 规范化查询
        normalized = query.lower().strip()
        # 生成hash
        query_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        return f"search_cache:{priority}:{query_hash}"
    
    def _get_ttl(self, query: str, priority: str) -> int:
        """
        根据priority和查询内容决定TTL
        
        Returns:
            TTL秒数，0表示不缓存
        """
        priority = priority.lower()
        query_lower = query.lower()
        
        # realtime 不缓存
        if priority == "realtime":
            return 0
        
        # critical 1小时
        if priority == "critical":
            return 3600
        
        # normal - 根据查询类型动态决定
        # 实时关键词 - 不缓存
        realtime_keywords = [
            "price", "股价", "今日", "breaking", "btc", "eth", 
            "latest", "最新", "刚刚", "now", "live"
        ]
        if any(kw in query_lower for kw in realtime_keywords):
            return 0
        
        # 近期事件 - 2小时
        recent_keywords = ["recent", "最近", "this week", "yesterday", "本周"]
        if any(kw in query_lower for kw in recent_keywords):
            return 7200
        
        # 新闻类 - 4小时
        news_keywords = ["news", "新闻", "announcement", "公告"]
        if any(kw in query_lower for kw in news_keywords):
            return 14400
        
        # 公司/人物背景 - 24小时
        background_keywords = [
            "company", "founder", "ceo", "history", "background",
            "公司", "创始人", "团队", "历史", "简介"
        ]
        if any(kw in query_lower for kw in background_keywords):
            return 86400
        
        # 技术/专利 - 7天
        static_keywords = ["patent", "专利", "技术架构", "market size", "市场规模"]
        if any(kw in query_lower for kw in static_keywords):
            return 604800
        
        # 默认 - 6小时
        return 21600
    
    async def get(self, query: str, priority: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取搜索结果
        
        Args:
            query: 搜索查询
            priority: 优先级
        
        Returns:
            缓存的结果，不存在返回None
        """
        try:
            ttl = self._get_ttl(query, priority)
            if ttl == 0:
                return None  # 不该使用缓存
            
            key = self._generate_key(query, priority)
            cached = await self.redis.get(key)
            
            if cached:
                self._stats["hits"] += 1
                logger.debug(f"[SearchCache] HIT: {key}")
                return json.loads(cached)
            
            self._stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.warning(f"[SearchCache] Get failed: {e}")
            return None
    
    async def set(
        self, 
        query: str, 
        priority: str, 
        result: Dict[str, Any]
    ) -> bool:
        """
        缓存搜索结果
        
        Args:
            query: 搜索查询
            priority: 优先级
            result: 搜索结果
        
        Returns:
            是否成功
        """
        try:
            ttl = self._get_ttl(query, priority)
            if ttl == 0:
                return False  # 不缓存
            
            key = self._generate_key(query, priority)
            
            # 添加缓存元数据
            result_with_meta = {
                **result,
                "_cached_at": datetime.now().isoformat(),
                "_cache_ttl": ttl
            }
            
            await self.redis.setex(
                key,
                ttl,
                json.dumps(result_with_meta, ensure_ascii=False, default=str)
            )
            
            logger.debug(f"[SearchCache] SET: {key} TTL={ttl}s")
            return True
            
        except Exception as e:
            logger.warning(f"[SearchCache] Set failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total
        }
    
    async def clear_pattern(self, pattern: str = "search_cache:*") -> int:
        """清除匹配的缓存"""
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis.delete(*keys)
            
            logger.info(f"[SearchCache] Cleared {len(keys)} keys matching '{pattern}'")
            return len(keys)
            
        except Exception as e:
            logger.error(f"[SearchCache] Clear failed: {e}")
            return 0
