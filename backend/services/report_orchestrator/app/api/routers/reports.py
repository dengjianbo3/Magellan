"""
Reports Router
报告管理路由
"""

import uuid
import logging
import io
import re
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse

from ...services.storage import get_report_storage, ReportStorage
from ...exporters.chart_generator import ChartGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize chart generator
chart_generator_zh = ChartGenerator(language="zh")
chart_generator_en = ChartGenerator(language="en")


def get_storage() -> ReportStorage:
    """依赖注入：获取报告存储服务"""
    try:
        return get_report_storage()
    except RuntimeError as e:
        # Strict mode: fail fast instead of silently using in-memory fallback.
        raise HTTPException(status_code=503, detail=str(e))


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


# ==================== Chart API ====================

def _extract_numbers_from_text(text: str) -> List[float]:
    """从文本中提取数字"""
    if not text:
        return []
    # Match numbers including decimals and percentages
    numbers = re.findall(r'[\d,]+\.?\d*', str(text))
    result = []
    for n in numbers:
        try:
            result.append(float(n.replace(',', '')))
        except (ValueError, TypeError):
            pass
    return result


def _extract_financial_data(report: Dict[str, Any]) -> Dict[str, Any]:
    """从报告中提取财务数据"""
    steps = report.get("steps", [])
    now_year = datetime.now().year

    # 尝试从步骤中提取财务数据
    financial_data = {
        "years": [],
        "revenue": [],
        "gross_margin": [],
        "net_margin": []
    }

    # 查找财务相关步骤
    for step in steps:
        result = step.get("result", "")
        agent = step.get("agent", "")

        if "财务" in agent or "Financial" in agent or "财务" in str(result):
            numbers = _extract_numbers_from_text(result)
            if len(numbers) >= 3:
                # 假设找到的数字是收入
                financial_data["revenue"] = numbers[:4] if len(numbers) >= 4 else numbers[:]
                break

    if financial_data["revenue"]:
        n = len(financial_data["revenue"])
        financial_data["years"] = list(range(now_year - n + 1, now_year + 1))

    return financial_data


def _extract_market_data(report: Dict[str, Any]) -> Dict[str, Any]:
    """从报告中提取市场数据"""
    company_name = report.get("company_name", "目标公司")
    # Best-effort extraction from step results if present; otherwise return empty to avoid fake charts.
    steps = report.get("steps", [])
    market_size = []
    years = []

    for step in steps:
        result = step.get("result", {})
        if isinstance(result, dict):
            if isinstance(result.get("market_size"), list):
                market_size = result.get("market_size")
                years = result.get("years") or []
                break

    data = {
        "companies": [],
        "shares": [],
        "years": years,
        "market_size": market_size,
        "growth_rate": []
    }

    # Some reports may embed "companies/shares" directly.
    for step in steps:
        result = step.get("result", {})
        if isinstance(result, dict) and result.get("companies") and result.get("shares"):
            data["companies"] = result.get("companies") or []
            data["shares"] = result.get("shares") or []
            break

    # Fallback: allow displaying only the target company if share data exists elsewhere (still requires real values).
    if data["companies"] and company_name not in data["companies"]:
        pass

    return data


def _extract_health_metrics(report: Dict[str, Any]) -> Dict[str, float]:
    """从报告中提取财务健康度指标"""
    steps = report.get("steps", [])
    for step in steps:
        result = step.get("result", {})
        if isinstance(result, dict) and isinstance(result.get("health_metrics"), dict):
            return result.get("health_metrics") or {}
    return {}


def _extract_risk_data(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从报告中提取风险数据"""
    steps = report.get("steps", [])
    for step in steps:
        result = step.get("result", {})
        if isinstance(result, dict) and isinstance(result.get("risks"), list):
            return result.get("risks") or []
    return []


def _extract_team_scores(report: Dict[str, Any]) -> Dict[str, float]:
    """从报告中提取团队评分"""
    steps = report.get("steps", [])
    for step in steps:
        result = step.get("result", {})
        if isinstance(result, dict) and isinstance(result.get("team_scores"), dict):
            return result.get("team_scores") or {}
    return {}


@router.get("/{report_id}/charts/{chart_type}")
async def get_report_chart(
    report_id: str,
    chart_type: str,
    language: str = Query("zh", description="Language: zh or en"),
    storage: ReportStorage = Depends(get_storage)
):
    """
    生成并返回报告图表

    支持的图表类型:
    - revenue: 收入趋势图
    - profit: 利润率趋势图
    - financial_health: 财务健康度评分卡
    - market_share: 市场份额饼图
    - market_growth: 市场增长趋势图
    - risk_matrix: 风险评估矩阵
    - team_radar: 团队能力雷达图
    """
    # 获取报告
    report = storage.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # 选择语言对应的图表生成器
    generator = chart_generator_zh if language == "zh" else chart_generator_en

    # 根据图表类型提取数据并生成图表
    try:
        img_buffer = io.BytesIO()

        no_data_msg = "Insufficient data for this chart." if language == "en" else "该报告暂无足够数据生成此图表。"

        try:
            if chart_type == "revenue":
                data = _extract_financial_data(report)
                generator.generate_revenue_chart(data, img_buffer)

            elif chart_type == "profit":
                data = _extract_financial_data(report)
                generator.generate_profit_chart(data, img_buffer)

            elif chart_type == "financial_health":
                data = _extract_health_metrics(report)
                generator.generate_financial_health_score(data, img_buffer)

            elif chart_type == "market_share":
                data = _extract_market_data(report)
                generator.generate_market_share_chart(data, img_buffer)

            elif chart_type == "market_growth":
                data = _extract_market_data(report)
                generator.generate_market_growth_chart(data, img_buffer)

            elif chart_type == "risk_matrix":
                data = _extract_risk_data(report)
                generator.generate_risk_matrix(data, img_buffer)

            elif chart_type == "team_radar":
                data = _extract_team_scores(report)
                generator.generate_team_radar_chart(data, img_buffer)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown chart type: {chart_type}. Supported types: revenue, profit, financial_health, market_share, market_growth, risk_matrix, team_radar"
                )
        except ValueError as e:
            # Truthful empty-state chart (no demo/random fallback).
            logger.info(f"Chart {chart_type} has insufficient data for report {report_id}: {e}")
            generator.generate_empty_chart(no_data_msg, img_buffer)

        else:
            pass

        # 重置buffer位置
        img_buffer.seek(0)

        # 返回PNG图像
        return StreamingResponse(
            img_buffer,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename={chart_type}.png",
                "Cache-Control": "max-age=3600"  # 缓存1小时
            }
        )

    except Exception as e:
        logger.error(f"Error generating chart {chart_type} for report {report_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")
