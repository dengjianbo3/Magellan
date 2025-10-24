# backend/services/llm_gateway/app/main.py
from google import genai
from google.genai import types
import os
import io
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

from .core.config import settings

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    parts: List[str]

class GenerateRequest(BaseModel):
    history: List[ChatMessage]

class GenerateResponse(BaseModel):
    content: str

# --- FastAPI App ---
app = FastAPI(
    title="LLM Gateway Service (Gemini)",
    description="A gateway for Gemini models, supporting text, chat, and native file understanding via the File API.",
    version="3.3.0" # Final V3 version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai_client = None

@app.on_event("startup")
def startup_event():
    global genai_client
    try:
        genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        print("Successfully initialized Google AI client.")
    except Exception as e:
        print(f"Failed to create Google AI client: {e}")
        raise RuntimeError(f"Failed to create Google AI client: {e}")

# --- API Endpoints ---
@app.post("/generate_from_file", response_model=GenerateResponse, tags=["AI Generation"])
async def generate_from_file(prompt: str = Form(...), file: UploadFile = File(...)):
    """
    Understands a file (PDF, image, etc.) by uploading it via the File API
    and then generating content with gemini-2.5-flash.
    """
    if not genai_client:
        raise HTTPException(status_code=503, detail="Google AI client is not available.")
        
    try:
        import time
        
        # 1. Read file content into a BytesIO object
        file_content = await file.read()
        file_io = io.BytesIO(file_content)
        file_io.name = file.filename  # Set the name attribute
        
        # 2. Upload file to Files API
        upload_response = genai_client.files.upload(
            file=file_io,
            config=types.UploadFileConfig(
                mime_type=file.content_type,
                display_name=file.filename
            )
        )
        
        # 3. Wait for file to be processed
        print(f"Uploaded file: {upload_response.name}, state: {upload_response.state}")
        while upload_response.state == "PROCESSING":
            time.sleep(1)
            upload_response = genai_client.files.get(name=upload_response.name)
            print(f"File state: {upload_response.state}")
        
        if upload_response.state != "ACTIVE":
            raise HTTPException(status_code=500, detail=f"File processing failed with state: {upload_response.state}")
        
        # 4. Generate content using the uploaded file
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                types.Part(text=prompt),
                types.Part(file_data=types.FileData(file_uri=upload_response.uri))
            ]
        )
        
        # 5. Clean up the file
        genai_client.files.delete(name=upload_response.name)
        
        return GenerateResponse(content=response.text)
    except Exception as e:
        import traceback
        print("====== DETAILED ERROR IN llm_gateway ======")
        traceback.print_exc()
        print("============================================")
        raise HTTPException(status_code=500, detail=f"Error during generation: {str(e)}")

@app.post("/chat", response_model=GenerateResponse, tags=["AI Generation"])
async def chat_handler(request: GenerateRequest):
    """
    Handles standard chat conversations with gemini-1.0-pro.
    Includes retry logic for 503 errors.
    """
    if not genai_client:
        raise HTTPException(status_code=503, detail="Google AI client is not available.")
        
    # Retry configuration
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Convert history to contents format for new SDK
            contents = []
            for msg in request.history:
                contents.append(
                    types.Content(
                        role=msg.role,
                        parts=[types.Part(text=part) for part in msg.parts]
                    )
                )
            
            response = genai_client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=contents
            )
            
            return GenerateResponse(content=response.text)
        except Exception as e:
            import traceback
            import asyncio
            from google.genai.errors import ServerError
            
            # Check if it's a 503 error that we should retry
            is_503_error = (isinstance(e, ServerError) and hasattr(e, 'status_code') and e.status_code == 503)
            
            if is_503_error and attempt < max_retries - 1:
                print(f"[RETRY] Attempt {attempt + 1}/{max_retries} failed with 503. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            
            # If it's the last attempt or not a retryable error, raise
            print("====== DETAILED ERROR IN llm_gateway chat ======")
            traceback.print_exc()
            print("================================================")
            raise HTTPException(status_code=500, detail=f"Error during chat: {str(e)}")

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "service": "LLM Gateway"}
