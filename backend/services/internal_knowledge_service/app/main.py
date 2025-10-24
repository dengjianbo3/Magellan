# backend/services/internal_knowledge_service/app/main.py
import chromadb
import uuid
import os
from google import genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- Pydantic Models ---
class DocumentUploadRequest(BaseModel):
    content: str = Field(..., description="The text content of the document to be stored.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="A dictionary of metadata, e.g., {'source': 'expert_interview_notes.txt'}")

class SearchQueryRequest(BaseModel):
    query: str = Field(..., description="The natural language query to search for.")
    limit: int = Field(default=3, description="The maximum number of results to return.")

class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]

# --- FastAPI Application ---
app = FastAPI(
    title="Internal Knowledge Service (ChromaDB)",
    description="Manages the company's internal knowledge base using ChromaDB.",
    version="3.2.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Clients ---
chroma_client = None
knowledge_collection = None
genai_client = None
KNOWLEDGE_COLLECTION_NAME = "internal_knowledge"

@app.on_event("startup")
def startup_event():
    global chroma_client, knowledge_collection, genai_client
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")

        genai_client = genai.Client(api_key=api_key)

        chroma_client = chromadb.HttpClient(host="chroma", port=8000)
        knowledge_collection = chroma_client.get_or_create_collection(name=KNOWLEDGE_COLLECTION_NAME)

        print("Successfully connected to ChromaDB and initialized Google AI client.")
    except Exception as e:
        print(f"Failed during startup: {e}")
        import traceback
        traceback.print_exc()
        chroma_client = None
        knowledge_collection = None
        genai_client = None

# --- API Endpoints ---
@app.post("/upload", status_code=201, tags=["Knowledge Base"])
async def upload_document(request: DocumentUploadRequest):
    if not knowledge_collection or not genai_client:
        raise HTTPException(status_code=503, detail="A required client (ChromaDB or Google AI) is not available.")
    
    try:
        # Use the new SDK to generate embeddings
        embedding_response = genai_client.models.embed_content(
            model="text-embedding-004",
            contents=request.content
        )

        doc_id = str(uuid.uuid4())
        knowledge_collection.add(
            ids=[doc_id],
            embeddings=[embedding_response.embeddings[0].values],
            documents=[request.content],
            metadatas=[request.metadata]
        )
        
        return {"message": "Document uploaded successfully."}
    except Exception as e:
        import traceback
        print("====== ERROR IN upload_document ======")
        traceback.print_exc()
        print("======================================")
        raise HTTPException(status_code=500, detail=f"Failed to process and insert document: {e}")

@app.post("/search", response_model=SearchResponse, tags=["Knowledge Base"])
async def search_knowledge_base(request: SearchQueryRequest):
    if not knowledge_collection or not genai_client:
        raise HTTPException(status_code=503, detail="A required client (ChromaDB or Google AI) is not available.")

    try:
        # Use the new SDK to generate query embedding
        query_embedding_response = genai_client.models.embed_content(
            model="text-embedding-004",
            contents=request.query
        )

        response = knowledge_collection.query(
            query_embeddings=[query_embedding_response.embeddings[0].values],
            n_results=request.limit
        )
        
        results = []
        if response['documents'] and len(response['documents'][0]) > 0:
            for i in range(len(response['documents'][0])):
                results.append(SearchResult(
                    content=response['documents'][0][i],
                    metadata=response['metadatas'][0][i]
                ))
        
        return SearchResponse(results=results)
    except Exception as e:
        import traceback
        print("====== ERROR IN search_knowledge_base ======")
        traceback.print_exc()
        print("============================================")
        raise HTTPException(status_code=500, detail=f"Failed to perform search: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Internal Knowledge Service"}
