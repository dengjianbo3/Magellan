"""
Analysis V2 Router
统一分析API路由 (5个投资场景)

Phase 4: 迁移自 main.py 的 V2 分析端点
- POST /start: 启动新分析
- GET /{session_id}/status: 获取分析状态
- GET /scenarios: 获取支持的场景列表

Note: WebSocket /ws/v2/analysis/{session_id} 保留在 main.py
"""
import uuid
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request

from ...models.analysis_models import (
    AnalysisRequest,
    AnalysisDepth
)
from ...core.session_store import SessionStore
from ...core.auth import CurrentUser, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _safe_session_store() -> Optional[SessionStore]:
    """Create a SessionStore if Redis is available; otherwise return None."""
    try:
        return SessionStore()
    except Exception as e:
        logger.warning(f"[AnalysisV2] Redis unavailable, session persistence disabled: {e}")
        return None


def _build_ws_url(request: Request, session_id: str) -> str:
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    scheme = forwarded_proto or request.url.scheme
    ws_scheme = "wss" if scheme in ("https", "wss") else "ws"
    host = request.headers.get("host") or request.url.netloc

    configured_base = (os.getenv("PUBLIC_WS_BASE_URL") or "").strip()
    if configured_base:
        base = configured_base.rstrip("/")
        parsed = urlparse(base)
        if parsed.scheme in ("http", "https"):
            cfg_ws_scheme = "wss" if parsed.scheme == "https" else "ws"
            base = f"{cfg_ws_scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        elif parsed.scheme in ("ws", "wss"):
            base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        elif base.startswith("//"):
            base = f"{ws_scheme}:{base}".rstrip("/")
        elif base.startswith("/"):
            base = f"{ws_scheme}://{host}{base}".rstrip("/")
        else:
            base = f"{ws_scheme}://{base.lstrip('/')}".rstrip("/")
        return f"{base}/ws/v2/analysis/{session_id}"

    return f"{ws_scheme}://{host}/ws/v2/analysis/{session_id}"


