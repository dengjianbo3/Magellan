"""
Analysis V2 Router
统一分析API路由 (5个投资场景)

Phase 4: 迁移自 main.py 的 V2 分析端点
- POST /start: 启动新分析
- GET /{session_id}/status: 获取分析状态
- GET /scenarios: 获取支持的场景列表
- WebSocket /ws/{session_id}: 实时分析进度 (在 websocket.py)
"""
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import asyncio

from ...models.analysis_models import (
    AnalysisRequest,
    InvestmentScenario,
    AnalysisDepth
)
from ...core.orchestrators.early_stage_orchestrator import EarlyStageInvestmentOrchestrator
from ...core.orchestrators.growth_orchestrator import GrowthInvestmentOrchestrator
from ...core.orchestrators.public_market_orchestrator import PublicMarketInvestmentOrchestrator
from ...core.orchestrators.alternative_orchestrator import AlternativeInvestmentOrchestrator
from ...core.orchestrators.industry_research_orchestrator import IndustryResearchOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/start")
async def start_analysis_v2(request: AnalysisRequest):
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
        # 生成session_id
        session_id = f"{request.scenario.value}_{uuid.uuid4().hex[:12]}"

        # 估算时长
        if request.config.depth == AnalysisDepth.QUICK:
            estimated_duration = "3-5分钟"
        elif request.config.depth == AnalysisDepth.STANDARD:
            estimated_duration = "30-45分钟"
        else:  # COMPREHENSIVE
            estimated_duration = "1-2小时"

        logger.info(f"[V2 API] Starting analysis: scenario={request.scenario.value}, depth={request.config.depth.value}, session={session_id}")

        return {
            "success": True,
            "session_id": session_id,
            "ws_url": f"ws://localhost:8000/ws/v2/analysis/{session_id}",
            "estimated_duration": estimated_duration,
            "scenario": request.scenario.value,
            "depth": request.config.depth.value
        }

    except Exception as e:
        logger.error(f"[V2 API] Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail=f"启动分析失败: {str(e)}")


@router.websocket("/ws/{session_id}")
async def websocket_analysis_v2(websocket: WebSocket, session_id: str):
    """
    V2: 统一分析WebSocket端点

    支持所有5个场景的实时分析进度推送
    Stage 2: 添加心跳机制支持
    """
    await websocket.accept()
    logger.info(f"[V2 WS] Client connected: session={session_id}")

    # Stage 2: 心跳处理和消息路由
    analysis_request = None
    analysis_started = asyncio.Event()
    heartbeat_active = True

    async def message_router():
        """统一处理所有接收的消息,避免竞争条件"""
        nonlocal analysis_request, heartbeat_active
        try:
            while heartbeat_active:
                try:
                    message = await websocket.receive_json()

                    if isinstance(message, dict):
                        msg_type = message.get('type')

                        if msg_type == 'ping':
                            # 立即响应心跳
                            logger.debug(f"[V2 WS] Heartbeat ping received from session={session_id}")
                            await websocket.send_json({
                                "type": "pong",
                                "timestamp": datetime.now().isoformat()
                            })
                        else:
                            # 这是实际的分析请求
                            if analysis_request is None:
                                analysis_request = message
                                logger.info(f"[V2 WS] Received analysis request: {message}")
                                analysis_started.set()
                            else:
                                # 分析已经开始,这可能是HITL响应或其他消息
                                logger.debug(f"[V2 WS] Received additional message during analysis: {msg_type}")

                except WebSocketDisconnect:
                    logger.info(f"[V2 WS] Message router: client disconnected session={session_id}")
                    heartbeat_active = False
                    break
                except Exception as e:
                    logger.error(f"[V2 WS] Message router error: {e}")
                    break
        except Exception as e:
            logger.error(f"[V2 WS] Message router fatal error: {e}")

    try:
        # Stage 2: 启动消息路由任务
        router_task = asyncio.create_task(message_router())

        # 等待接收分析请求 (通过message_router)
        await asyncio.wait_for(analysis_started.wait(), timeout=30.0)

        if analysis_request is None:
            raise Exception("Failed to receive analysis request")

        # 解析请求
        request = AnalysisRequest(**analysis_request)

        # 根据scenario创建对应的Orchestrator
        orchestrator = None

        if request.scenario == InvestmentScenario.EARLY_STAGE:
            orchestrator = EarlyStageInvestmentOrchestrator(
                session_id=session_id,
                request=request,
                websocket=websocket
            )
        elif request.scenario == InvestmentScenario.GROWTH:
            orchestrator = GrowthInvestmentOrchestrator(
                session_id=session_id,
                request=request,
                websocket=websocket
            )
        elif request.scenario == InvestmentScenario.PUBLIC_MARKET:
            orchestrator = PublicMarketInvestmentOrchestrator(
                session_id=session_id,
                request=request,
                websocket=websocket
            )
        elif request.scenario == InvestmentScenario.ALTERNATIVE:
            orchestrator = AlternativeInvestmentOrchestrator(
                session_id=session_id,
                request=request,
                websocket=websocket
            )
        elif request.scenario == InvestmentScenario.INDUSTRY_RESEARCH:
            orchestrator = IndustryResearchOrchestrator(
                session_id=session_id,
                request=request,
                websocket=websocket
            )
        else:
            # 停止消息路由
            heartbeat_active = False
            router_task.cancel()
            raise HTTPException(
                status_code=501,
                detail=f"场景 {request.scenario.value} 暂未实现"
            )

        # 执行分析
        result = await orchestrator.orchestrate()

        logger.info(f"[V2 WS] Analysis completed: session={session_id}")

        # Stage 2: 停止消息路由任务
        heartbeat_active = False
        router_task.cancel()

    except WebSocketDisconnect:
        logger.info(f"[V2 WS] Client disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"[V2 WS] Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "error": str(e)
                }
            })
        except:
            pass


@router.get("/{session_id}/status")
async def get_analysis_status_v2(session_id: str):
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
    # TODO: 从Redis获取session状态
    # session_data = await session_store.get_session(session_id)

    # Phase 1: 返回模拟数据
    return {
        "session_id": session_id,
        "status": "running",
        "progress": 50,
        "message": "V2 API - Session status (mock data)"
    }


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
    return {
        "scenarios": [
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
                "status": "coming_soon"
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
                "status": "coming_soon"
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
                "status": "coming_soon"
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
                "status": "coming_soon"
            }
        ]
    }
