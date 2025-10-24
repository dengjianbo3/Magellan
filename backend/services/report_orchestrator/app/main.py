# backend/services/report_orchestrator/app/main.py
import httpx
import asyncio
import json
import re
import os
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# V2 models (keep for backward compatibility)
from .models.dd_models import (
    DDAnalysisRequest,
    DDWorkflowMessage,
    DDSessionContext,
    PreliminaryIM,
)

# V3: Import state machine
from .core.dd_state_machine import DDStateMachine

# --- Service Discovery ---
EXTERNAL_DATA_URL = "http://external_data_service:8006"
LLM_GATEWAY_URL = "http://llm_gateway:8003"

app = FastAPI(
    title="Orchestrator Agent Service",
    description="Manages the multi-agent workflow for generating investment reports (V2) and DD analysis (V3).",
    version="3.0.0"  # Updated for V3
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Pydantic Models ---
class AnalysisRequest(BaseModel):
    ticker: str

class ContinueRequest(BaseModel):
    session_id: str
    selected_ticker: str

class Step(BaseModel):
    id: int
    title: str
    status: str # 'running', 'success', 'error', 'paused'
    result: str | None = None
    options: List[Dict[str, Any]] | None = None # For HITL

class ReportSection(BaseModel):
    section_title: str
    content: str

class FinancialChartData(BaseModel):
    years: List[int]
    revenues: List[float]
    profits: List[float]

class FullReportResponse(BaseModel):
    company_ticker: str
    report_sections: List[ReportSection]
    financial_chart_data: Optional[FinancialChartData] = None

class InstantFeedbackRequest(BaseModel):
    analysis_context: str
    user_input: str

class InstantFeedbackResponse(BaseModel):
    feedback: str

class AnalysisResponse(BaseModel):
    session_id: str
    status: str # 'in_progress', 'hitl_required', 'completed', 'error', 'hitl_follow_up_required'
    steps: List[Step]
    preliminary_report: Optional[FullReportResponse] = None
    key_questions: Optional[List[str]] = None


# --- Helper Functions ---
async def call_llm_gateway(client: httpx.AsyncClient, history: List[Dict[str, Any]]) -> str:
    try:
        response = await client.post(f"{LLM_GATEWAY_URL}/chat", json={"history": history})
        if response.status_code == 200:
            try:
                return response.json()["content"]
            except (json.JSONDecodeError, KeyError):
                return '["Error: LLM returned invalid JSON."]'
        else:
            return f'["Error: LLM Gateway returned status code {response.status_code}"]'
    except Exception as e:
        return f'["Error: Could not connect to LLM Gateway: {e}"]'

from fastapi import WebSocket, WebSocketDisconnect

# ... (existing model definitions) ...

class WebSocketMessage(BaseModel):
    """Standard message format for WebSocket communication."""
    session_id: str
    status: str
    step: Optional[Step] = None
    preliminary_report: Optional[FullReportResponse] = None
    key_questions: Optional[List[str]] = None

USER_SERVICE_URL = "http://user_service:8008"

# ... (existing model definitions) ...

class UserPersona(BaseModel):
    investment_style: Optional[str] = "Balanced"
    risk_tolerance: Optional[str] = "Medium"

# --- WebSocket Workflow ---
@app.websocket("/ws/start_analysis")
async def websocket_analysis_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = ""
    user_persona = UserPersona()
    selected_ticker = ""

    try:
        # 1. Wait for the initial request
        initial_request = await websocket.receive_json()
        ticker = initial_request.get("ticker")
        user_id = initial_request.get("user_id", "default_user")

        if not ticker:
            await websocket.close(code=1008, reason="Ticker not provided")
            return

        async with httpx.AsyncClient(timeout=300.0) as client:
            uuid_response = await client.get('https://www.uuidgenerator.net/api/version4')
            session_id = f"session_{ticker}_{uuid_response.text}"

            print("DEBUG: Starting Step 0: Fetch User Persona")
            step0 = Step(id=0, title=f"正在获取用户 '{user_id}' 的投资画像", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step0).dict())
            print("DEBUG: Sent Step 0 running status")
            try:
                print("DEBUG: Calling user_service")
                persona_resp = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
                persona_resp.raise_for_status()
                user_persona = UserPersona(**persona_resp.json())
                step0.status = "success"
                step0.result = f"画像已加载：投资风格 '{user_persona.investment_style}', 风险偏好 '{user_persona.risk_tolerance}'."
                print("DEBUG: user_service call successful")
            except Exception as e:
                step0.status = "error"
                step0.result = "无法加载用户画像，将使用默认设置。"
                print(f"DEBUG: user_service call failed: {e}")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step0).dict())
            print("DEBUG: Sent Step 0 final status")

            # --- Step 1: Data Collection & Ambiguity Resolution ---
            print("DEBUG: Starting Step 1: Data Collection")
            step1 = Step(id=1, title=f"正在为 '{ticker}' 获取公开数据", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())
            print("DEBUG: Sent Step 1 running status")
            
            public_data_resp = await client.post(f"{EXTERNAL_DATA_URL}/get_company_info", json={"ticker": ticker})
            print("DEBUG: Called get_company_info")
            public_data_resp.raise_for_status()
            response_data = public_data_resp.json()

            if response_data['status'] == 'multiple_options':
                print("DEBUG: Ambiguity found, pausing for user input")
                step1.status = "paused"
                step1.result = "公司名称存在歧义，请选择正确的公司。"
                step1.options = response_data['data']
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='hitl_required', step=step1).dict())
                
                print("DEBUG: Waiting for user choice...")
                user_choice = await websocket.receive_json()
                selected_ticker = user_choice.get("selected_ticker")
                ticker = selected_ticker
                print(f"DEBUG: User selected {selected_ticker}")

                step1.title = f"正在为 {selected_ticker} 获取已确认的数据"
                step1.status = "running"
                step1.result = f"您选择了 {selected_ticker}。正在继续分析..."
                step1.options = None
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())

                public_data_resp = await client.post(f"{EXTERNAL_DATA_URL}/get_company_info", json={"ticker": selected_ticker})
                print("DEBUG: Called get_company_info again with confirmed ticker")
            else:
                selected_ticker = ticker

            public_data_resp.raise_for_status()
            public_data = public_data_resp.json()['data']
            step1.status = "success"
            step1.result = f"已成功获取 {public_data.get('company_name', selected_ticker)} 的数据。"
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())
            print("DEBUG: Sent Step 1 success status")

            # --- Step 2: Initial Analysis with LLM ---
            print("DEBUG: Starting Step 2: Initial Analysis")
            step2 = Step(id=2, title="正在使用 Gemini 生成初步分析", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step2).dict())
            prompt = f"请根据以下公司数据，为一位投资者撰写一份简洁并引人入胜的中文公司介绍。\n\n数据:\n{public_data}"
            summary = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])
            step2.status = "success"
            step2.result = summary
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step2).dict())
            print("DEBUG: Sent Step 2 success status")

            # --- Step 3: Fetch Financial Data for Chart ---
            print("DEBUG: Starting Step 3: Fetch Financial Data")
            step3 = Step(id=3, title="正在获取用于图表的财务摘要", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step3).dict())
            financial_data = None
            try:
                print("DEBUG: Calling get_financial_summary")
                financial_resp = await client.post(f"{EXTERNAL_DATA_URL}/get_financial_summary", json={"ticker": selected_ticker})
                financial_resp.raise_for_status()
                financial_data = financial_resp.json()
                step3.status = "success"
                step3.result = "已成功获取财务摘要。"
                print("DEBUG: get_financial_summary successful")
            except Exception as e:
                step3.status = "error"
                step3.result = f"无法获取财务摘要: {e}"
                print(f"DEBUG: get_financial_summary failed: {e}")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step3).dict())
            print("DEBUG: Sent Step 3 final status")

            # --- Step 4: Generate Key Questions (HITL Node 2) ---
            print("DEBUG: Starting Step 4: Generate Key Questions")
            step4 = Step(id=4, title="正在生成关键追问问题", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step4).dict())
            prompt = f"""你是一位专业的投资分析师。你的客户的投资风格是 '{user_persona.investment_style}'，风险偏好为 '{user_persona.risk_tolerance}'。
            请根据以下的公司介绍，为这位客户量身定制一个包含3-4个有深度、有批判性的中文追问问题的JSON数组。
            公司介绍: {summary}
            
            关键要求：你的整个回答必须只有纯粹的JSON数组，不包含任何额外的文字、解释或markdown格式。
            """
            questions_str = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])
            
            key_questions = []
            try:
                # First, try to parse directly
                key_questions = json.loads(questions_str)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract from markdown
                match = re.search(r"```json\n(.*)\n```", questions_str, re.DOTALL)
                if match:
                    try:
                        key_questions = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        key_questions = ["错误：无法从LLM返回的Markdown中解析JSON。"]
                else:
                    key_questions = ["错误：LLM返回了无效的、非JSON格式的内容。"]

            # Handle cases where the LLM returns a list of objects with a "question" key
            if key_questions and isinstance(key_questions[0], dict):
                key_questions = [q.get("question", "无效的问题格式") for q in key_questions]
            
            if not key_questions or "错误" in key_questions[0]:
                step4.status = "error"
                step4.result = key_questions[0] if key_questions else "错误：LLM返回了空的问题列表。"
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='error', step=step4).dict())
                return

            step4.status = "success"
            step4.result = "已成功生成用于用户追问的关键问题。"
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step4).dict())
            print("DEBUG: Sent Step 4 success status")

            # --- Final HITL Follow-up ---
            print("DEBUG: Preparing final HITL message")
            preliminary_report = FullReportResponse(
                company_ticker=selected_ticker,
                report_sections=[
                    ReportSection(section_title="初步分析", content=summary),
                    ReportSection(section_title="财务分析", content="包含关键财务数据的交互式图表。")
                ],
                financial_chart_data=financial_data
            )
            
            await websocket.send_json(WebSocketMessage(
                session_id=session_id,
                status='hitl_follow_up_required',
                preliminary_report=preliminary_report.dict(),
                key_questions=key_questions
            ).dict())
            print("DEBUG: Sent final HITL message")


    except WebSocketDisconnect:
        print(f"Client disconnected from session {session_id}")
    except Exception as e:
        print(f"An unexpected error occurred in session {session_id}: {e}")
        error_step = Step(id=-1, title="Workflow Error", status="error", result=str(e))
        if websocket.client_state == 1: # OPEN
             await websocket.send_json(WebSocketMessage(session_id=session_id, status='error', step=error_step).dict())
             await websocket.close(code=1011, reason=f"An internal error occurred: {e}")


