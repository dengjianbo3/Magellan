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

# V4: Import intent recognition and conversation management
from .core.intent_recognizer import IntentRecognizer, ConversationManager, IntentType

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

# V5: Saved reports storage (in-memory for now)
saved_reports: List[Dict[str, Any]] = []

# V5: Dashboard analytics storage
dashboard_analytics = {
    "daily_stats": [],  # Daily reports/analyses counts
    "agent_usage": {}   # Agent usage statistics
}


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

        # V5: Extract frontend configuration
        project_name = initial_request.get("project_name")
        selected_agents = initial_request.get("selected_agents", [])
        data_sources = initial_request.get("data_sources", [])
        priority = initial_request.get("priority", "normal")
        description = initial_request.get("description")

        print(f"[DEBUG] company_name={company_name}, has_bp={bp_file_base64 is not None}", flush=True)
        print(f"[DEBUG] project_name={project_name}, selected_agents={selected_agents}", flush=True)
        print(f"[DEBUG] data_sources={data_sources}, priority={priority}", flush=True)

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
                user_id=user_id,
                # V5: Pass frontend configuration
                project_name=project_name,
                selected_agents=selected_agents,
                data_sources=data_sources,
                priority=priority,
                description=description
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


@app.post("/api/reports", tags=["Reports (V5)"])
async def save_report(report_data: Dict[str, Any]):
    """
    V5: Save a completed DD analysis report.

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
    import uuid
    from datetime import datetime

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
    saved_reports.append(saved_report)

    print(f"[REPORTS] Saved report {report_id} for {saved_report['company_name']}", flush=True)

    return {
        "success": True,
        "report_id": report_id,
        "message": "报告已成功保存"
    }


@app.get("/api/reports", tags=["Reports (V5)"])
async def get_reports():
    """
    V5: Get all saved reports.

    Returns a list of saved DD analysis reports sorted by creation time.
    """
    # Sort by created_at (newest first)
    sorted_reports = sorted(
        saved_reports,
        key=lambda r: r.get("created_at", ""),
        reverse=True
    )

    return {
        "success": True,
        "count": len(sorted_reports),
        "reports": sorted_reports
    }


@app.get("/api/reports/{report_id}", tags=["Reports (V5)"])
async def get_report(report_id: str):
    """
    V5: Get a specific report by ID.
    """
    report = next((r for r in saved_reports if r["id"] == report_id), None)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    return {
        "success": True,
        "report": report
    }


@app.delete("/api/reports/{report_id}", tags=["Reports (V5)"])
async def delete_report(report_id: str):
    """
    V5: Delete a report by ID.
    """
    global saved_reports

    # Find the report
    report_index = next((i for i, r in enumerate(saved_reports) if r["id"] == report_id), None)

    if report_index is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # Remove the report
    deleted_report = saved_reports.pop(report_index)

    print(f"[REPORTS] Deleted report {report_id} for {deleted_report.get('company_name')}", flush=True)

    return {
        "success": True,
        "message": "报告已成功删除",
        "deleted_report_id": report_id
    }


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


# ============================================================================
# V5: Dashboard Analytics APIs
# ============================================================================

@app.get("/api/dashboard/stats", tags=["Dashboard (V5)"])
async def get_dashboard_stats():
    """
    V5: Get dashboard statistics including:
    - Total reports count
    - Active analyses count
    - AI agents count
    - Success rate
    """
    from datetime import datetime, timedelta

    # Total reports
    total_reports = len(saved_reports)

    # Active analyses (sessions that are not completed)
    active_analyses = len([s for s in dd_sessions.values() if s.current_state not in ["completed", "error"]])

    # AI agents count (fixed number for now)
    ai_agents_count = 6  # market-analyst, financial-expert, team-evaluator, risk-assessor, tech-specialist, legal-advisor

    # Success rate (reports with status='completed' vs all reports)
    completed_reports = len([r for r in saved_reports if r.get("status") == "completed"])
    success_rate = (completed_reports / total_reports * 100) if total_reports > 0 else 0

    # Calculate trends (compare to previous period - using mock data for now)
    # In production, this should compare to data from a database
    reports_change = "+12.5%"  # Mock
    analyses_change = f"+{active_analyses}"
    agents_change = "0"
    success_rate_change = "+2.1%"  # Mock

    return {
        "success": True,
        "stats": {
            "total_reports": {
                "value": total_reports,
                "change": reports_change,
                "trend": "up"
            },
            "active_analyses": {
                "value": active_analyses,
                "change": analyses_change,
                "trend": "up" if active_analyses > 0 else "neutral"
            },
            "ai_agents": {
                "value": ai_agents_count,
                "change": agents_change,
                "trend": "neutral"
            },
            "success_rate": {
                "value": f"{success_rate:.1f}%",
                "change": success_rate_change,
                "trend": "up"
            }
        }
    }


@app.get("/api/dashboard/recent-reports", tags=["Dashboard (V5)"])
async def get_recent_reports(limit: int = 5):
    """
    V5: Get most recent reports for dashboard display.
    """
    from datetime import datetime

    # Sort by created_at (newest first) and limit
    sorted_reports = sorted(
        saved_reports,
        key=lambda r: r.get("created_at", ""),
        reverse=True
    )[:limit]

    # Format for dashboard display
    recent_reports = []
    for report in sorted_reports:
        # Calculate time ago
        created_at = datetime.fromisoformat(report.get("created_at", datetime.now().isoformat()))
        time_diff = datetime.now() - created_at

        if time_diff.days > 0:
            time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"

        # Count agents used
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


@app.get("/api/dashboard/trends", tags=["Dashboard (V5)"])
async def get_analysis_trends(days: int = 7):
    """
    V5: Get analysis trends data for the past N days.
    Returns daily counts of reports and analyses.
    """
    from datetime import datetime, timedelta
    from collections import defaultdict

    # Generate labels for the past N days
    labels = []
    end_date = datetime.now()
    for i in range(days - 1, -1, -1):
        date = end_date - timedelta(days=i)
        labels.append(date.strftime("%a"))  # Mon, Tue, Wed, etc.

    # Count reports by day
    reports_by_day = defaultdict(int)
    analyses_by_day = defaultdict(int)

    for report in saved_reports:
        created_at = datetime.fromisoformat(report.get("created_at", datetime.now().isoformat()))
        days_ago = (end_date - created_at).days
        if days_ago < days:
            day_label = created_at.strftime("%a")
            reports_by_day[day_label] += 1

    for session in dd_sessions.values():
        created_at = datetime.fromisoformat(session.created_at)
        days_ago = (end_date - created_at).days
        if days_ago < days:
            day_label = created_at.strftime("%a")
            analyses_by_day[day_label] += 1

    # Build data arrays matching the labels
    reports_data = [reports_by_day.get(label, 0) for label in labels]
    analyses_data = [analyses_by_day.get(label, 0) for label in labels]

    return {
        "success": True,
        "labels": labels,
        "datasets": {
            "reports": reports_data,
            "analyses": analyses_data
        }
    }


@app.get("/api/dashboard/agent-performance", tags=["Dashboard (V5)"])
async def get_agent_performance():
    """
    V5: Get agent performance/usage statistics.
    Returns the distribution of tasks by agent type.
    """
    from collections import defaultdict

    # Count agent usage from saved reports
    agent_usage = defaultdict(int)

    for report in saved_reports:
        steps = report.get("steps", [])
        for step in steps:
            # Map step titles to agent categories
            title = step.get("title", "").lower()
            if "market" in title or "市场" in title:
                agent_usage["market_analysis"] += 1
            elif "financial" in title or "财务" in title:
                agent_usage["financial_review"] += 1
            elif "team" in title or "团队" in title:
                agent_usage["team_evaluation"] += 1
            elif "risk" in title or "风险" in title:
                agent_usage["risk_assessment"] += 1

    # Get total for percentage calculation
    total = sum(agent_usage.values())

    # Return percentages
    if total > 0:
        performance = {
            "market_analysis": round(agent_usage["market_analysis"] / total * 100),
            "financial_review": round(agent_usage["financial_review"] / total * 100),
            "team_evaluation": round(agent_usage["team_evaluation"] / total * 100),
            "risk_assessment": round(agent_usage["risk_assessment"] / total * 100)
        }
    else:
        # Mock data if no reports
        performance = {
            "market_analysis": 35,
            "financial_review": 25,
            "team_evaluation": 20,
            "risk_assessment": 20
        }

    return {
        "success": True,
        "performance": performance
    }


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


# ============================================================================
# V4: Roundtable Discussion WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/roundtable")
async def websocket_roundtable_endpoint(websocket: WebSocket):
    """
    圆桌讨论 WebSocket 端点

    支持多智能体投资分析讨论

    Client sends:
    {
        "action": "start_discussion",
        "topic": "特斯拉2024Q4投资价值分析",
        "company_name": "特斯拉",
        "context": {...}  // Optional: 公司数据、财务数据等上下文
    }

    Server responses:
    {
        "type": "agent_event",
        "event": {
            "agent_name": "市场分析师",
            "event_type": "thinking" | "message" | "completed",
            "message": "...",
            "data": {...}
        }
    }

    OR:
    {
        "type": "discussion_complete",
        "summary": {...}
    }
    """
    await websocket.accept()
    print(f"[ROUNDTABLE] WebSocket connection accepted", flush=True)

    # Import roundtable components
    from .core.roundtable import Meeting, Message, MessageType
    from .core.roundtable.investment_agents import (
        create_leader,
        create_market_analyst,
        create_financial_expert,
        create_risk_assessor,
        create_team_evaluator
    )
    from .core.agent_event_bus import AgentEventBus

    session_id = None

    try:
        # Wait for initial request
        initial_request = await websocket.receive_json()
        print(f"[ROUNDTABLE] Received request: {initial_request}", flush=True)

        action = initial_request.get("action")

        if action == "start_discussion":
            topic = initial_request.get("topic", "投资价值分析")
            company_name = initial_request.get("company_name", "目标公司")
            context = initial_request.get("context", {})

            # Generate session ID
            session_id = f"roundtable_{company_name}_{uuid.uuid4().hex[:8]}"
            print(f"[ROUNDTABLE] Starting discussion for: {company_name}, session: {session_id}", flush=True)

            # Create agent event bus for real-time updates
            event_bus = AgentEventBus()
            await event_bus.subscribe(websocket)

            # Create expert team
            agents = [
                create_leader(),
                create_market_analyst(),
                create_financial_expert(),
                create_team_evaluator(),
                create_risk_assessor()
            ]

            print(f"[ROUNDTABLE] Created {len(agents)} agents", flush=True)

            # Send agent list to frontend
            await websocket.send_json({
                "type": "agents_ready",
                "session_id": session_id,
                "agents": [agent.name for agent in agents],
                "message": f"圆桌讨论准备就绪，共{len(agents)}位专家参与"
            })

            # Create meeting
            meeting = Meeting(
                agents=agents,
                agent_event_bus=event_bus,
                max_turns=15,
                max_duration_seconds=300
            )

            # Build initial message based on context
            initial_content = f"各位专家好！今天我们要讨论{company_name}的{topic}。"

            # Add context if available
            if context:
                if context.get("summary"):
                    initial_content += f"\n\n公司概况：\n{context['summary']}"
                if context.get("financial_data"):
                    initial_content += f"\n\n关键财务数据已提供。"
                if context.get("market_data"):
                    initial_content += f"\n\n市场数据已提供。"

            initial_content += "\n\n请各位从自己的专业角度分析，给出投资建议。请领导者主持讨论。"

            initial_message = Message(
                sender="主持人",
                recipient="ALL",
                content=initial_content
            )

            print(f"[ROUNDTABLE] Starting meeting...", flush=True)

            # Run discussion
            try:
                result = await meeting.run(initial_message=initial_message)

                print(f"[ROUNDTABLE] Discussion completed", flush=True)

                # Send completion summary
                await websocket.send_json({
                    "type": "discussion_complete",
                    "session_id": session_id,
                    "summary": result
                })

            except Exception as meeting_error:
                print(f"[ROUNDTABLE] Meeting error: {meeting_error}", flush=True)
                import traceback
                traceback.print_exc()

                await websocket.send_json({
                    "type": "error",
                    "message": f"讨论过程中出现错误: {str(meeting_error)}"
                })

            finally:
                # Unsubscribe event bus
                await event_bus.unsubscribe(websocket)

        else:
            await websocket.send_json({
                "type": "error",
                "message": f"未知的操作: {action}"
            })

    except WebSocketDisconnect:
        print(f"[ROUNDTABLE] Client disconnected from session {session_id}", flush=True)
    except Exception as e:
        print(f"[ROUNDTABLE] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

        try:
            if websocket.client_state == 1:  # OPEN
                await websocket.send_json({
                    "type": "error",
                    "message": f"圆桌讨论出现错误: {str(e)}"
                })
        except Exception as send_error:
            print(f"[ROUNDTABLE] Failed to send error message: {send_error}", flush=True)


# ============================================================================
# V4: Intelligent Conversation WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/conversation")
async def websocket_conversation_endpoint(websocket: WebSocket):
    """
    V4 智能对话WebSocket端点

    支持意图识别、对话式交互、用户确认后再启动分析

    Client sends:
    {
        "type": "message",
        "content": "用户输入的消息",
        "bp_file_base64": "...",  // Optional
        "bp_filename": "..."       // Optional
    }

    OR:
    {
        "type": "action",
        "action": "start_dd_analysis",  // 或其他action
        "company_name": "...",
        "bp_file_base64": "...",  // Optional
        "bp_filename": "...",      // Optional
        "user_id": "..."
    }

    Server responses:
    {
        "type": "intent_recognized",
        "intent": {...},
        "message": "...",
        "options": [...]
    }

    OR:
    {
        "type": "dd_progress",
        "session_id": "...",
        "status": "...",
        "current_step": {...}
    }
    """
    await websocket.accept()
    print(f"[CONVERSATION] WebSocket connection accepted", flush=True)

    # Initialize intent recognizer and conversation manager
    intent_recognizer = IntentRecognizer(llm_gateway_url=LLM_GATEWAY_URL)
    conversation_manager = ConversationManager(intent_recognizer)

    session_id = None

    try:
        while True:
            # Receive message from client
            try:
                message = await websocket.receive_json()
                print(f"[CONVERSATION] Received message: {message}", flush=True)
            except Exception as recv_error:
                print(f"[CONVERSATION] Error receiving message: {recv_error}", flush=True)
                break

            message_type = message.get("type", "message")

            if message_type == "message":
                # User sent a text message - recognize intent
                user_input = message.get("content", "")

                if not user_input:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请输入消息内容"
                    })
                    continue

                # Process message with conversation manager
                response = await conversation_manager.process_message(user_input)

                # Send intent recognition result
                await websocket.send_json({
                    "type": "intent_recognized",
                    "intent": {
                        "type": response["intent"].type,
                        "confidence": response["intent"].confidence,
                        "entities": response["intent"].extracted_entities
                    },
                    "response_type": response["response_type"],
                    "message": response.get("message", ""),
                    "options": response.get("options", []),
                    "suggested_action": response.get("suggested_action"),
                    "file_upload_hint": response.get("file_upload_hint")
                })
                print(f"[CONVERSATION] Sent intent recognition response", flush=True)

            elif message_type == "action":
                # User confirmed an action - execute it
                action = message.get("action")
                company_name = message.get("company_name", "")
                bp_file_base64 = message.get("bp_file_base64")
                bp_filename = message.get("bp_filename", "business_plan.pdf")
                user_id = message.get("user_id", "default_user")

                if action == "start_dd_analysis":
                    # Start DD analysis workflow
                    print(f"[CONVERSATION] Starting DD analysis for: {company_name}", flush=True)

                    # Generate session ID
                    session_id = f"dd_{company_name}_{uuid.uuid4().hex[:8]}"

                    # Decode BP file if provided
                    import base64
                    bp_file_content = None
                    if bp_file_base64:
                        try:
                            bp_file_content = base64.b64decode(bp_file_base64)
                            print(f"[CONVERSATION] Decoded BP file: {len(bp_file_content)} bytes", flush=True)
                        except Exception as decode_error:
                            print(f"[CONVERSATION] Failed to decode BP file: {decode_error}", flush=True)
                            await websocket.send_json({
                                "type": "error",
                                "message": "BP文件解码失败"
                            })
                            continue

                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "action_started",
                        "action": "dd_analysis",
                        "session_id": session_id,
                        "message": f"正在为「{company_name}」启动完整尽职调查分析..."
                    })

                    # Create and run DD state machine
                    try:
                        state_machine = DDStateMachine(
                            session_id=session_id,
                            company_name=company_name,
                            bp_file_content=bp_file_content,
                            bp_filename=bp_filename,
                            user_id=user_id
                        )

                        # Store session
                        dd_sessions[session_id] = state_machine.get_current_context()

                        # Execute workflow (this will send progress updates via websocket)
                        await state_machine.run(websocket)

                        # Update stored session
                        dd_sessions[session_id] = state_machine.get_current_context()

                        print(f"[CONVERSATION] DD analysis completed for {session_id}", flush=True)

                    except Exception as dd_error:
                        print(f"[CONVERSATION] DD analysis failed: {dd_error}", flush=True)
                        import traceback
                        traceback.print_exc()

                        await websocket.send_json({
                            "type": "error",
                            "message": f"分析过程中出现错误: {str(dd_error)}"
                        })

                elif action == "quick_overview":
                    # Quick overview (simplified analysis)
                    print(f"[CONVERSATION] Starting quick overview for: {company_name}", flush=True)

                    await websocket.send_json({
                        "type": "action_started",
                        "action": "quick_overview",
                        "message": f"正在快速获取「{company_name}」的基本信息..."
                    })

                    # TODO: Implement quick overview logic
                    # For now, send a simple response
                    await websocket.send_json({
                        "type": "quick_overview_result",
                        "company_name": company_name,
                        "summary": "快速概览功能即将推出..."
                    })

                elif action == "free_chat":
                    # Free chat mode
                    print(f"[CONVERSATION] Entering free chat mode", flush=True)

                    await websocket.send_json({
                        "type": "chat_mode_active",
                        "message": "已进入自由对话模式。有什么我可以帮助您的吗？"
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"未知的操作: {action}"
                    })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知的消息类型: {message_type}"
                })

    except WebSocketDisconnect:
        print(f"[CONVERSATION] Client disconnected", flush=True)
    except Exception as e:
        print(f"[CONVERSATION] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

        try:
            if websocket.client_state == 1:  # OPEN
                await websocket.send_json({
                    "type": "error",
                    "message": f"对话过程中出现错误: {str(e)}"
                })
        except Exception as send_error:
            print(f"[CONVERSATION] Failed to send error message: {send_error}", flush=True)
