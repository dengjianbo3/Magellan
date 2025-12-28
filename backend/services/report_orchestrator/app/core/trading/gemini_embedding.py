"""
Gemini Embedding Service

使用 Gemini Embedding API 进行语义相似度计算。
用于 CycleSearchCache 的语义匹配功能。

API 文档: https://ai.google.dev/gemini-api/docs/embeddings
"""

import os
import logging
import numpy as np
from typing import List, Dict, Optional, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Embedding 配置
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_TASK_TYPE = "SEMANTIC_SIMILARITY"
EMBEDDING_CACHE_SIZE = 100  # 缓存最近 100 个查询的 embedding


class GeminiEmbeddingService:
    """
    Gemini Embedding 服务
    
    使用 Google Gemini API 生成文本 embedding，
    用于计算查询之间的语义相似度。
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Embedding 服务
        
        Args:
            api_key: Gemini API Key，默认从环境变量获取
                     (尝试 GOOGLE_API_KEY 或 GEMINI_API_KEY)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self._client = None
        self._embedding_cache: Dict[str, List[float]] = {}
        self._stats = {
            "embed_calls": 0,
            "cache_hits": 0,
            "similarity_calcs": 0
        }
        
        if not self.api_key:
            logger.warning("[GeminiEmbedding] No API key found. Semantic matching will fallback to string similarity.")
    
    @property
    def client(self):
        """Lazy initialize Gemini client"""
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("[GeminiEmbedding] Client initialized successfully")
            except ImportError:
                logger.error("[GeminiEmbedding] google-genai package not installed. Run: pip install google-genai")
                raise
            except Exception as e:
                logger.error(f"[GeminiEmbedding] Failed to initialize client: {e}")
                raise
        return self._client
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取文本的 embedding 向量
        
        Args:
            text: 输入文本
            
        Returns:
            embedding 向量 (List[float]) 或 None
        """
        # 检查缓存
        cache_key = text[:200]  # 使用前 200 字符作为 key
        if cache_key in self._embedding_cache:
            self._stats["cache_hits"] += 1
            return self._embedding_cache[cache_key]
        
        if not self.api_key:
            return None
        
        try:
            from google.genai import types
            
            result = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(task_type=EMBEDDING_TASK_TYPE)
            )
            
            self._stats["embed_calls"] += 1
            
            if result.embeddings:
                embedding = list(result.embeddings[0].values)
                
                # 缓存结果（限制大小）
                if len(self._embedding_cache) >= EMBEDDING_CACHE_SIZE:
                    # 移除最早的条目
                    oldest_key = next(iter(self._embedding_cache))
                    del self._embedding_cache[oldest_key]
                self._embedding_cache[cache_key] = embedding
                
                return embedding
            
            return None
            
        except Exception as e:
            logger.warning(f"[GeminiEmbedding] Failed to get embedding: {e}")
            return None
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量获取 embedding
        
        Args:
            texts: 文本列表
            
        Returns:
            embedding 向量列表
        """
        if not self.api_key:
            return [None] * len(texts)
        
        try:
            from google.genai import types
            
            result = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type=EMBEDDING_TASK_TYPE)
            )
            
            self._stats["embed_calls"] += 1
            
            embeddings = []
            for i, emb in enumerate(result.embeddings):
                embedding = list(emb.values)
                embeddings.append(embedding)
                
                # 缓存
                cache_key = texts[i][:200]
                self._embedding_cache[cache_key] = embedding
            
            return embeddings
            
        except Exception as e:
            logger.warning(f"[GeminiEmbedding] Batch embedding failed: {e}")
            return [None] * len(texts)
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1, vec2: 向量
            
        Returns:
            相似度 (0-1)
        """
        try:
            arr1 = np.array(vec1)
            arr2 = np.array(vec2)
            
            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            self._stats["similarity_calcs"] += 1
            return float(dot_product / (norm1 * norm2))
            
        except Exception as e:
            logger.warning(f"[GeminiEmbedding] Cosine similarity error: {e}")
            return 0.0
    
    async def semantic_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的语义相似度
        
        Args:
            text1, text2: 输入文本
            
        Returns:
            相似度 (0-1)
        """
        emb1 = await self.get_embedding(text1)
        emb2 = await self.get_embedding(text2)
        
        if emb1 is None or emb2 is None:
            return 0.0
        
        return self.cosine_similarity(emb1, emb2)
    
    async def find_most_similar(
        self, 
        query: str, 
        candidates: List[str],
        threshold: float = 0.75
    ) -> Optional[tuple]:
        """
        找到与 query 最相似的候选项
        
        Args:
            query: 查询文本
            candidates: 候选文本列表
            threshold: 相似度阈值
            
        Returns:
            (最相似文本, 相似度) 或 None
        """
        if not candidates:
            return None
        
        query_emb = await self.get_embedding(query)
        if query_emb is None:
            return None
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            cand_emb = await self.get_embedding(candidate)
            if cand_emb is None:
                continue
            
            score = self.cosine_similarity(query_emb, cand_emb)
            if score > best_score and score >= threshold:
                best_match = candidate
                best_score = score
        
        if best_match:
            logger.debug(f"[GeminiEmbedding] Best match: '{query[:30]}...' → '{best_match[:30]}...' (sim={best_score:.3f})")
            return (best_match, best_score)
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "cache_size": len(self._embedding_cache),
            "has_api_key": bool(self.api_key)
        }
    
    def clear_cache(self):
        """清空 embedding 缓存"""
        self._embedding_cache.clear()


# 全局单例
_embedding_service: Optional[GeminiEmbeddingService] = None


def get_embedding_service() -> GeminiEmbeddingService:
    """获取全局 embedding 服务"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = GeminiEmbeddingService()
    return _embedding_service


def reset_embedding_service():
    """重置全局服务（用于测试）"""
    global _embedding_service
    _embedding_service = None