# ... (Instant Feedback with Persona) ...
@app.post("/get_instant_feedback", response_model=InstantFeedbackResponse, tags=["Agent Workflow"])
async def get_instant_feedback(request: InstantFeedbackRequest):
    # In a real implementation, we'd fetch the user_persona here as well
    prompt = f"""你是一位AI投资分析师助手。你的用户有特定的投资画像。
    
    报告摘要:
    ---
    {request.analysis_context}
    ---
    
    用户的输入:
    ---
    {request.user_input}
    ---
    
    请从一个“平衡型”投资者且风险偏好为“中等”的角度，分析用户的输入，并提供简洁、有洞察力的中文反馈。
    """
    # ... (rest of the implementation)


# --- Deprecated HTTP Endpoints ---
@app.post("/start_analysis", response_model=AnalysisResponse, tags=["Agent Workflow (Deprecated)"])
async def start_analysis_session(request: AnalysisRequest):
    """
    [DEPRECATED] Use the WebSocket endpoint `/ws/start_analysis` instead.
    """
    # ... (existing implementation)
    pass

@app.post("/continue_analysis", response_model=AnalysisResponse, tags=["Agent Workflow (Deprecated)"])
async def continue_analysis_session(request: ContinueRequest):
    """
    [DEPRECATED] Use the WebSocket endpoint `/ws/start_analysis` instead.
    """
    # ... (existing implementation)
    pass

