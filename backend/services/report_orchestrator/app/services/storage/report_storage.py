"""
Report Storage Service
报告存储服务

提供报告的 CRUD 操作，支持 Redis 和内存回退
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ReportStorage:
    """
    报告存储服务

    封装报告的存储逻辑，支持 Redis 和内存回退
    """

    def __init__(self, session_store=None):
        """
        初始化存储服务

        Args:
            session_store: Redis session store 实例，None 时使用内存存储
        """
        self._session_store = session_store
        self._memory_storage: List[Dict[str, Any]] = []  # 内存回退存储
        self._use_redis = session_store is not None

        if self._use_redis:
            logger.info("ReportStorage initialized with Redis backend")
        else:
            logger.warning("ReportStorage initialized with in-memory backend (fallback)")

    @property
    def is_redis_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self._use_redis and self._session_store is not None

    def save(self, report_id: str, report_data: Dict[str, Any], ttl_days: int = 365) -> bool:
        """
        保存报告

        Args:
            report_id: 报告 ID
            report_data: 报告数据
            ttl_days: 数据保留天数

        Returns:
            是否保存成功
        """
        if self._use_redis:
            try:
                return self._session_store.save_report(report_id, report_data, ttl_days=ttl_days)
            except Exception as e:
                logger.error(f"Failed to save report to Redis: {e}")
                # Fall through to memory storage
                self._use_redis = False

        # 内存存储
        # 先检查是否已存在，如果存在则更新
        existing_index = next(
            (i for i, r in enumerate(self._memory_storage) if r.get("id") == report_id),
            None
        )
        if existing_index is not None:
            self._memory_storage[existing_index] = report_data
        else:
            self._memory_storage.append(report_data)
        return True

    def get(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个报告

        Args:
            report_id: 报告 ID

        Returns:
            报告数据，不存在时返回 None
        """
        if self._use_redis:
            try:
                return self._session_store.get_report(report_id)
            except Exception as e:
                logger.error(f"Failed to get report from Redis: {e}")
                self._use_redis = False

        # 内存存储
        return next((r for r in self._memory_storage if r.get("id") == report_id), None)

    def get_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有报告

        Args:
            limit: 最大返回数量

        Returns:
            报告列表
        """
        if self._use_redis:
            try:
                return self._session_store.get_all_reports(limit=limit)
            except Exception as e:
                logger.error(f"Failed to get all reports from Redis: {e}")
                self._use_redis = False

        # 内存存储
        return self._memory_storage[:limit]

    def delete(self, report_id: str) -> bool:
        """
        删除报告

        Args:
            report_id: 报告 ID

        Returns:
            是否删除成功
        """
        if self._use_redis:
            try:
                return self._session_store.delete_report(report_id)
            except Exception as e:
                logger.error(f"Failed to delete report from Redis: {e}")
                self._use_redis = False

        # 内存存储
        report_index = next(
            (i for i, r in enumerate(self._memory_storage) if r.get("id") == report_id),
            None
        )
        if report_index is not None:
            self._memory_storage.pop(report_index)
            return True
        return False

    def count(self) -> int:
        """获取报告总数"""
        if self._use_redis:
            try:
                return len(self._session_store.get_all_reports(limit=10000))
            except Exception:
                pass
        return len(self._memory_storage)


# 单例实例
_report_storage: Optional[ReportStorage] = None


def get_report_storage(session_store=None) -> ReportStorage:
    """
    获取报告存储服务单例

    Args:
        session_store: 可选的 session store 实例

    Returns:
        ReportStorage 实例
    """
    global _report_storage
    if _report_storage is None:
        _report_storage = ReportStorage(session_store)
    return _report_storage


def init_report_storage(session_store) -> ReportStorage:
    """
    初始化报告存储服务

    Args:
        session_store: session store 实例

    Returns:
        ReportStorage 实例
    """
    global _report_storage
    _report_storage = ReportStorage(session_store)
    return _report_storage
