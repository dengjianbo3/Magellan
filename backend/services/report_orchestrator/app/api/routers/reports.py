"""
Reports Router
报告管理路由
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends

from ...services.storage import get_report_storage, ReportStorage

router = APIRouter()
logger = logging.getLogger(__name__)


def get_storage() -> ReportStorage:
    """依赖注入：获取报告存储服务"""
    return get_report_storage()


@router.post("")
async def save_report(
    report_data: Dict[str, Any],
    storage: ReportStorage = Depends(get_storage)
):
    """
    保存 DD 分析报告

    Request body:
    {
        "session_id": "dd_...",
        "project_name": "...",
        "company_name": "...",
        "analysis_type": "...",
        "preliminary_im": {...},
        "steps": [...],
        "created_at": "...",
        "status": "completed"
    }
    """
    # Generate report ID
    report_id = f"report_{uuid.uuid4().hex[:12]}"

    # Add metadata
    saved_report = {
        "id": report_id,
        "session_id": report_data.get("session_id"),
        "project_name": report_data.get("project_name"),
        "company_name": report_data.get("company_name"),
        "analysis_type": report_data.get("analysis_type", "due-diligence"),
        "preliminary_im": report_data.get("preliminary_im"),
        "steps": report_data.get("steps", []),
        "status": report_data.get("status", "completed"),
        "created_at": report_data.get("created_at", datetime.now().isoformat()),
        "saved_at": datetime.now().isoformat()
    }

    # Store report
    storage.save(report_id, saved_report)

    logger.info(f"Saved report {report_id} for {saved_report['company_name']}")

    return {
        "success": True,
        "report_id": report_id,
        "message": "报告已成功保存"
    }


@router.get("")
async def get_reports(storage: ReportStorage = Depends(get_storage)):
    """获取所有保存的报告"""
    all_reports = storage.get_all(limit=100)

    # Sort by created_at (newest first)
    sorted_reports = sorted(
        all_reports,
        key=lambda r: r.get("created_at", ""),
        reverse=True
    )

    return {
        "success": True,
        "count": len(sorted_reports),
        "reports": sorted_reports
    }


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    storage: ReportStorage = Depends(get_storage)
):
    """获取指定报告"""
    report = storage.get(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    return {
        "success": True,
        "report": report
    }


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    storage: ReportStorage = Depends(get_storage)
):
    """删除指定报告"""
    report = storage.get(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    success = storage.delete(report_id)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete report {report_id}")

    logger.info(f"Deleted report {report_id} for {report.get('company_name')}")

    return {
        "success": True,
        "message": "报告已成功删除",
        "deleted_report_id": report_id
    }
