"""
DD Workflow Router
DD尽职调查工作流路由

Phase 4: 迁移自 main.py 的 DD 工作流端点
- POST /start_http: HTTP版本启动DD分析
- GET /session/{session_id}: 获取DD会话状态
- POST /{session_id}/valuation: 生成估值分析
"""
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ...models.dd_models import (
    DDSessionContext,
    PreliminaryIM,
)
from ...core.dd_state_machine import DDStateMachine

router = APIRouter()

# Dependencies - will be set from main.py
_session_exists_func: Optional[Callable] = None
_get_session_func: Optional[Callable] = None
_save_session_func: Optional[Callable] = None


def set_session_funcs(exists_func: Callable, get_func: Callable, save_func: Callable):
    """Set session management functions from main.py"""
    global _session_exists_func, _get_session_func, _save_session_func
    _session_exists_func = exists_func
    _get_session_func = get_func
    _save_session_func = save_func
    print("[dd_workflow.py] Session functions set")


def _session_exists(session_id: str) -> bool:
    if _session_exists_func:
        return _session_exists_func(session_id)
    return False


def _get_session(session_id: str) -> Optional[DDSessionContext]:
    if _get_session_func:
        return _get_session_func(session_id)
    return None


def _save_session(session_id: str, context: DDSessionContext) -> bool:
    if _save_session_func:
        return _save_session_func(session_id, context)
    return False


async def _run_dd_workflow_background(state_machine: DDStateMachine):
    """Run DD workflow in background (for HTTP endpoint)"""
    try:
        await state_machine.run(websocket=None)
        _save_session(state_machine.context.session_id, state_machine.get_current_context())
    except Exception as e:
        print(f"Background DD workflow error: {e}")
        import traceback
        traceback.print_exc()


@router.post("/start_http")
async def start_dd_analysis_http(
    company_name: str = Form(...),
    bp_file: UploadFile = File(...),
    user_id: str = Form(default="default_user")
):
    """
    HTTP version of DD analysis (for testing without WebSocket).
    Returns immediately with session_id, use /dd/session/{session_id} to poll status.
    """
    # Generate session ID
    session_id = f"dd_{company_name}_{uuid.uuid4().hex[:8]}"

    # Read file
    bp_file_content = await bp_file.read()

    # Create state machine
    state_machine = DDStateMachine(
        session_id=session_id,
        company_name=company_name,
        bp_file_content=bp_file_content,
        bp_filename=bp_file.filename,
        user_id=user_id
    )

    # Store session
    _save_session(session_id, state_machine.get_current_context())

    # Run workflow in background
    asyncio.create_task(_run_dd_workflow_background(state_machine))

    return {
        "session_id": session_id,
        "status": "started",
        "message": f"DD 分析已启动，session_id: {session_id}"
    }


@router.get("/session/{session_id}")
async def get_dd_session(session_id: str):
    """Query DD session status"""
    if not _session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    context = _get_session(session_id)

    if context is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Build response
    response = {
        "session_id": context.session_id,
        "company_name": context.company_name,
        "current_state": context.current_state,
        "created_at": context.created_at,
        "updated_at": context.updated_at,
    }

    # Add results if available
    if context.current_state == "completed":
        response["preliminary_im"] = PreliminaryIM(
            company_name=context.company_name,
            bp_structured_data=context.bp_data,
            team_section=context.team_analysis,
            market_section=context.market_analysis,
            cross_check_results=context.cross_check_results,
            dd_questions=context.dd_questions,
            session_id=context.session_id
        ).dict()

    if len(context.errors) > 0:
        response["errors"] = context.errors

    return response


