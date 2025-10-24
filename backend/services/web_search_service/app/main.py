# backend/services/web_search_service/app/main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from tavily import TavilyClient
from typing import List, Dict, Any

# --- Pydantic Models ---
class SearchRequest(BaseModel):
    query: str = Field(..., description="The search query.")
    max_results: int = Field(default=5, description="The maximum number of search results to return.")

class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]

# --- FastAPI Application ---
app = FastAPI(
    title="Web Search Service",
    description="Provides real-time web search capabilities using the Tavily API.",
    version="3.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Tavily Client ---
tavily_client = None

@app.on_event("startup")
def startup_event():
    global tavily_client
    try:
        # It's recommended to set the API key as an environment variable
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set.")
        tavily_client = TavilyClient(api_key=tavily_api_key)
        print("Successfully initialized Tavily client.")
    except Exception as e:
        print(f"Failed to initialize Tavily client: {e}")
        tavily_client = None

# --- API Endpoints ---
@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_endpoint(request: SearchRequest):
    if not tavily_client:
        raise HTTPException(status_code=503, detail="Tavily client is not available.")
    
    try:
        # Perform the search
        response = tavily_client.search(
            query=request.query,
            search_depth="advanced", # Use advanced for more thorough results
            max_results=request.max_results
        )
        
        # Format the response
        results = [
            SearchResult(
                title=res.get("title", ""),
                url=res.get("url", ""),
                content=res.get("content", ""),
                score=res.get("score", 0.0)
            )
            for res in response.get("results", [])
        ]
        
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during the search: {str(e)}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Web Search Service"}
