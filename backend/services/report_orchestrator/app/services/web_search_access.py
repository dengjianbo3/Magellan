"""
Shared web-search access client.

Provides one request/response contract for calling web_search_service.
"""

from typing import Any, Dict, List, Optional

import httpx


def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    title = item.get("title") or ""
    url = item.get("url") or ""
    content = item.get("content") or ""
    score = item.get("score")
    if not isinstance(score, (int, float)):
        score = 0.0
    published_date = item.get("published_date")
    return {
        "title": title,
        "url": url,
        "content": content,
        "score": float(score),
        "published_date": published_date,
    }


async def search_web(
    web_search_url: str,
    *,
    query: str,
    max_results: int = 5,
    topic: str = "general",
    time_range: Optional[str] = None,
    days: Optional[int] = None,
    include_date: bool = True,
    timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    """Search via web_search_service and return normalized results."""
    q = (query or "").strip()
    if not q:
        return []

    payload: Dict[str, Any] = {
        "query": q,
        "max_results": max(1, min(int(max_results), 20)),
        "topic": topic,
        "include_date": include_date,
    }
    if time_range:
        payload["time_range"] = time_range
    if days is not None:
        payload["days"] = max(1, int(days))

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{web_search_url.rstrip('/')}/search", json=payload)
        response.raise_for_status()
        data = response.json()

    raw_results = data.get("results") if isinstance(data, dict) else []
    if not isinstance(raw_results, list):
        return []
    return [_normalize_item(item) for item in raw_results if isinstance(item, dict)]
