"""
Dashboard Router
仪表板路由
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends

from ...services.storage import get_report_storage, ReportStorage

router = APIRouter()
logger = logging.getLogger(__name__)


def get_storage() -> ReportStorage:
    """依赖注入：获取报告存储服务"""
    return get_report_storage()


@router.get("/stats")
async def get_dashboard_stats(storage: ReportStorage = Depends(get_storage)):
    """
    获取仪表板统计信息
    - 报告总数
    - 活跃分析数
    - AI Agent 数量
    - 成功率
    """
    all_reports = storage.get_all(limit=1000)
    total_reports = len(all_reports)

    # AI agents count
    ai_agents_count = 9  # 新的 AgentRegistry 中有 9 个 Agent

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
                "value": 0,
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
    storage: ReportStorage = Depends(get_storage)
):
    """获取最近的报告"""
    all_reports = storage.get_all(limit=limit * 2)
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
        except:
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
    storage: ReportStorage = Depends(get_storage)
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
    all_reports = storage.get_all(limit=1000)

    for report in all_reports:
        try:
            created_at = datetime.fromisoformat(report.get("created_at", datetime.now().isoformat()))
            days_ago = (end_date - created_at).days
            if days_ago < days:
                day_label = created_at.strftime("%a")
                reports_by_day[day_label] += 1
        except:
            pass

    reports_data = [reports_by_day.get(label, 0) for label in labels]

    return {
        "success": True,
        "labels": labels,
        "datasets": {
            "reports": reports_data,
            "analyses": [0] * len(labels)  # 简化版不跟踪会话
        }
    }


@router.get("/agent-performance")
async def get_agent_performance(storage: ReportStorage = Depends(get_storage)):
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

    all_reports = storage.get_all(limit=1000)
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

    # 确保至少有一些数据用于图表显示
    total = sum(category_counts.values())
    if total == 0:
        # 如果没有数据，提供示例数据
        category_counts = {
            "market_analysis": 35,
            "financial_review": 28,
            "team_evaluation": 20,
            "risk_assessment": 17
        }

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
        "agents": agents[:10]  # Top 10
    }
