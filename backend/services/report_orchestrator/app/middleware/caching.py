"""
Response Caching Middleware
Implements in-memory caching for API responses with configurable TTL
"""
import time
import hashlib
import json
from typing import Dict, Any, Optional, Callable
from functools import wraps
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached response entry."""

    def __init__(self, content: bytes, headers: dict, status_code: int, ttl: int):
        self.content = content
        self.headers = headers
        self.status_code = status_code
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class ResponseCache:
    """
    In-memory response cache with TTL support.

    In production, consider using Redis for distributed caching.
    """

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get a cache entry if it exists and is not expired."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._cache[key]
            return None
        return entry

    def set(self, key: str, entry: CacheEntry):
        """Set a cache entry, evicting old entries if necessary."""
        # Simple LRU-like eviction: remove expired entries first
        if len(self._cache) >= self._max_size:
            self._evict_expired()

        # If still over limit, remove oldest entries
        if len(self._cache) >= self._max_size:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at
            )
            del self._cache[oldest_key]

        self._cache[key] = entry

    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching a pattern."""
        if pattern is None:
            self._cache.clear()
        else:
            keys_to_delete = [
                k for k in self._cache.keys()
                if pattern in k
            ]
            for k in keys_to_delete:
                del self._cache[k]

    def _evict_expired(self):
        """Remove all expired entries."""
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]
        for k in expired_keys:
            del self._cache[k]

    def stats(self) -> dict:
        """Get cache statistics."""
        self._evict_expired()
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "entries": [
                {
                    "key": k[:50],
                    "age_seconds": int(time.time() - v.created_at),
                    "ttl": v.ttl
                }
                for k, v in list(self._cache.items())[:10]
            ]
        }


# Global cache instance
response_cache = ResponseCache()


# Cache configuration for different endpoints
CACHE_CONFIG = {
    # Static configuration endpoints - cache longer
    "/api/scenarios": {"ttl": 3600, "methods": ["GET"]},
    "/api/workflows": {"ttl": 3600, "methods": ["GET"]},
    "/api/health": {"ttl": 60, "methods": ["GET"]},

    # Reports list - cache briefly
    "/api/reports": {"ttl": 30, "methods": ["GET"]},

    # Individual report - cache longer as reports don't change
    "/api/reports/": {"ttl": 300, "methods": ["GET"], "prefix": True},
}


def generate_cache_key(request: Request) -> str:
    """Generate a unique cache key for a request."""
    key_parts = [
        request.method,
        str(request.url.path),
        str(sorted(request.query_params.items()))
    ]
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def get_cache_config(path: str, method: str) -> Optional[dict]:
    """Get cache configuration for a given path and method."""
    # Check exact matches first
    config = CACHE_CONFIG.get(path)
    if config and method in config.get("methods", []):
        return config

    # Check prefix matches
    for pattern, cfg in CACHE_CONFIG.items():
        if cfg.get("prefix") and path.startswith(pattern):
            if method in cfg.get("methods", []):
                return cfg

    return None


class CachingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache API responses.

    Only caches GET requests for configured endpoints.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        # Check if this path should be cached
        cache_config = get_cache_config(request.url.path, request.method)
        if not cache_config:
            return await call_next(request)

        # Generate cache key
        cache_key = generate_cache_key(request)

        # Check cache
        cached = response_cache.get(cache_key)
        if cached:
            logger.debug(f"[Cache] HIT for {request.url.path}")
            response = Response(
                content=cached.content,
                status_code=cached.status_code,
                headers=dict(cached.headers)
            )
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Cache-Age"] = str(
                int(time.time() - cached.created_at)
            )
            return response

        # Get response
        response = await call_next(request)

        # Only cache successful responses
        if response.status_code == 200:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Store in cache
            entry = CacheEntry(
                content=body,
                headers=dict(response.headers),
                status_code=response.status_code,
                ttl=cache_config["ttl"]
            )
            response_cache.set(cache_key, entry)

            logger.debug(f"[Cache] MISS - stored for {request.url.path}")

            # Return new response with body
            new_response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            new_response.headers["X-Cache"] = "MISS"
            new_response.headers["Cache-Control"] = f"max-age={cache_config['ttl']}"
            return new_response

        return response


def cache_response(ttl: int = 60):
    """
    Decorator for caching individual endpoint responses.

    Usage:
        @router.get("/data")
        @cache_response(ttl=300)
        async def get_data():
            return {"data": "value"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            key_parts = [
                func.__name__,
                str(args),
                str(sorted(kwargs.items()))
            ]
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()

            # Check cache
            cached = response_cache.get(cache_key)
            if cached:
                return json.loads(cached.content)

            # Call function
            result = await func(*args, **kwargs)

            # Store in cache
            entry = CacheEntry(
                content=json.dumps(result).encode(),
                headers={},
                status_code=200,
                ttl=ttl
            )
            response_cache.set(cache_key, entry)

            return result

        return wrapper
    return decorator
