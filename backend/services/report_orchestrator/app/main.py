# backend/services/report_orchestrator/app/main.py
import asyncio
import httpx
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

# --- Service Discovery ---
FILE_SERVICE_URL = "http://file_service:8001"
PDF_PARSER_URL = "http://pdf_parser:8002"
EXCEL_PARSER_URL = "http://excel_parser:8004"
WORD_PARSER_URL = "http://word_parser:8005"
PUBLIC_DATA_URL = "http://public_data_service:8006"
LLM_GATEWAY_URL = "http://llm_gateway:8003"

app = FastAPI(
    title="Report Orchestrator Service",
    description="Orchestrates all services to generate structured investment reports.",
    version="2.0.0"
)

# --- Pydantic Models for the new Chat Endpoint ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage]
    new_message: str
    file_id: str | None = None

class ChatResponse(BaseModel):
    ai_message: str

# --- Helper Functions ---
async def get_public_company_info(client: httpx.AsyncClient, ticker: str) -> Dict[str, Any]:
    try:
        response = await client.post(f"{PUBLIC_DATA_URL}/get_company_info", json={"ticker": ticker})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError:
        return {"error": f"Could not retrieve data for ticker {ticker}. Please ensure it's a valid stock ticker."}

async def get_llm_response(client: httpx.AsyncClient, prompt: str) -> str:
    response = await client.post(f"{LLM_GATEWAY_URL}/generate", json={"prompt": prompt})
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# --- Core Chat Logic ---
@app.post("/chat", response_model=ChatResponse, tags=["Conversational Agent"])
async def chat_handler(request: ChatRequest):
    """
    Handles a single turn in the conversation with the Exploration & Insight Agent.
    """
    async with httpx.AsyncClient(timeout=300.0) as client:
        user_message = request.new_message

        # V1 Logic: Check if the first message is likely a company ticker.
        if len(request.history) <= 1: # This is the first real user message
            public_data = await get_public_company_info(client, user_message.strip().upper())
            if "error" in public_data:
                return ChatResponse(ai_message=public_data["error"])

            prompt = f"""
            Based on the following company data, write a brief, engaging introduction for an investor.
            Keep it to 2-3 sentences. End by asking the user to upload relevant documents or ask specific questions.

            Data:
            {public_data}
            """
            ai_response = await get_llm_response(client, prompt)
            return ChatResponse(ai_message=ai_response)
        
        # TODO: Add more sophisticated logic for handling follow-up questions and file-based Q&A.
        # For now, we'll just have a simple echo for demonstration.
        else:
            prompt = f"""
            The user's latest message is: "{user_message}"
            The conversation history is: {request.history}
            
            Provide a helpful, generic response.
            """
            ai_response = await get_llm_response(client, prompt)
            return ChatResponse(ai_message=ai_response)


@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Report Orchestrator"}

# Note: The old /generate_full_report endpoint is kept for now but will be deprecated.
# ... (old endpoint code can be kept here during transition)