@router.post("/start")
async def start_analysis_v2(
    request: AnalysisRequest,
    http_request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    V2: 启动新的分析任务 (统一入口,支持5个投资场景)

    支持场景:
    - early-stage-investment: 早期投资 (Angel/Seed/Series A)
    - growth-investment: 成长期投资 (Series B+)
    - public-market-investment: 公开市场投资 (股票/ETF)
    - alternative-investment: 另类投资 (Crypto/DeFi/NFT)
    - industry-research: 行业/市场研究

    Returns:
        {
            "success": true,
            "session_id": "early_abc123...",
            "ws_url": "ws://localhost:8000/ws/v2/analysis/early_abc123",
            "estimated_duration": "5分钟" (quick) or "30-45分钟" (standard)
        }
    """
    try:
        request = request.model_copy(update={"user_id": current_user.id})

        # 生成session_id
        session_id = f"{request.scenario.value}_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        # 估算时长
        if request.config.depth == AnalysisDepth.QUICK:
            estimated_duration = "3-5分钟"
        elif request.config.depth == AnalysisDepth.STANDARD:
            estimated_duration = "30-45分钟"
        else:  # COMPREHENSIVE
            estimated_duration = "1-2小时"

        logger.info(f"[V2 API] Starting analysis: scenario={request.scenario.value}, depth={request.config.depth.value}, session={session_id}")

        # Persist an initial snapshot for /status recovery (even before WS connects).
        store = _safe_session_store()
        if store:
            try:
                store.save_session(session_id, {
                    "session_id": session_id,
                    "scenario": request.scenario.value,
                    "request": request.model_dump(),
                    "status": "created",
                    "results": {},
                    "workflow": [],
                    "started_at": now,
                    "updated_at": now,
                })
            finally:
                try:
                    store.close()
                except Exception:
                    pass

        return {
            "success": True,
            "session_id": session_id,
            "ws_url": _build_ws_url(http_request, session_id),
            "estimated_duration": estimated_duration,
            "scenario": request.scenario.value,
            "depth": request.config.depth.value
        }

    except Exception as e:
        logger.error(f"[V2 API] Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail=f"启动分析失败: {str(e)}")


@router.get("/{session_id}/status")
async def get_analysis_status_v2(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    V2: 获取分析状态 (用于恢复进度)

    Returns:
        {
            "session_id": "...",
            "status": "running" | "completed" | "error",
            "progress": 60,
            "current_step": {...},
            "workflow": [...],
            "started_at": "...",
            "quick_judgment": {...} (如果有快速判断结果)
        }
    """
    store = _safe_session_store()
    if not store:
        raise HTTPException(status_code=503, detail="Session store unavailable (Redis not connected)")

    try:
        session = store.get_session(session_id, user_id=current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        workflow: List[Dict[str, Any]] = session.get("workflow") or []
        total = len(workflow)

        def _step_status(step: Dict[str, Any]) -> str:
            return str(step.get("status") or "pending")

        # Compute overall progress based on completed steps and current running step progress.
        progress = 0.0
        current_step: Optional[Dict[str, Any]] = None
        for idx, step in enumerate(workflow):
            st = _step_status(step)
            if st in ("success", "completed"):
                progress += 100.0 / max(total, 1)
            elif st == "running":
                progress += float(step.get("progress") or 0) / 100.0 * (100.0 / max(total, 1))
                if current_step is None:
                    current_step = {**step, "step_number": idx + 1}
            elif current_step is None and st in ("pending", "skipped", "error"):
                # Best effort: expose the first non-success step as the "current" step.
                current_step = {**step, "step_number": idx + 1}

        if total == 0:
            # No workflow yet (WS not connected or not started).
            progress = 0.0

        status = session.get("status") or "running"
        if session.get("error"):
            status = "error"

        return {
            "session_id": session_id,
            "status": status,
            "progress": int(min(max(progress, 0.0), 100.0)),
            "current_step": current_step,
            "workflow": workflow,
            "started_at": session.get("started_at"),
            "updated_at": session.get("updated_at"),
            "quick_judgment": session.get("quick_judgment"),
            "final_report": session.get("final_report"),
            "error": session.get("error"),
        }
    finally:
        try:
            store.close()
        except Exception:
            pass


@router.get("/scenarios")
async def get_available_scenarios():
    """
    V2: 获取支持的投资场景列表

    Returns:
        {
            "scenarios": [
                {
                    "id": "early-stage-investment",
                    "name": "早期投资",
                    "description": "评估Angel/Seed/Series A投资机会",
                    "required_inputs": ["company_name", "stage"],
                    "optional_inputs": ["bp_file_id", "team_members"],
                    "supported_depths": ["quick", "standard", "comprehensive"]
                },
                ...
            ]
        }
    """
    # Keep a clear product surface:
    # - early-stage-investment is active by default
    # - other scenarios are marked coming_soon unless explicitly enabled
    enable_experimental = os.getenv("ANALYSIS_ENABLE_EXPERIMENTAL_SCENARIOS", "false").lower() == "true"
    experimental_status = "active" if enable_experimental else "coming_soon"

    scenarios = [
        {
            "id": "early-stage-investment",
            "name": "早期投资",
            "description": "评估Angel/Seed/Series A投资机会",
            "icon": "rocket",
            "stages": ["angel", "seed", "pre-a", "series-a"],
            "required_inputs": ["company_name", "stage"],
            "optional_inputs": ["bp_file_id", "team_members", "industry", "founded_year"],
            "supported_depths": ["quick", "standard", "comprehensive"],
            "quick_mode_duration": "3-5分钟",
            "standard_mode_duration": "30-45分钟",
            "status": "active"
        },
        {
            "id": "growth-investment",
            "name": "成长期投资",
            "description": "评估Series B+公司的扩张潜力",
            "icon": "chart",
            "stages": ["series-b", "series-c", "series-d", "series-e", "pre-ipo"],
            "required_inputs": ["company_name", "stage"],
            "optional_inputs": ["financial_file_id", "annual_revenue", "growth_rate"],
            "supported_depths": ["quick", "standard", "comprehensive"],
            "quick_mode_duration": "3-5分钟",
            "standard_mode_duration": "30-45分钟",
            "status": experimental_status
        },
        {
            "id": "public-market-investment",
            "name": "公开市场投资",
            "description": "分析上市公司投资价值",
            "icon": "building",
            "required_inputs": ["ticker"],
            "optional_inputs": ["exchange", "asset_type"],
            "supported_depths": ["quick", "standard", "comprehensive"],
            "quick_mode_duration": "3-5分钟",
            "standard_mode_duration": "20-30分钟",
            "status": experimental_status
        },
        {
            "id": "alternative-investment",
            "name": "另类投资",
            "description": "评估Crypto/DeFi/NFT投资机会",
            "icon": "bitcoin",
            "required_inputs": ["asset_type"],
            "optional_inputs": ["symbol", "contract_address", "chain", "project_name"],
            "supported_depths": ["quick", "standard", "comprehensive"],
            "quick_mode_duration": "3-5分钟",
            "standard_mode_duration": "25-35分钟",
            "status": experimental_status
        },
        {
            "id": "industry-research",
            "name": "行业/市场研究",
            "description": "系统性研究行业趋势和投资机会",
            "icon": "search",
            "required_inputs": ["industry_name", "research_topic"],
            "optional_inputs": ["geo_scope", "key_questions"],
            "supported_depths": ["quick", "standard", "comprehensive"],
            "quick_mode_duration": "5-8分钟",
            "standard_mode_duration": "45-60分钟",
            "status": experimental_status
        },
    ]

    return {"scenarios": scenarios}
