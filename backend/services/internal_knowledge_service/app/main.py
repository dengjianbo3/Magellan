# backend/services/internal_knowledge_service/app/main.py
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    content: str = Field(..., description="Text content to upload into knowledge base.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")
    title: Optional[str] = Field(default=None, description="Optional title override.")
    category: Optional[str] = Field(default=None, description="Optional category override.")


class SearchQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query.")
    limit: Optional[int] = Field(default=None, description="Maximum number of results.")
    top_k: Optional[int] = Field(default=None, description="Alias of limit.")
    category: Optional[str] = Field(default=None, description="Optional category filter.")
    use_reranking: bool = Field(default=True, description="Whether to apply reranking.")


class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: Optional[float] = None
    source: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    documents: List[SearchResult]
    count: int
    search_type: str = "hybrid"


app = FastAPI(
    title="Internal Knowledge Service (Compatibility Proxy)",
    description="Compatibility layer that forwards to report_orchestrator knowledge APIs.",
    version="3.3.0",
)


def _parse_cors_allow_origins() -> List[str]:
    raw = (os.getenv("CORS_ALLOW_ORIGINS") or "http://localhost:5174,http://localhost:8081").strip()
    if not raw:
        return []
    if raw in ("*", "all"):
        return ["*"]
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            pass
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPSTREAM_KB_BASE_URL = os.getenv("INTERNAL_KB_UPSTREAM_URL", "http://report_orchestrator:8000").rstrip("/")
UPSTREAM_TIMEOUT = float(os.getenv("INTERNAL_KB_UPSTREAM_TIMEOUT", "30"))


def _resolve_limit(limit: Optional[int], top_k: Optional[int]) -> int:
    candidate = limit if limit is not None else top_k
    if candidate is None:
        return 3
    return max(1, min(int(candidate), 50))


def _normalize_results(items: List[Dict[str, Any]]) -> List[SearchResult]:
    normalized: List[SearchResult] = []
    for item in items:
        content = item.get("content") or item.get("text") or ""
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {}
        source = item.get("source") or metadata.get("source") or metadata.get("title") or metadata.get("filename")
        score = item.get("score")
        if not isinstance(score, (int, float)):
            score = None
        normalized.append(
            SearchResult(
                content=content,
                metadata=metadata,
                score=score,
                source=source,
            )
        )
    return normalized


def _build_upstream_headers(authorization: Optional[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if authorization:
        headers["Authorization"] = authorization
    return headers


@app.post("/upload", status_code=201, tags=["Knowledge Base"])
async def upload_document(
    request: DocumentUploadRequest,
    authorization: Optional[str] = Header(default=None),
):
    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")

    title = request.title or request.metadata.get("title") or request.metadata.get("source") or "internal-note.txt"
    category = request.category or request.metadata.get("category") or "general"
    text_bytes = request.content.encode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            upload_resp = await client.post(
                f"{UPSTREAM_KB_BASE_URL}/api/knowledge/upload",
                files={"file": (f"{title}.txt" if "." not in title else title, text_bytes, "text/plain")},
                data={"title": title, "category": category},
                headers=_build_upstream_headers(authorization),
            )
            if upload_resp.status_code >= 400:
                detail = upload_resp.text
                try:
                    detail = upload_resp.json().get("detail", detail)
                except Exception:
                    pass
                raise HTTPException(status_code=upload_resp.status_code, detail=detail)

            # Keep BM25 index fresh for compatibility callers.
            try:
                await client.post(
                    f"{UPSTREAM_KB_BASE_URL}/api/knowledge/refresh-index",
                    headers=_build_upstream_headers(authorization),
                )
            except Exception:
                pass

            return {
                "message": "Document uploaded successfully.",
                "upstream": upload_resp.json(),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {e}")


@app.post("/search", response_model=SearchResponse, tags=["Knowledge Base"])
async def search_knowledge_base(
    request: SearchQueryRequest,
    authorization: Optional[str] = Header(default=None),
):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    top_k = _resolve_limit(request.limit, request.top_k)
    params: Dict[str, Any] = {
        "query": query,
        "top_k": top_k,
        "use_reranking": request.use_reranking,
    }
    if request.category:
        params["category"] = request.category

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            response = await client.get(
                f"{UPSTREAM_KB_BASE_URL}/api/knowledge/hybrid-search",
                params=params,
                headers=_build_upstream_headers(authorization),
            )
            if response.status_code >= 400:
                detail = response.text
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    pass
                raise HTTPException(status_code=response.status_code, detail=detail)

            payload = response.json()
            upstream_results = payload.get("results", [])
            normalized = _normalize_results(upstream_results)
            return SearchResponse(
                query=query,
                results=normalized,
                documents=normalized,  # Backward compatibility for legacy callers
                count=len(normalized),
                search_type=payload.get("search_type", "hybrid"),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform search: {e}")


@app.get("/", tags=["Health Check"])
def read_root():
    return {
        "status": "ok",
        "service": "Internal Knowledge Service",
        "mode": "proxy",
        "upstream": UPSTREAM_KB_BASE_URL,
    }
