# backend/services/llm_gateway/app/main.py
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

from .core.config import settings

# --- Pydantic Models for API Request/Response ---
class ChatMessage(BaseModel):
    role: str
    parts: List[str]

class GenerateRequest(BaseModel):
    model: str = Field(default=settings.GEMINI_MODEL_NAME, description="The model to use for generation.")
    history: List[ChatMessage] = Field(..., description="The conversational history to provide context.")

class GenerateResponse(BaseModel):
    role: str
    content: str

# --- FastAPI Application ---
app = FastAPI(
    title="LLM Gateway Service (Gemini)",
    description="A dedicated gateway to interact with Google's Gemini models, optimized for chat.",
    version="2.1.0" # Version bump
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- Application Lifespan Events ---
@app.on_event("startup")
def startup_event():
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
    except Exception as e:
        raise RuntimeError(f"Failed to configure Google AI client: {e}")

# --- API Endpoints ---
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "service": "LLM Gateway"}

@app.post("/chat", response_model=GenerateResponse, tags=["AI Generation"])
async def chat_handler(request: GenerateRequest):
    print(f"--- LLM GATEWAY: RECEIVED REQUEST ---")
    print(request.json())
    print("------------------------------------")
    try:
        # Explicitly use the v1beta API version to access the latest models
        model = genai.GenerativeModel(model_name=request.model)
        
        gemini_history = [{'role': msg.role, 'parts': msg.parts} for msg in request.history]
        latest_prompt = gemini_history.pop(-1)['parts']

        chat = model.start_chat(history=gemini_history)
        response = await chat.send_message_async(latest_prompt)

        response_data = GenerateResponse(
            role="model",
            content=response.text
        )
        print(f"--- LLM GATEWAY: SENDING RESPONSE ---")
        print(response_data.json())
        print("-------------------------------------")
        return response_data

    except Exception as e:
        # Log the detailed error from the API
        print(f"An error occurred with the Gemini API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred with the Gemini API: {str(e)}"
        )
