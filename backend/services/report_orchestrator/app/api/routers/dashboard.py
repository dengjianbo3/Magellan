"""
Dashboard Router
仪表板路由
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException

from ...services.storage import get_report_storage, ReportStorage
from ...core.agents.registry import get_agent_registry
from ...core.session_store import SessionStore
from ...core.auth import CurrentUser, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def get_storage() -> ReportStorage:
    """依赖注入：获取报告存储服务"""
    try:
        return get_report_storage()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/stats")
async def get_dashboard_stats(
    storage: ReportStorage = Depends(get_storage),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取仪表板统计信息
    - 报告总数
    - 活跃分析数
    - AI Agent 数量
    - 成功率
    """
    all_reports = storage.get_all(limit=1000, user_id=current_user.id)
    total_reports = len(all_reports)

    # AI agents count (real registry)
    try:
        ai_agents_count = len(get_agent_registry().list_agents())
    except Exception:
        ai_agents_count = 0

    # Active analyses count (sessions that are not completed)
    active_analyses = 0
    try:
        store = SessionStore()
        sessions = store.list_sessions(limit=2000, user_id=current_user.id)
        active_statuses = {"created", "initializing", "running"}
        active_analyses = sum(1 for s in sessions if str(s.get("status") or "").lower() in active_statuses)
    except Exception:
        active_analyses = 0

    # Success rate
    completed_reports = len([r for r in all_reports if r.get("status") == "completed"])
    success_rate = (completed_reports / total_reports * 100) if total_reports > 0 else 100

    return {
        "success": True,
        "stats": {
            "total_reports": {
                "value": total_reports,
                "change": "+0",
                "trend": "neutral"
            },
            "active_analyses": {
                "value": active_analyses,
                "change": "+0",
                "trend": "neutral"
            },
            "ai_agents": {
                "value": ai_agents_count,
                "change": "0",
                "trend": "neutral"
            },
            "success_rate": {
                "value": f"{success_rate:.1f}%",
                "change": "+0%",
                "trend": "up" if success_rate > 90 else "neutral"
            }
        }
    }


@router.get("/recent-reports")
async def get_recent_reports(
    limit: int = 5,
    storage: ReportStorage = Depends(get_storage),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取最近的报告"""
    all_reports = storage.get_all(limit=limit * 2, user_id=current_user.id)
    sorted_reports = sorted(
        all_reports,
        key=lambda r: r.get("created_at", ""),
        reverse=True
    )[:limit]

    recent_reports = []
    for report in sorted_reports:
        # Calculate time ago
        try:
            created_at = datetime.fromisoformat(report.get("created_at", datetime.now().isoformat()))
            time_diff = datetime.now() - created_at

            if time_diff.days > 0:
                time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = max(1, time_diff.seconds // 60)
                time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        except (ValueError, TypeError, AttributeError):
            time_ago = "recently"

        agents_used = len(report.get("steps", []))

        recent_reports.append({
            "id": report["id"],
            "title": report.get("project_name", f"{report.get('company_name')} Analysis"),
            "date": time_ago,
            "status": report.get("status", "completed"),
            "agents": agents_used
        })

    return {
        "success": True,
        "reports": recent_reports
    }


@router.get("/trends")
async def get_analysis_trends(
    days: int = 7,
    storage: ReportStorage = Depends(get_storage),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取分析趋势数据"""
    # Generate labels
    labels = []
    end_date = datetime.now()
    for i in range(days - 1, -1, -1):
        date = end_date - timedelta(days=i)
        labels.append(date.strftime("%a"))

    # Count reports by day
    reports_by_day = defaultdict(int)
    all_reports = storage.get_all(limit=1000, user_id=current_user.id)

    for report in all_reports:
        try:
            created_at = datetime.fromisoformat(report.get("created_at", datetime.now().isoformat()))
            days_ago = (end_date - created_at).days
            if days_ago < days:
                day_label = created_at.strftime("%a")
                reports_by_day[day_label] += 1
        except (ValueError, TypeError, KeyError):
            pass

    reports_data = [reports_by_day.get(label, 0) for label in labels]

    # Best-effort: count analysis sessions by day as "analyses started".
    analyses_by_day = defaultdict(int)
    try:
        store = SessionStore()
        sessions = store.list_sessions(limit=5000, user_id=current_user.id)
        for s in sessions:
            started_at = s.get("started_at") or s.get("updated_at")
            if not started_at:
                continue
            try:
                started_dt = datetime.fromisoformat(started_at)
            except Exception:
                continue
            days_ago = (end_date - started_dt).days
            if 0 <= days_ago < days:
                analyses_by_day[started_dt.strftime("%a")] += 1
    except Exception:
        analyses_by_day = defaultdict(int)

    analyses_data = [analyses_by_day.get(label, 0) for label in labels]

    return {
        "success": True,
        "labels": labels,
        "datasets": {
            "reports": reports_data,
            "analyses": analyses_data
        }
    }


@router.get("/agent-performance")
async def get_agent_performance(
    storage: ReportStorage = Depends(get_storage),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取 Agent 性能统计"""
    # 从报告中统计 Agent 使用情况
    agent_stats = defaultdict(lambda: {"count": 0, "success": 0})

    # 定义 Agent 类别映射
    agent_categories = {
        "market_analysis": ["market_analyst", "MarketAnalyst", "市场分析"],
        "financial_review": ["financial_expert", "FinancialExpert", "财务分析"],
        "team_evaluation": ["team_evaluator", "TeamEvaluator", "团队评估"],
        "risk_assessment": ["risk_assessor", "RiskAssessor", "风险评估"],
        "tech_analysis": ["tech_specialist", "TechSpecialist", "技术专家"],
        "legal_review": ["legal_advisor", "LegalAdvisor", "法律顾问"],
        "technical_analysis": ["technical_analyst", "TechnicalAnalyst", "技术分析师"],
    }

    all_reports = storage.get_all(limit=1000, user_id=current_user.id)
    for report in all_reports:
        for step in report.get("steps", []):
            agent_name = step.get("agent", step.get("agent_name", step.get("name", "unknown")))
            agent_stats[agent_name]["count"] += 1
            if step.get("status") in ["completed", "success"]:
                agent_stats[agent_name]["success"] += 1

    # 计算各类别的任务数
    category_counts = {
        "market_analysis": 0,
        "financial_review": 0,
        "team_evaluation": 0,
        "risk_assessment": 0
    }

    for agent_name, stats in agent_stats.items():
        for category, keywords in agent_categories.items():
            if category in category_counts:
                for keyword in keywords:
                    if keyword.lower() in agent_name.lower():
                        category_counts[category] += stats["count"]
                        break

    total = sum(category_counts.values())

    # Format agents list response
    agents = []
    for name, stats in agent_stats.items():
        success_rate = (stats["success"] / stats["count"] * 100) if stats["count"] > 0 else 100
        agents.append({
            "name": name,
            "usage_count": stats["count"],
            "success_rate": round(success_rate, 1),
            "status": "active"
        })

    # Sort by usage count
    agents.sort(key=lambda x: x["usage_count"], reverse=True)

    return {
        "success": True,
        "performance": category_counts,  # 前端期望的格式
        "agents": agents[:10],  # Top 10
        "has_data": total > 0
    }