# ... (rest of the file)


@app.post("/generate_full_report", response_model=FullReportResponse, tags=["Agent Workflow"])
async def generate_full_report(
    ticker: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    **V2 Sprint 4 Workflow:**
    1. Receives uploaded files and a ticker.
    2. Simulates a multi-step analysis process.
    3. Returns a final, structured report.
    """
    file_names = [file.filename for file in files]
    await asyncio.sleep(2) # Simulate document parsing
    await asyncio.sleep(3) # Simulate LLM generating sections

    mock_sections = [
        ReportSection(section_title="Executive Summary", content=f"This is a comprehensive analysis of {ticker}, incorporating insights from {len(file_names)} uploaded documents and public market data. The company shows strong potential in its core market..."),
        ReportSection(section_title="Financial Analysis", content="The company's revenue has grown steadily over the past three years. Key metrics indicate a healthy financial position... (Data would be here)"),
        ReportSection(section_title="Market Position", content="The company is a major player in its industry, though it faces competition from several key rivals..."),
        ReportSection(section_title="Risk Assessment", content="Potential risks include market volatility, regulatory changes, and supply chain disruptions..."),
        ReportSection(section_title="Investment Recommendation", content="Based on the analysis, our recommendation is a 'BUY' with a target price of... This is a mock recommendation.")
    ]
    
    

@app.post("/get_instant_feedback", response_model=InstantFeedbackResponse, tags=["Agent Workflow"])
async def get_instant_feedback(request: InstantFeedbackRequest):
    """
    Provides instant feedback on a user's input based on the current analysis context.
    """
    prompt = f"""You are an AI investment analyst assistant. Your user is currently reviewing an investment report summary.
    
    Report Summary:
    ---
    {request.analysis_context}
    ---
    
    The user has just provided the following information or answer to a question:
    ---
    {request.user_input}
    ---
    
    Based on the user's input, provide a concise, insightful feedback. Analyze how this new information strengthens, weakens, or clarifies the points in the original summary. Do not just repeat the information.
    """
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            feedback = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])
            return InstantFeedbackResponse(feedback=feedback)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get feedback from LLM Gateway: {e}")


@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Orchestrator Agent", "version": "3.0.0"}


# ============================================================================
# V3: DD Workflow WebSocket Endpoint
# ============================================================================

# Session storage (in-memory for now, should use Redis in production)
dd_sessions: Dict[str, DDSessionContext] = {}


@app.websocket("/ws/start_dd_analysis")
async def websocket_dd_analysis_endpoint(websocket: WebSocket):
    """
    V3 WebSocket endpoint for Due Diligence (DD) workflow.
    
    Client sends:
    {
        "company_name": "智算科技",
        "bp_file_base64": "...",  // Base64 encoded file
        "bp_filename": "智算科技_BP.pdf",
        "user_id": "investor_001"
    }
    
    Server pushes:
    DDWorkflowMessage with real-time progress updates
    """
    await websocket.accept()
    print(f"[DEBUG] WebSocket connection accepted", flush=True)
    session_id = ""
    
    try:
        # 1. Receive initial request
        print(f"[DEBUG] Waiting for initial request...", flush=True)
        try:
            initial_request = await websocket.receive_json()
            print(f"[DEBUG] Received request: {initial_request}", flush=True)
        except Exception as recv_error:
            print(f"[ERROR] Failed to receive JSON: {recv_error}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        
        company_name = initial_request.get("company_name")
        bp_file_base64 = initial_request.get("bp_file_base64")
        bp_filename = initial_request.get("bp_filename", "business_plan.pdf")
        user_id = initial_request.get("user_id", "default_user")
        
        print(f"[DEBUG] company_name={company_name}, has_bp={bp_file_base64 is not None}", flush=True)
        
        if not company_name:
            print(f"[DEBUG] Missing company_name, closing connection", flush=True)
            await websocket.close(code=1008, reason="company_name is required")
            return
        
        # 2. Generate session ID
        session_id = f"dd_{company_name}_{uuid.uuid4().hex[:8]}"
        print(f"[DEBUG] Generated session_id: {session_id}", flush=True)
        
        # 3. Decode BP file (optional)
        import base64
        bp_file_content = None
        if bp_file_base64:
            try:
                bp_file_content = base64.b64decode(bp_file_base64)
                print(f"[DEBUG] Decoded BP file: {len(bp_file_content)} bytes", flush=True)
            except Exception as decode_error:
                print(f"[ERROR] Failed to decode BP file: {decode_error}", flush=True)
                raise
        else:
            print(f"[DEBUG] No BP file provided", flush=True)
        
        # 4. Create and run state machine
        print(f"[DEBUG] Creating DDStateMachine...", flush=True)
        try:
            state_machine = DDStateMachine(
                session_id=session_id,
                company_name=company_name,
                bp_file_content=bp_file_content,
                bp_filename=bp_filename,
                user_id=user_id
            )
            print(f"[DEBUG] DDStateMachine created successfully", flush=True)
        except Exception as create_error:
            print(f"[ERROR] Failed to create state machine: {create_error}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        
        # Store session
        dd_sessions[session_id] = state_machine.get_current_context()
        print(f"[DEBUG] Session stored", flush=True)
        
        # 5. Execute workflow
        print(f"[DEBUG] Starting workflow execution...", flush=True)
        try:
            await state_machine.run(websocket)
            print(f"[DEBUG] Workflow completed", flush=True)
        except Exception as run_error:
            print(f"[ERROR] Workflow execution failed: {run_error}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        
        # 6. Update stored session
        dd_sessions[session_id] = state_machine.get_current_context()
        
    except WebSocketDisconnect:
        print(f"[INFO] Client disconnected from DD session {session_id}", flush=True)
    except Exception as e:
        print(f"[ERROR] Error in DD workflow {session_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        
        try:
            if websocket.client_state == 1:  # OPEN
                error_dict = {
                    "session_id": session_id or "unknown",
                    "status": "error",
                    "message": f"DD 工作流出现错误: {str(e)}"
                }
                await websocket.send_json(error_dict)
                await websocket.close(code=1011, reason=f"Internal error: {str(e)}")
        except Exception as close_error:
            print(f"[ERROR] Failed to send error message: {close_error}", flush=True)


@app.post("/start_dd_analysis_http", tags=["DD Workflow (V3)"])
async def start_dd_analysis_http(
    company_name: str = Form(...),
    bp_file: UploadFile = File(...),
    user_id: str = Form(default="default_user")
):
    """
    HTTP version of DD analysis (for testing without WebSocket).
    Returns immediately with session_id, use /dd_session/{session_id} to poll status.
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
    dd_sessions[session_id] = state_machine.get_current_context()
    
    # Run workflow in background
    asyncio.create_task(_run_dd_workflow_background(state_machine))
    
    return {
        "session_id": session_id,
        "status": "started",
        "message": f"DD 分析已启动，session_id: {session_id}"
    }


async def _run_dd_workflow_background(state_machine: DDStateMachine):
    """Run DD workflow in background (for HTTP endpoint)"""
    try:
        await state_machine.run(websocket=None)
        dd_sessions[state_machine.context.session_id] = state_machine.get_current_context()
    except Exception as e:
        print(f"Background DD workflow error: {e}")
        import traceback
        traceback.print_exc()


@app.get("/dd_session/{session_id}", tags=["DD Workflow (V3)"])
async def get_dd_session(session_id: str):
    """Query DD session status"""
    if session_id not in dd_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    context = dd_sessions[session_id]
    
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


# ======================================
# Sprint 7: 估值与退出分析
# ======================================

@app.post("/api/v1/dd/{session_id}/valuation", tags=["DD Workflow (V3) - Valuation"])
async def generate_valuation_analysis(session_id: str):
    """
    生成估值与退出分析（Sprint 7）
    
    为已完成的 DD 工作流生成估值和退出路径分析
    """
    # 1. 检查 session 是否存在
    if session_id not in dd_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    context = dd_sessions[session_id]
    
    # 2. 检查是否已有必要的分析结果
    if not context.bp_data or not context.market_analysis:
        raise HTTPException(
            status_code=400,
            detail="BP data and market analysis are required for valuation analysis"
        )
    
    try:
        # 3. 导入 Agents
        from .agents.valuation_agent import ValuationAgent, ValuationAnalysis
        from .agents.exit_agent import ExitAgent, ExitAnalysis
        
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
        
        # 7. 保存到 context（可选，用于后续查询）
        context.updated_at = context.updated_at  # Trigger update
        
        # 8. 返回结果
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
|---------|---------|---------|------|--------|
"""
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
    section += "⚠️ **估值风险**:\n"
    for risk in valuation.risks:
        section += f"- {risk}\n"
    
    section += "\n⚠️ **退出风险**:\n"
    for risk in exit.exit_risks:
        section += f"- {risk}\n"
    
    section += "\n---\n\n"
    section += valuation.analysis_text
    section += "\n\n"
    section += exit.analysis_text
    
    return section
