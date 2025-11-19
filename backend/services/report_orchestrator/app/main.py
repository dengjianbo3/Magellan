# backend/services/report_orchestrator/app/main.py
import httpx
import asyncio
import json
import re
import os
import uuid
import time
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

# V5: Import Redis session store
from .core.session_store import SessionStore

# Phase 2: Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

# Phase 2: Structured logging
from .core.logging_config import configure_logging, get_logger
import os

# Phase 2: Knowledge Base services
from .services.vector_store import VectorStoreService
from .services.document_parser import DocumentParser
from .services.rag_service import RAGService
import tempfile
import shutil

# Configure logging (JSON in production, console in development)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
JSON_LOGS = os.getenv("JSON_LOGS", "false").lower() == "true"
configure_logging(log_level=LOG_LEVEL, json_logs=JSON_LOGS)
logger = get_logger(__name__)

# --- Service Discovery ---
EXTERNAL_DATA_URL = "http://external_data_service:8006"
LLM_GATEWAY_URL = "http://llm_gateway:8003"
FILE_SERVICE_URL = "http://file_service:8001"

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

# Phase 2: Initialize Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["System (Phase 2)"])

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

# V5: Initialize Redis Session Store for persistence
try:
    session_store = SessionStore()  # Uses REDIS_URL from environment
    print("[main.py] ✅ SessionStore initialized successfully")
except Exception as e:
    print(f"[main.py] ❌ Failed to initialize SessionStore: {e}")
    print("[main.py] ⚠️  Falling back to in-memory storage")
    session_store = None

# V5: Backward compatibility - keep in-memory storage as fallback
dd_sessions: Dict[str, DDSessionContext] = {}  # Fallback if Redis fails
saved_reports: List[Dict[str, Any]] = []  # Fallback if Redis fails

# V5: Dashboard analytics storage
dashboard_analytics = {
    "daily_stats": [],  # Daily reports/analyses counts
    "agent_usage": {}   # Agent usage statistics
}

# Phase 2: Initialize Vector Store for Knowledge Base
try:
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    vector_store = VectorStoreService(qdrant_url=QDRANT_URL)
    print("[main.py] ✅ VectorStore initialized successfully")
except Exception as e:
    print(f"[main.py] ❌ Failed to initialize VectorStore: {e}")
    print("[main.py] ⚠️  Knowledge base features will be disabled")
    vector_store = None

# Phase 2: Initialize RAG Service for Advanced Search
try:
    if vector_store:
        rag_service = RAGService(vector_store_service=vector_store)
        # Build BM25 index on startup
        rag_service.refresh_bm25_index()
        print("[main.py] ✅ RAG Service initialized successfully")
    else:
        rag_service = None
        print("[main.py] ⚠️  RAG Service disabled (VectorStore not available)")
except Exception as e:
    print(f"[main.py] ❌ Failed to initialize RAG Service: {e}")
    print("[main.py] ⚠️  Advanced search features will be disabled")
    rag_service = None


# ============================================================================
# V5: Storage Helper Functions (Redis with Fallback)
# ============================================================================

def save_session(session_id: str, context: DDSessionContext) -> bool:
    """Save session to Redis or fallback to in-memory storage."""
    if session_store:
        # Convert DDSessionContext to dict for JSON serialization
        context_dict = context.model_dump() if hasattr(context, 'model_dump') else context.dict()
        return session_store.save_session(session_id, context_dict, ttl_days=30)
    else:
        # Fallback to in-memory
        dd_sessions[session_id] = context
        return True


def get_session(session_id: str) -> Optional[DDSessionContext]:
    """Get session from Redis or fallback to in-memory storage."""
    if session_store:
        context_dict = session_store.get_session(session_id)
        if context_dict:
            return DDSessionContext(**context_dict)
        return None
    else:
        # Fallback to in-memory
        return dd_sessions.get(session_id)


def session_exists(session_id: str) -> bool:
    """Check if session exists."""
    if session_store:
        return session_store.session_exists(session_id)
    else:
        return session_id in dd_sessions


def _save_report_to_store(report_id: str, report_data: Dict[str, Any]) -> bool:
    """Save report to Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.save_report(report_id, report_data, ttl_days=365)
    else:
        # Fallback to in-memory
        saved_reports.append(report_data)
        return True


def _get_report_from_store(report_id: str) -> Optional[Dict[str, Any]]:
    """Get report from Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.get_report(report_id)
    else:
        # Fallback to in-memory
        return next((r for r in saved_reports if r["id"] == report_id), None)


