"""
Session Storage Service
会话存储服务

提供 DD 会话的存储操作，支持 Redis 和内存回退
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SessionStorage:
    """
    会话存储服务

    封装会话的存储逻辑，支持 Redis 和内存回退
    """

    def __init__(self, session_store=None):
        """
        初始化存储服务

        Args:
            session_store: Redis session store 实例，None 时使用内存存储
        """
        self._session_store = session_store
        self._memory_storage: Dict[str, Any] = {}  # 内存回退存储
        self._use_redis = session_store is not None

        if self._use_redis:
            logger.info("SessionStorage initialized with Redis backend")
        else:
            logger.warning("SessionStorage initialized with in-memory backend (fallback)")

    @property
    def is_redis_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self._use_redis and self._session_store is not None

    def save(self, session_id: str, context: Any) -> bool:
        """
        保存会话

        Args:
            session_id: 会话 ID
            context: 会话上下文数据

        Returns:
            是否保存成功
        """
        if self._use_redis:
            try:
                # 将 context 转换为字典
                context_dict = context.dict() if hasattr(context, 'dict') else context
                return self._session_store.save_session(session_id, context_dict)
            except Exception as e:
                logger.error(f"Failed to save session to Redis: {e}")
                self._use_redis = False

        # 内存存储
        self._memory_storage[session_id] = context
        return True

    def get(self, session_id: str) -> Optional[Any]:
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            会话上下文，不存在时返回 None
        """
        if self._use_redis:
            try:
                return self._session_store.get_session(session_id)
            except Exception as e:
                logger.error(f"Failed to get session from Redis: {e}")
                self._use_redis = False

        # 内存存储
        return self._memory_storage.get(session_id)

    def exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_id: 会话 ID

        Returns:
            是否存在
        """
        if self._use_redis:
            try:
                return self._session_store.session_exists(session_id)
            except Exception as e:
                logger.error(f"Failed to check session existence in Redis: {e}")
                self._use_redis = False

        # 内存存储
        return session_id in self._memory_storage

    def delete(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        if self._use_redis:
            try:
                return self._session_store.delete_session(session_id)
            except Exception as e:
                logger.error(f"Failed to delete session from Redis: {e}")
                self._use_redis = False

        # 内存存储
        if session_id in self._memory_storage:
            del self._memory_storage[session_id]
            return True
        return False


# 单例实例
_session_storage: Optional[SessionStorage] = None


def get_session_storage(session_store=None) -> SessionStorage:
    """
    获取会话存储服务单例

    Args:
        session_store: 可选的 session store 实例

    Returns:
        SessionStorage 实例
    """
    global _session_storage
    if _session_storage is None:
        _session_storage = SessionStorage(session_store)
    return _session_storage


def init_session_storage(session_store) -> SessionStorage:
    """
    初始化会话存储服务

    Args:
        session_store: session store 实例

    Returns:
        SessionStorage 实例
    """
    global _session_storage
    _session_storage = SessionStorage(session_store)
    return _session_storage
