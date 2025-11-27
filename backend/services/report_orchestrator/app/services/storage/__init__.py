"""
Storage Services
存储服务层

提供统一的数据存储接口，支持 Redis 和内存回退
"""

from .report_storage import ReportStorage, get_report_storage, init_report_storage
from .session_storage import SessionStorage, get_session_storage, init_session_storage

__all__ = [
    "ReportStorage",
    "get_report_storage",
    "init_report_storage",
    "SessionStorage",
    "get_session_storage",
    "init_session_storage",
]