def _get_all_reports_from_store(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all reports from Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.get_all_reports(limit=limit)
    else:
        # Fallback to in-memory
        return saved_reports[:limit]


def _delete_report_from_store(report_id: str) -> bool:
    """Delete report from Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.delete_report(report_id)
    else:
        # Fallback to in-memory
        global saved_reports
        report_index = next((i for i, r in enumerate(saved_reports) if r["id"] == report_id), None)
        if report_index is not None:
            saved_reports.pop(report_index)
            return True
        return False


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
        bp_file_base64 = initial_request.get("bp_file_base64")  # Legacy: base64 encoded file
        file_id = initial_request.get("file_id")  # V5: File ID from upload API
        bp_filename = initial_request.get("bp_filename", "business_plan.pdf")
        user_id = initial_request.get("user_id", "default_user")

        # V5: Extract frontend configuration
        project_name = initial_request.get("project_name")
        selected_agents = initial_request.get("selected_agents", [])
        data_sources = initial_request.get("data_sources", [])
        priority = initial_request.get("priority", "normal")
        description = initial_request.get("description")

        print(f"[DEBUG] company_name={company_name}, has_bp_base64={bp_file_base64 is not None}, file_id={file_id}", flush=True)
        print(f"[DEBUG] project_name={project_name}, selected_agents={selected_agents}", flush=True)
        print(f"[DEBUG] data_sources={data_sources}, priority={priority}", flush=True)

        if not company_name:
            print(f"[DEBUG] Missing company_name, closing connection", flush=True)
            await websocket.close(code=1008, reason="company_name is required")
            return

        # 2. Generate session ID
        session_id = f"dd_{company_name}_{uuid.uuid4().hex[:8]}"
        print(f"[DEBUG] Generated session_id: {session_id}", flush=True)

        # 3. Load BP file content
        import base64
        bp_file_content = None

        # V5: Try file_id first (new approach)
        if file_id:
            try:
                print(f"[DEBUG] Loading file from File Service: {file_id}", flush=True)
                # Load file from shared volume
                file_path = f"/var/uploads/{file_id}"

                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        bp_file_content = f.read()
                    print(f"[DEBUG] Loaded file from disk: {len(bp_file_content)} bytes", flush=True)
                else:
                    print(f"[ERROR] File not found: {file_path}", flush=True)
                    await websocket.send_json({
                        "status": "error",
                        "message": f"文件未找到: {file_id}"
                    })
                    await websocket.close(code=1011, reason="File not found")
                    return

            except Exception as file_load_error:
                print(f"[ERROR] Failed to load file {file_id}: {file_load_error}", flush=True)
                import traceback
                traceback.print_exc()
                await websocket.send_json({
                    "status": "error",
                    "message": f"文件加载失败: {str(file_load_error)}"
                })
                await websocket.close(code=1011, reason="File load error")
                return

        # Legacy: Fall back to base64 encoded file
        elif bp_file_base64:
            try:
                bp_file_content = base64.b64decode(bp_file_base64)
                print(f"[DEBUG] Decoded BP file from base64: {len(bp_file_content)} bytes", flush=True)
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
        save_session(session_id, state_machine.get_current_context())
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
        save_session(session_id, state_machine.get_current_context())

        # 7. Auto-save report after workflow completion
        try:
            context = state_machine.get_current_context()
            if context.get("current_state") == "COMPLETED":
                from datetime import datetime

                # Generate report ID
                report_id = f"report_{uuid.uuid4().hex[:12]}"

                # Serialize steps (convert Pydantic models to dict)
                steps_data = []
                if hasattr(state_machine, 'steps'):
                    for step in state_machine.steps:
                        if hasattr(step, 'dict'):
                            steps_data.append(step.dict())
                        elif isinstance(step, dict):
                            steps_data.append(step)

                # Create report data
                saved_report = {
                    "id": report_id,
                    "session_id": session_id,
                    "project_name": project_name or company_name,
                    "company_name": company_name,
                    "analysis_type": "due-diligence",
                    "preliminary_im": context.get("preliminary_im"),
                    "team_analysis": context.get("team_analysis"),
                    "market_analysis": context.get("market_analysis"),
                    "steps": steps_data,
                    "status": "completed",
                    "created_at": context.get("created_at", datetime.now().isoformat()),
                    "saved_at": datetime.now().isoformat()
                }

                # Save report to store
                _save_report_to_store(report_id, saved_report)

                print(f"[REPORTS] Auto-saved report {report_id} for {company_name}", flush=True)

                # Notify frontend about saved report
                await websocket.send_json({
                    "type": "report_saved",
                    "report_id": report_id,
                    "session_id": session_id,
                    "message": "报告已自动保存"
                })
        except Exception as save_error:
            print(f"[ERROR] Failed to auto-save report: {save_error}", flush=True)
            import traceback
            traceback.print_exc()
        
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
    save_session(session_id, state_machine.get_current_context())

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
        save_session(state_machine.context.session_id, state_machine.get_current_context())
    except Exception as e:
        print(f"Background DD workflow error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# V5: BP File Upload API
# ============================================================================

@app.post("/api/upload_bp", tags=["File Upload (V5)"])
async def upload_bp_file(
    file: UploadFile = File(...),
    max_size_mb: int = 10
):
    """
    V5: Upload BP (Business Plan) file to File Service.

    Supports: PDF, Word (.doc, .docx), Excel (.xls, .xlsx)

    Returns:
        file_id: Unique identifier for the uploaded file
        original_filename: Original name of the uploaded file
        file_size: Size of the file in bytes

    Usage:
        1. Frontend uploads BP file to this endpoint
        2. Get file_id from response
        3. Send file_id via WebSocket to start DD analysis
    """
    try:
        # 1. Validate file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_extension}. 支持的类型: {', '.join(allowed_extensions)}"
            )

        # 2. Read file content for size validation
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size (convert MB to bytes)
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {file_size / (1024*1024):.2f}MB. 最大允许: {max_size_mb}MB"
            )

        # 3. Forward file to File Service
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Reset file pointer and create new UploadFile for forwarding
            files = {
                "file": (file.filename, file_content, file.content_type)
            }

            response = await client.post(
                f"{FILE_SERVICE_URL}/upload",
                files=files
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"文件上传失败: {response.text}"
                )

            # 4. Get file_id from File Service response
            upload_result = response.json()
            file_id = upload_result.get("file_id")

            print(f"[UPLOAD] ✅ File uploaded: {file.filename} → {file_id} ({file_size} bytes)")

            return {
                "success": True,
                "file_id": file_id,
                "original_filename": file.filename,
                "file_size": file_size,
                "file_extension": file_extension,
                "message": "文件上传成功"
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD] ❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )


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
    _save_report_to_store(report_id, saved_report)

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
    # Get all reports from store
    all_reports = _get_all_reports_from_store(limit=100)

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


@app.get("/api/reports/{report_id}", tags=["Reports (V5)"])
async def get_report(report_id: str):
    """
    V5: Get a specific report by ID.
    """
    report = _get_report_from_store(report_id)

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
    # Get report before deleting (for logging)
    report = _get_report_from_store(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # Delete the report
    success = _delete_report_from_store(report_id)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete report {report_id}")

    print(f"[REPORTS] Deleted report {report_id} for {report.get('company_name')}", flush=True)

    return {
        "success": True,
        "message": "报告已成功删除",
        "deleted_report_id": report_id
    }


@app.get("/api/reports/{report_id}/export/pdf", tags=["Reports (Phase 2)"])
async def export_report_to_pdf(report_id: str, language: str = "zh"):
    """
    Phase 2: Export a report to PDF format.

    Args:
        report_id: 报告ID
        language: 语言设置 ("zh" or "en")

    Returns:
        PDF file as downloadable response
    """
    from fastapi.responses import FileResponse
    from .exporters.pdf_generator import generate_pdf_report
    import tempfile
    import os

    # Get report data
    report = _get_report_from_store(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        # Create temporary PDF file
        temp_dir = tempfile.gettempdir()
        company_name = report.get('company_name', 'Company').replace(' ', '_')
        pdf_filename = f"{company_name}_Report_{report_id[:8]}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)

        # Generate PDF
        print(f"[PDF_EXPORT] Generating PDF for report {report_id}, language={language}", flush=True)
        generate_pdf_report(report, pdf_path, language=language)
        print(f"[PDF_EXPORT] PDF generated successfully: {pdf_path}", flush=True)

        # Return PDF file
        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=pdf_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{pdf_filename}"'
            }
        )

    except Exception as e:
        print(f"[PDF_EXPORT] Error generating PDF: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@app.get("/api/reports/{report_id}/export/word", tags=["Reports (Phase 2)"])
async def export_report_to_word(report_id: str, language: str = "zh"):
    """
    Phase 2: Export a report to Word format.

    Args:
        report_id: 报告ID
        language: 语言设置 ("zh" or "en")

    Returns:
        Word file as downloadable response
    """
    from fastapi.responses import FileResponse
    from .exporters.word_generator import generate_word_report
    import tempfile
    import os

    # Get report data
    report = _get_report_from_store(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        # Create temporary Word file
        temp_dir = tempfile.gettempdir()
        company_name = report.get('company_name', 'Company').replace(' ', '_')
        word_filename = f"{company_name}_Report_{report_id[:8]}.docx"
        word_path = os.path.join(temp_dir, word_filename)

        # Generate Word
        print(f"[WORD_EXPORT] Generating Word for report {report_id}, language={language}", flush=True)
        generate_word_report(report, word_path, language=language)
        print(f"[WORD_EXPORT] Word generated successfully: {word_path}", flush=True)

        # Return Word file
        return FileResponse(
            path=word_path,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            filename=word_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{word_filename}"'
            }
        )

    except Exception as e:
        print(f"[WORD_EXPORT] Error generating Word: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Word: {str(e)}"
        )


@app.get("/api/reports/{report_id}/export/excel", tags=["Reports (Phase 2)"])
async def export_report_to_excel(report_id: str, language: str = "zh"):
    """
    Phase 2: Export a report to Excel format.

    Args:
        report_id: 报告ID
        language: 语言设置 ("zh" or "en")

    Returns:
        Excel file as downloadable response
    """
    from fastapi.responses import FileResponse
    from .exporters.excel_generator import generate_excel_report
    import tempfile
    import os

    # Get report data
    report = _get_report_from_store(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        # Create temporary Excel file
        temp_dir = tempfile.gettempdir()
        company_name = report.get('company_name', 'Company').replace(' ', '_')
        excel_filename = f"{company_name}_Report_{report_id[:8]}.xlsx"
        excel_path = os.path.join(temp_dir, excel_filename)

        # Generate Excel
        print(f"[EXCEL_EXPORT] Generating Excel for report {report_id}, language={language}", flush=True)
        generate_excel_report(report, excel_path, language=language)
        print(f"[EXCEL_EXPORT] Excel generated successfully: {excel_path}", flush=True)

        # Return Excel file
        return FileResponse(
            path=excel_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=excel_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{excel_filename}"'
            }
        )

    except Exception as e:
        print(f"[EXCEL_EXPORT] Error generating Excel: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Excel: {str(e)}"
        )


@app.get("/api/reports/{report_id}/charts/{chart_type}", tags=["Reports (Phase 2)"])
async def generate_report_chart(report_id: str, chart_type: str, language: str = "zh"):
    """
    Phase 2: Generate chart for a specific report.

    Args:
        report_id: Report ID
        chart_type: Type of chart (revenue, profit, financial_health, market_share, market_growth, risk_matrix, team_radar)
        language: Language setting ("zh" or "en")

    Returns:
        PNG image of the chart
    """
    from fastapi.responses import FileResponse
    from .exporters.chart_generator import generate_chart_for_report
    import tempfile
    import os

    # Get report data
    report = _get_report_from_store(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        # Prepare chart data based on type
        chart_data = _prepare_chart_data(report, chart_type)

        # Create temporary chart file
        temp_dir = tempfile.gettempdir()
        chart_filename = f"{report_id}_{chart_type}.png"
        chart_path = os.path.join(temp_dir, chart_filename)

        # Generate chart
        print(f"[CHART] Generating {chart_type} chart for report {report_id}, language={language}", flush=True)
        generate_chart_for_report(chart_type, chart_data, chart_path, language=language)
        print(f"[CHART] Chart generated successfully: {chart_path}", flush=True)

        # Return chart file
        return FileResponse(
            path=chart_path,
            media_type='image/png',
            filename=chart_filename,
            headers={
                "Content-Disposition": f'inline; filename="{chart_filename}"'
            }
        )

    except Exception as e:
        print(f"[CHART] Error generating chart: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate chart: {str(e)}"
        )


def _prepare_chart_data(report: Dict[str, Any], chart_type: str) -> Dict[str, Any]:
    """
    Prepare chart data from report based on chart type
    从报告中准备图表数据
    """
    preliminary_im = report.get('preliminary_im', {})
    market_analysis = report.get('market_analysis', {})
    team_analysis = report.get('team_analysis', {})

    if chart_type == 'revenue':
        # Extract or mock revenue data
        return {
            'years': [2021, 2022, 2023],
            'revenue': [1000000, 1500000, 2200000]  # Mock data
        }

    elif chart_type == 'profit':
        return {
            'years': [2021, 2022, 2023],
            'gross_margin': [0.45, 0.52, 0.58],
            'net_margin': [0.15, 0.22, 0.28]
        }

    elif chart_type == 'financial_health':
        return {
            'liquidity': 0.75,
            'solvency': 0.68,
            'profitability': 0.72,
            'efficiency': 0.65,
            'growth': 0.80
        }

    elif chart_type == 'market_share':
        return {
            'companies': [report.get('company_name', 'Target'), 'Competitor A', 'Competitor B', 'Others'],
            'shares': [15, 25, 20, 40]
        }

    elif chart_type == 'market_growth':
        return {
            'years': [2019, 2020, 2021, 2022, 2023],
            'market_size': [500, 650, 850, 1100, 1400],
            'growth_rate': [None, 30, 31, 29, 27]
        }

    elif chart_type == 'risk_matrix':
        risks_data = preliminary_im.get('risks', [])
        if isinstance(risks_data, list) and risks_data:
            # Convert risk data to matrix format
            risks = []
            for risk in risks_data[:5]:  # Limit to 5 risks
                if isinstance(risk, dict):
                    risks.append({
                        'name': risk.get('name', 'Unknown'),
                        'probability': 0.5,  # Mock - ideally extracted from risk data
                        'impact': 0.6
                    })
            return risks if risks else [{'name': 'Sample Risk', 'probability': 0.5, 'impact': 0.5}]
        return [{'name': 'Market Risk', 'probability': 0.6, 'impact': 0.7}]

    elif chart_type == 'team_radar':
        return {
            'technical': 0.8,
            'market': 0.7,
            'leadership': 0.75,
            'execution': 0.72,
            'finance': 0.65,
            'innovation': 0.78
        }

    else:
        raise ValueError(f"Unknown chart type: {chart_type}")


@app.get("/health", tags=["System (Phase 2)"])
async def health_check():
    """
    Phase 2: System health check endpoint.

    Returns:
        Health status of the service and its dependencies
    """
    import time
    from datetime import datetime

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "report_orchestrator",
        "version": "3.0.0-phase2",
        "checks": {}
    }

    # Check Redis connection
    try:
        session_store.redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Connected to Redis"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }

    # Check LLM Gateway (optional - don't fail health check if down)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://llm_gateway:8002/health", timeout=2.0)
            if response.status_code == 200:
                health_status["checks"]["llm_gateway"] = {
                    "status": "healthy",
                    "message": "LLM Gateway is reachable"
                }
            else:
                health_status["checks"]["llm_gateway"] = {
                    "status": "degraded",
                    "message": f"LLM Gateway returned status {response.status_code}"
                }
    except Exception as e:
        health_status["checks"]["llm_gateway"] = {
            "status": "degraded",
            "message": f"LLM Gateway unreachable: {str(e)}"
        }

    # System info
    health_status["system"] = {
        "python_version": "3.11",
        "uptime_seconds": int(time.time() - startup_time) if 'startup_time' in globals() else 0
    }

    return health_status


# Track startup time for uptime calculation
startup_time = time.time()


@app.get("/dd_session/{session_id}", tags=["DD Workflow (V3)"])
async def get_dd_session(session_id: str):
    """Query DD session status"""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    context = get_session(session_id)

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

    # Get stats from Redis if available
    if session_store:
        redis_stats = session_store.get_stats()
        total_reports = redis_stats.get('reports', 0)
        # Note: active_analyses not available in Redis stats yet, use 0 for now
        active_analyses = 0
    else:
        # Fallback to in-memory stats
        total_reports = len(saved_reports)
        active_analyses = len([s for s in dd_sessions.values() if s.current_state not in ["completed", "error"]])

    # AI agents count (fixed number for now)
    ai_agents_count = 6  # market-analyst, financial-expert, team-evaluator, risk-assessor, tech-specialist, legal-advisor

    # Success rate (reports with status='completed' vs all reports)
    all_reports = _get_all_reports_from_store(limit=1000)  # Get a large number for stats
    completed_reports = len([r for r in all_reports if r.get("status") == "completed"])
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

    # Get reports from store and sort
    all_reports = _get_all_reports_from_store(limit=limit*2)  # Get more than needed
    sorted_reports = sorted(
        all_reports,
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

    # Get all reports from store
    all_reports = _get_all_reports_from_store(limit=1000)
    for report in all_reports:
        created_at = datetime.fromisoformat(report.get("created_at", datetime.now().isoformat()))
        days_ago = (end_date - created_at).days
        if days_ago < days:
            day_label = created_at.strftime("%a")
            reports_by_day[day_label] += 1

    # Note: Session-based analytics not available with Redis yet
    # Using only report data for now
    if not session_store:
        # Fallback: use in-memory sessions
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

    # Get all reports from store
    all_reports = _get_all_reports_from_store(limit=1000)
    for report in all_reports:
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
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    context = get_session(session_id)
    
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
# V4: Roundtable Discussion APIs
# ============================================================================

@app.post("/api/roundtable/generate_summary", tags=["Roundtable"])
async def generate_roundtable_summary(request: dict):
    """
    根据圆桌讨论历史生成会议纪要

    Request body:
    {
        "topic": "讨论主题",
        "messages": [{speaker, content, timestamp}],
        "participants": ["leader", "market-analyst", ...],
        "rounds": 5
    }
    """
    try:
        topic = request.get("topic", "投资讨论")
        messages = request.get("messages", [])
        participants = request.get("participants", [])
        rounds = request.get("rounds", 0)
        language = request.get("language", "zh")  # 获取语言偏好

        # 构建对话历史
        dialogue_text = "\n\n".join([
            f"【{msg.get('speaker')}】\n{msg.get('content')}"
            for msg in messages
        ])

        # 使用LLM生成会议纪要 - 根据语言选择prompt
        llm_service_url = LLM_GATEWAY_BASE_URL

        if language == "en":
            summary_prompt = f"""Based on the following roundtable discussion, generate a professional meeting minutes.

Discussion Topic: {topic}
Participants: {', '.join(participants)}
Discussion Rounds: {rounds}

Discussion Content:
{dialogue_text}

Please generate meeting minutes in the following format:

## Meeting Minutes

**Topic**: {topic}
**Participants**: {', '.join(participants)}
**Date & Time**: [Current time]

### 1. Key Viewpoints Summary
[Summarize main viewpoints of each expert, list by bullet points]

### 2. Key Discussion Points
[List key issues and disagreements in the discussion]

### 3. Consensus Reached
[List conclusions agreed upon by all parties]

### 4. Action Recommendations
[Specific recommendations based on the discussion]

### 5. Risk Alerts
[Risk factors mentioned in the discussion]

Please present in a professional and concise manner with clear logic.
"""
        else:
            summary_prompt = f"""基于以下圆桌讨论内容，生成一份专业的会议纪要。

讨论主题：{topic}
参与专家：{', '.join(participants)}
讨论轮次：{rounds}

讨论内容：
{dialogue_text}

请按以下格式生成会议纪要：

## 会议纪要

**会议主题**: {topic}
**参与人员**: {', '.join(participants)}
**讨论时间**: [当前时间]

### 一、核心观点总结
[总结各专家的主要观点，分点列出]

### 二、关键讨论点
[列出讨论中的关键问题和分歧点]

### 三、达成的共识
[列出各方达成一致的结论]

### 四、行动建议
[基于讨论提出的具体建议]

### 五、风险提示
[讨论中提到的风险因素]

请以专业、简洁的方式呈现，确保逻辑清晰。
"""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{llm_service_url}/v1/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": "你是一位专业的会议记录员，擅长总结和提炼会议要点。"},
                        {"role": "user", "content": summary_prompt}
                    ],
                    "temperature": 0.3
                }
            )

            if response.status_code == 200:
                llm_response = response.json()
                summary = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")

                return {
                    "success": True,
                    "summary": summary
                }
            else:
                raise HTTPException(status_code=500, detail="LLM服务调用失败")

    except Exception as e:
        print(f"[ERROR] Failed to generate roundtable summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            language = initial_request.get("language", "zh")  # 获取语言偏好，默认中文

            # Generate session ID
            session_id = f"roundtable_{company_name}_{uuid.uuid4().hex[:8]}"
            print(f"[ROUNDTABLE] Starting discussion for: {company_name}, session: {session_id}", flush=True)

            # Create agent event bus for real-time updates
            event_bus = AgentEventBus()
            await event_bus.subscribe(websocket)

            # Create expert team with language preference
            agents = [
                create_leader(language),
                create_market_analyst(language),
                create_financial_expert(language),
                create_team_evaluator(language),
                create_risk_assessor(language)
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
                        save_session(session_id, state_machine.get_current_context())

                        # Execute workflow (this will send progress updates via websocket)
                        await state_machine.run(websocket)

                        # Update stored session
                        save_session(session_id, state_machine.get_current_context())

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

# ============================================================================
# Phase 2: Knowledge Base Management APIs
# ============================================================================

@app.post("/api/knowledge/upload", tags=["Knowledge Base (Phase 2)"])
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None)
):
    """
    Upload a document to the knowledge base
    
    Supports: PDF, DOCX, TXT
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        # Parse document
        parsed_doc = DocumentParser.parse_document(temp_path)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if not parsed_doc['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse document: {parsed_doc['metadata'].get('error', 'Unknown error')}"
            )
        
        text = parsed_doc['text']
        if not text.strip():
            raise HTTPException(status_code=400, detail="Document contains no extractable text")
        
        # Chunk text for better retrieval
        chunks = DocumentParser.chunk_text(text, chunk_size=500, chunk_overlap=50)
        
        # Prepare metadata
        base_metadata = {
            "title": title or file.filename,
            "filename": file.filename,
            "category": category or "general",
            "file_type": file_ext[1:],  # Remove dot
            **parsed_doc['metadata']
        }
        
        # Add chunks to vector store
        doc_ids = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata['chunk_index'] = i
            chunk_metadata['total_chunks'] = len(chunks)
            
            doc_id = vector_store.add_document(
                text=chunk,
                metadata=chunk_metadata
            )
            doc_ids.append(doc_id)
        
        logger.info(f"Uploaded document: {file.filename}, {len(chunks)} chunks")
        
        return {
            "success": True,
            "document_ids": doc_ids,
            "num_chunks": len(chunks),
            "metadata": base_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@app.get("/api/knowledge/documents", tags=["Knowledge Base (Phase 2)"])
async def list_documents(
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None
):
    """
    List documents in the knowledge base
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category
        
        documents = vector_store.list_documents(
            limit=limit,
            offset=offset,
            filter_conditions=filter_conditions
        )
        
        # Get collection info
        collection_info = vector_store.get_collection_info()
        
        return {
            "documents": documents,
            "total_vectors": collection_info.get("vectors_count", 0),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.get("/api/knowledge/search", tags=["Knowledge Base (Phase 2)"])
async def search_knowledge_base(
    query: str,
    limit: int = 10,
    category: Optional[str] = None
):
    """
    Search the knowledge base using semantic search
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category
        
        results = vector_store.search(
            query=query,
            limit=limit,
            score_threshold=0.3,  # Minimum similarity score
            filter_conditions=filter_conditions
        )
        
        logger.info(f"Search query: '{query}', found {len(results)} results")
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.delete("/api/knowledge/documents/{doc_id}", tags=["Knowledge Base (Phase 2)"])
async def delete_document(doc_id: str):
    """
    Delete a document from the knowledge base
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    try:
        success = vector_store.delete_document(doc_id)
        
        if success:
            logger.info(f"Deleted document: {doc_id}")
            return {"success": True, "message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@app.get("/api/knowledge/stats", tags=["Knowledge Base (Phase 2)"])
async def get_knowledge_base_stats():
    """
    Get knowledge base statistics
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")

    try:
        collection_info = vector_store.get_collection_info()

        return {
            "collection_name": collection_info.get("collection_name", ""),
            "total_vectors": collection_info.get("vectors_count", 0),
            "total_documents": collection_info.get("points_count", 0),
            "status": collection_info.get("status", "unknown")
        }

    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ============================================================================
# Phase 2 - Task 10: Advanced RAG Search Endpoints
# ============================================================================

@app.get("/api/knowledge/hybrid-search", tags=["Knowledge Base (Phase 2)"])
async def hybrid_search(
    query: str,
    top_k: int = 10,
    use_reranking: bool = True,
    category: Optional[str] = None
):
    """
    Perform hybrid search combining vector search and BM25 keyword search

    Args:
        query: Search query
        top_k: Number of results to return
        use_reranking: Whether to apply cross-encoder reranking
        category: Optional category filter

    Returns:
        Search results with relevance scores
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")

    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        results = rag_service.hybrid_search(
            query=query,
            top_k=top_k,
            use_reranking=use_reranking,
            filter_conditions=filter_conditions
        )

        logger.info(f"Hybrid search query: '{query}', found {len(results)} results")

        return {
            "query": query,
            "results": results,
            "count": len(results),
            "search_type": "hybrid" + (" + reranking" if use_reranking else "")
        }

    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


@app.get("/api/knowledge/rag-context", tags=["Knowledge Base (Phase 2)"])
async def get_rag_context(
    query: str,
    top_k: int = 5,
    max_context_length: int = 2000,
    category: Optional[str] = None
):
    """
    Build RAG context for a query by retrieving relevant documents

    Args:
        query: User query
        top_k: Number of source documents to retrieve
        max_context_length: Maximum total character length of context
        category: Optional category filter

    Returns:
        Assembled context with source documents
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")

    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        context_data = rag_service.build_context(
            query=query,
            top_k=top_k,
            max_context_length=max_context_length,
            filter_conditions=filter_conditions
        )

        logger.info(f"RAG context built for query: '{query}', {context_data['num_sources']} sources")

        return context_data

    except Exception as e:
        logger.error(f"Error building RAG context: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build context: {str(e)}")


@app.post("/api/knowledge/rag-answer", tags=["Knowledge Base (Phase 2)"])
async def get_rag_answer(request: dict):
    """
    Get an LLM answer using RAG (Retrieval-Augmented Generation)

    Request body:
        query: User question
        top_k: Number of source documents (default: 5)
        category: Optional category filter

    Returns:
        Answer with sources and context
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")

    query = request.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        top_k = request.get("top_k", 5)
        category = request.get("category")

        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        # Build context with RAG
        rag_result = rag_service.get_answer_with_sources(
            query=query,
            llm_client=None,  # Not using LLM integration yet
            top_k=top_k,
            filter_conditions=filter_conditions
        )

        logger.info(f"RAG answer generated for query: '{query}'")

        return {
            "query": rag_result['query'],
            "context": rag_result['context'],
            "sources": rag_result['sources'],
            "prompt": rag_result['prompt'],
            "num_sources": rag_result['num_sources'],
            "note": "LLM integration pending - returning context and prompt for now"
        }

    except Exception as e:
        logger.error(f"Error generating RAG answer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@app.post("/api/knowledge/refresh-index", tags=["Knowledge Base (Phase 2)"])
async def refresh_bm25_index():
    """
    Refresh the BM25 index for hybrid search

    This should be called after uploading new documents to enable BM25 search
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")

    try:
        success = rag_service.refresh_bm25_index()

        if success:
            logger.info("BM25 index refreshed successfully")
            return {
                "success": True,
                "message": "BM25 index refreshed successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh index")

    except Exception as e:
        logger.error(f"Error refreshing BM25 index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh index: {str(e)}")


# ============================================================================
# Analysis Module V2 - 统一分析API (5个投资场景)
# ============================================================================

from .models.analysis_models import (
    AnalysisRequest,
    AnalysisSession,
    InvestmentScenario,
    AnalysisDepth
)
from .core.orchestrators.early_stage_orchestrator import EarlyStageInvestmentOrchestrator
from .core.orchestrators.growth_orchestrator import GrowthInvestmentOrchestrator
from .core.orchestrators.public_market_orchestrator import PublicMarketInvestmentOrchestrator
from .core.orchestrators.alternative_orchestrator import AlternativeInvestmentOrchestrator
from .core.orchestrators.industry_research_orchestrator import IndustryResearchOrchestrator


@app.post("/api/v2/analysis/start", tags=["Analysis V2"])
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


@app.websocket("/ws/v2/analysis/{session_id}")
async def websocket_analysis_v2(websocket: WebSocket, session_id: str):
    """
    V2: 统一分析WebSocket端点

    支持所有5个场景的实时分析进度推送
    """
    await websocket.accept()
    logger.info(f"[V2 WS] Client connected: session={session_id}")

    try:
        # 接收初始请求
        data = await websocket.receive_json()
        logger.info(f"[V2 WS] Received request: {data}")

        # 解析请求
        request = AnalysisRequest(**data)

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
            raise HTTPException(
                status_code=501,
                detail=f"场景 {request.scenario.value} 暂未实现"
            )

        # 执行分析
        result = await orchestrator.orchestrate()

        logger.info(f"[V2 WS] Analysis completed: session={session_id}")

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


@app.get("/api/v2/analysis/{session_id}/status", tags=["Analysis V2"])
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


@app.get("/api/v2/analysis/scenarios", tags=["Analysis V2"])
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
                "icon": "🚀",
                "stages": ["angel", "seed", "pre-a", "series-a"],
                "required_inputs": ["company_name", "stage"],
                "optional_inputs": ["bp_file_id", "team_members", "industry", "founded_year"],
                "supported_depths": ["quick", "standard", "comprehensive"],
                "quick_mode_duration": "3-5分钟",
                "standard_mode_duration": "30-45分钟"
            },
            {
                "id": "growth-investment",
                "name": "成长期投资",
                "description": "评估Series B+公司的扩张潜力",
                "icon": "📈",
                "stages": ["series-b", "series-c", "series-d", "series-e", "pre-ipo"],
                "required_inputs": ["company_name", "stage"],
                "optional_inputs": ["financial_file_id", "annual_revenue", "growth_rate"],
                "supported_depths": ["quick", "standard", "comprehensive"],
                "quick_mode_duration": "3-5分钟",
                "standard_mode_duration": "30-45分钟"
            },
            {
                "id": "public-market-investment",
                "name": "公开市场投资",
                "description": "分析上市公司投资价值",
                "icon": "📊",
                "required_inputs": ["ticker"],
                "optional_inputs": ["exchange", "asset_type"],
                "supported_depths": ["quick", "standard", "comprehensive"],
                "quick_mode_duration": "3-5分钟",
                "standard_mode_duration": "20-30分钟"
            },
            {
                "id": "alternative-investment",
                "name": "另类投资",
                "description": "评估Crypto/DeFi/NFT投资机会",
                "icon": "₿",
                "required_inputs": ["asset_type"],
                "optional_inputs": ["symbol", "contract_address", "chain", "project_name"],
                "supported_depths": ["quick", "standard", "comprehensive"],
                "quick_mode_duration": "3-5分钟",
                "standard_mode_duration": "25-35分钟"
            },
            {
                "id": "industry-research",
                "name": "行业/市场研究",
                "description": "系统性研究行业趋势和投资机会",
                "icon": "🔍",
                "required_inputs": ["industry_name", "research_topic"],
                "optional_inputs": ["geo_scope", "key_questions"],
                "supported_depths": ["quick", "standard", "comprehensive"],
                "quick_mode_duration": "5-8分钟",
                "standard_mode_duration": "45-60分钟"
            }
        ]
    }
