"""
API Routers
API 路由模块

Phase 4: 组织和管理所有 API 端点 (完整迁移)
"""

from fastapi import APIRouter

# 创建主路由
api_router = APIRouter()

# 导入并注册子路由
from .health import router as health_router
from .reports import router as reports_router
from .dashboard import router as dashboard_router
from .knowledge import router as knowledge_router
from .roundtable import router as roundtable_router
from .files import router as files_router
from .analysis import router as analysis_router
from .export import router as export_router, set_get_report_func
from .dd_workflow import router as dd_workflow_router, set_session_funcs

# 注册路由
api_router.include_router(health_router)
api_router.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
api_router.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
api_router.include_router(knowledge_router, prefix="/api/knowledge", tags=["Knowledge Base"])
api_router.include_router(roundtable_router, prefix="/api/roundtable", tags=["Roundtable"])
api_router.include_router(files_router, prefix="/api", tags=["File Upload"])
api_router.include_router(analysis_router, prefix="/api/v2/analysis", tags=["Analysis V2"])
api_router.include_router(export_router, prefix="/api/reports", tags=["Report Export"])
api_router.include_router(dd_workflow_router, prefix="/api/dd", tags=["DD Workflow"])

__all__ = [
    "api_router",
    "health_router",
    "reports_router",
    "dashboard_router",
    "knowledge_router",
    "roundtable_router",
    "files_router",
    "analysis_router",
    "export_router",
    "dd_workflow_router",
    "set_get_report_func",
    "set_session_funcs"
]