@router.post("/{session_id}/valuation")
async def generate_valuation_analysis(session_id: str):
    """
    生成估值与退出分析（Sprint 7）

    为已完成的 DD 工作流生成估值和退出路径分析
    """
    # 1. 检查 session 是否存在
    if not _session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    context = _get_session(session_id)

    if context is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # 2. 检查是否已有必要的分析结果
    if not context.bp_data or not context.market_analysis:
        raise HTTPException(
            status_code=400,
            detail="BP data and market analysis are required for valuation analysis"
        )

    try:
        # 3. 导入 Agents
        from ...agents.valuation_agent import ValuationAgent, ValuationAnalysis
        from ...agents.exit_agent import ExitAgent, ExitAnalysis

        # 4. 执行估值分析
        valuation_agent = ValuationAgent()
        valuation_result = await valuation_agent.analyze_valuation(
            bp_data=context.bp_data,
            market_analysis=context.market_analysis
        )

        # 5. 执行退出分析
        exit_agent = ExitAgent()
        exit_result = await exit_agent.analyze_exit_paths(
            bp_data=context.bp_data,
            market_analysis=context.market_analysis,
            valuation_analysis=valuation_result
        )

        # 6. 构建完整的"财务与估值"章节
        valuation_section = _build_valuation_section(valuation_result, exit_result)

        # 7. 返回结果
        return {
            "session_id": session_id,
            "valuation_analysis": valuation_result.dict(),
            "exit_analysis": exit_result.dict(),
            "im_section": valuation_section
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Valuation analysis failed: {str(e)}")


def _build_valuation_section(valuation: Any, exit: Any) -> str:
    """构建完整的财务与估值章节（Markdown 格式）"""

    section = f"""## 六、财务与估值分析

### 6.1 估值方法论

{valuation.methodology}

### 6.2 估值区间

基于{valuation.methodology}，我们给出以下估值建议：

- **估值区间**: {valuation.valuation_range.low/100000000:.2f} 亿元 - {valuation.valuation_range.high/100000000:.2f} 亿元（{valuation.valuation_range.currency}）
- **估值方法**: {valuation.methodology}

"""

    # 6.3 可比公司
    if valuation.comparable_companies:
        section += """### 6.3 可比公司分析

| 公司名称 | PE 倍数 | PS 倍数 | 市值 | 增长率 |
|---------|---------|---------|------|--------|\n"""
        for comp in valuation.comparable_companies:
            pe = f"{comp.pe_ratio}x" if comp.pe_ratio else "N/A"
            ps = f"{comp.ps_ratio}x" if comp.ps_ratio else "N/A"
            market_cap = comp.market_cap or "N/A"
            growth = comp.growth_rate or "N/A"
            section += f"| {comp.name} | {pe} | {ps} | {market_cap} | {growth} |\n"

        section += "\n"

    # 6.4 关键假设
    section += "### 6.4 关键假设\n\n"
    for i, assumption in enumerate(valuation.key_assumptions, 1):
        section += f"{i}. {assumption}\n"
    section += "\n"

    # 6.5 退出路径分析
    section += f"""### 6.5 退出路径分析

#### 主要退出路径: {exit.primary_path}

**IPO 分析**:
- **可行性**: {exit.ipo_analysis.feasibility}
- **预计时间**: {exit.ipo_analysis.estimated_timeline}
- **目标板块**: {exit.ipo_analysis.target_board or 'N/A'}

**前置条件**:
"""
    for i, req in enumerate(exit.ipo_analysis.requirements, 1):
        section += f"{i}. {req}\n"

    # 并购机会
    if exit.ma_opportunities:
        section += "\n**并购机会** (潜在买家):\n"
        for i, buyer in enumerate(exit.ma_opportunities, 1):
            section += f"{i}. {buyer}\n"

    # 风险提示
    section += "\n### 6.6 风险提示\n\n"
    section += "**估值风险**:\n"
    for risk in valuation.risks:
        section += f"- {risk}\n"

    section += "\n**退出风险**:\n"
    for risk in exit.exit_risks:
        section += f"- {risk}\n"

    section += "\n---\n\n"
    section += valuation.analysis_text
    section += "\n\n"
    section += exit.analysis_text

    return section
