"""
Shared knowledge-base access client.

This keeps one calling contract for all modules that query knowledge search APIs.
"""

from typing import Any, Dict, List, Optional

import httpx
from app.core.auth import get_current_access_token


def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    source = item.get("source") or metadata.get("source") or metadata.get("title") or metadata.get("filename")
    score = item.get("score")
    if not isinstance(score, (int, float)):
        score = 0.0
    return {
        "content": item.get("content") or item.get("text") or "",
        "metadata": metadata,
        "source": source or "Unknown",
        "score": float(score),
    }


async def search_knowledge_base(
    knowledge_service_url: str,
    *,
    query: str,
    top_k: int = 3,
    category: Optional[str] = None,
    use_reranking: bool = True,
    timeout: float = 30.0,
    auth_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query knowledge base through a single contract.

    Expected upstream endpoint: POST {knowledge_service_url}/search
    """
    q = (query or "").strip()
    if not q:
        return {"query": q, "results": [], "count": 0}

    limit = max(1, min(int(top_k), 50))
    payload: Dict[str, Any] = {
        "query": q,
        "limit": limit,
        "top_k": limit,
        "use_reranking": use_reranking,
    }
    if category:
        payload["category"] = category

    resolved_token = (auth_token or get_current_access_token() or "").strip()
    headers: Dict[str, str] = {}
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{knowledge_service_url.rstrip('/')}/search",
            json=payload,
            headers=headers or None,
        )
        response.raise_for_status()
        data = response.json()

    raw_results = data.get("results") or data.get("documents") or []
    normalized = [_normalize_item(item) for item in raw_results if isinstance(item, dict)]
    return {
        "query": data.get("query", q),
        "results": normalized,
        "count": len(normalized),
        "search_type": data.get("search_type", "hybrid"),
    }
