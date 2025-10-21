# backend/services/report_orchestrator/app/main.py
import httpx
import asyncio
import json
import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Service Discovery ---
PUBLIC_DATA_URL = "http://public_data_service:8006"
LLM_GATEWAY_URL = "http://llm_gateway:8003"

app = FastAPI(
    title="Orchestrator Agent Service",
    description="Manages the multi-agent workflow for generating investment reports.",
    version="2.3.0"
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
            step0 = Step(id=0, title=f"Fetching user persona for '{user_id}'", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step0).dict())
            print("DEBUG: Sent Step 0 running status")
            try:
                print("DEBUG: Calling user_service")
                persona_resp = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
                persona_resp.raise_for_status()
                user_persona = UserPersona(**persona_resp.json())
                step0.status = "success"
                step0.result = f"Persona loaded: Style '{user_persona.investment_style}', Risk '{user_persona.risk_tolerance}'."
                print("DEBUG: user_service call successful")
            except Exception as e:
                step0.status = "error"
                step0.result = "Could not load user persona, using defaults."
                print(f"DEBUG: user_service call failed: {e}")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step0).dict())
            print("DEBUG: Sent Step 0 final status")

            # --- Step 1: Data Collection & Ambiguity Resolution ---
            print("DEBUG: Starting Step 1: Data Collection")
            step1 = Step(id=1, title=f"Fetching public data for '{ticker}'", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())
            print("DEBUG: Sent Step 1 running status")
            
            public_data_resp = await client.post(f"{PUBLIC_DATA_URL}/get_company_info", json={"ticker": ticker})
            print("DEBUG: Called get_company_info")
            public_data_resp.raise_for_status()
            response_data = public_data_resp.json()

            if response_data['status'] == 'multiple_options':
                print("DEBUG: Ambiguity found, pausing for user input")
                step1.status = "paused"
                step1.result = "Ambiguous company name. Please select the correct one."
                step1.options = response_data['data']
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='hitl_required', step=step1).dict())
                
                print("DEBUG: Waiting for user choice...")
                user_choice = await websocket.receive_json()
                selected_ticker = user_choice.get("selected_ticker")
                ticker = selected_ticker
                print(f"DEBUG: User selected {selected_ticker}")

                step1.title = f"Fetching confirmed data for {selected_ticker}"
                step1.status = "running"
                step1.result = f"You selected {selected_ticker}. Continuing analysis..."
                step1.options = None
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())

                public_data_resp = await client.post(f"{PUBLIC_DATA_URL}/get_company_info", json={"ticker": selected_ticker})
                print("DEBUG: Called get_company_info again with confirmed ticker")
            else:
                selected_ticker = ticker

            public_data_resp.raise_for_status()
            public_data = public_data_resp.json()['data']
            step1.status = "success"
            step1.result = f"Successfully retrieved data for {public_data.get('company_name', selected_ticker)}."
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())
            print("DEBUG: Sent Step 1 success status")

            # --- Step 2: Initial Analysis with LLM ---
            print("DEBUG: Starting Step 2: Initial Analysis")
            step2 = Step(id=2, title="Generating initial analysis with Gemini", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step2).dict())
            prompt = f"Based on the following company data, write a brief, engaging introduction for an investor.\n\nData:\n{public_data}"
            summary = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])
            step2.status = "success"
            step2.result = summary
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step2).dict())
            print("DEBUG: Sent Step 2 success status")

            # --- Step 3: Fetch Financial Data for Chart ---
            print("DEBUG: Starting Step 3: Fetch Financial Data")
            step3 = Step(id=3, title="Fetching financial summary for chart", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step3).dict())
            financial_data = None
            try:
                print("DEBUG: Calling get_financial_summary")
                financial_resp = await client.post(f"{PUBLIC_DATA_URL}/get_financial_summary", json={"ticker": selected_ticker})
                financial_resp.raise_for_status()
                financial_data = financial_resp.json()
                step3.status = "success"
                step3.result = "Successfully retrieved financial summary."
                print("DEBUG: get_financial_summary successful")
            except Exception as e:
                step3.status = "error"
                step3.result = f"Could not retrieve financial summary: {e}"
                print(f"DEBUG: get_financial_summary failed: {e}")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step3).dict())
            print("DEBUG: Sent Step 3 final status")

            # --- Step 4: Generate Key Questions (HITL Node 2) ---
            print("DEBUG: Starting Step 4: Generate Key Questions")
            step4 = Step(id=4, title="Generating key follow-up questions", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step4).dict())
            prompt = f"""You are an expert investment analyst. Your client has an investment style of '{user_persona.investment_style}' and a '{user_persona.risk_tolerance}' risk tolerance.
            Based on the following company introduction, generate a JSON array of 3-4 insightful and critical follow-up questions tailored to the client's persona.
            Introduction: {summary}
            
            CRITICAL: Your entire response must be only the raw JSON array, with no extra text, explanations, or markdown formatting.
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
                        key_questions = ["Error: Could not parse JSON from LLM markdown."]
                else:
                    key_questions = ["Error: LLM returned invalid, non-JSON content."]

            # Handle cases where the LLM returns a list of objects with a "question" key
            if key_questions and isinstance(key_questions[0], dict):
                key_questions = [q.get("question", "Invalid question format") for q in key_questions]
            
            if not key_questions or "Error" in key_questions[0]:
                step4.status = "error"
                step4.result = key_questions[0] if key_questions else "Error: LLM returned an empty list of questions."
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='error', step=step4).dict())
                return

            step4.status = "success"
            step4.result = "Successfully generated key questions for user follow-up."
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step4).dict())
            print("DEBUG: Sent Step 4 success status")

            # --- Final HITL Follow-up ---
            print("DEBUG: Preparing final HITL message")
            preliminary_report = FullReportResponse(
                company_ticker=selected_ticker,
                report_sections=[
                    ReportSection(section_title="Preliminary Analysis", content=summary),
                    ReportSection(section_title="Financial Analysis", content="Interactive chart with key financial data.")
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
    prompt = f"""You are an AI investment analyst assistant. Your user has a specific investment persona.
    
    Report Summary:
    ---
    {request.analysis_context}
    ---
    
    User's Input:
    ---
    {request.user_input}
    ---
    
    Analyze the user's input from the perspective of a 'Balanced' investor with 'Medium' risk tolerance. Provide concise, insightful feedback.
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
    return {"status": "ok", "service": "Orchestrator Agent"}
