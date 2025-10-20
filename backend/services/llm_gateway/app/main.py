# backend/services/llm_gateway/app/main.py
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .core.config import settings

# --- Pydantic Models for API Request/Response ---
class GenerateRequest(BaseModel):
    """Request model for the /generate endpoint."""
    # As per user request, we will use the specified model name
    model: str = Field(default="gemini-2.5-pro", description="The model to use for generation.")
    prompt: str = Field(..., description="The prompt to send to the language model.")

class Message(BaseModel):
    role: str
    content: str

class Choice(BaseModel):
    message: Message

class GenerateResponse(BaseModel):
    """Standardized response model, mimicking OpenAI's structure for consistency."""
    model: str
    choices: list[Choice]

# --- FastAPI Application ---
app = FastAPI(
    title="LLM Gateway Service",
    description="A gateway to interact with Google's Gemini Pro models.",
    version="1.0.0"
)

# --- Application Lifespan Events ---
@app.on_event("startup")
def startup_event():
    """
    On application startup, configure the Google Generative AI client
    using the API key from the environment settings.
    """
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
    except Exception as e:
        # This will prevent the app from starting if the API key is missing or invalid
        raise RuntimeError(f"Failed to configure Google AI client: {e}")

# --- API Endpoints ---
@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Gateway"}

@app.post("/generate", response_model=GenerateResponse, tags=["AI Generation"])
async def generate_text(request: GenerateRequest):
    """
    Receives a prompt and generates a response using the specified Gemini model.
    """
    try:
        model = genai.GenerativeModel(request.model)
        response = model.generate_content(request.prompt)

        # Standardize the response to our internal format.
        # This abstraction is useful if we ever want to support multiple providers.
        standardized_response = GenerateResponse(
            model=request.model,
            choices=[
                Choice(
                    message=Message(
                        role="assistant",
                        content=response.text
                    )
                )
            ]
        )
        return standardized_response

    except Exception as e:
        # Catch potential errors from the Gemini API (e.g., invalid model, safety blocks)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred with the Gemini API: {e}"
        )
