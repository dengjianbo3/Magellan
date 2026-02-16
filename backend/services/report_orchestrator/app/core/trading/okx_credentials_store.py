"""
OKX Credentials Store (Redis)

Goal:
- Do NOT rely on server-side .env OKX keys for hosted testing.
- Allow users to configure OKX demo credentials from the frontend.
- Never return secrets back to the frontend; only return masked status.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Any, Dict

import redis.asyncio as redis

from .trading_config import get_infra_config

logger = logging.getLogger(__name__)


@dataclass
class OkxCredentials:
    api_key: str
    secret_key: str
    passphrase: str
    demo_mode: bool = True
    updated_at: str = ""

    def normalized(self) -> "OkxCredentials":
        return OkxCredentials(
            api_key=(self.api_key or "").strip(),
            secret_key=(self.secret_key or "").strip(),
            passphrase=(self.passphrase or "").strip(),
            demo_mode=bool(self.demo_mode),
            updated_at=self.updated_at or datetime.now(timezone.utc).isoformat(),
        )

    def is_configured(self) -> bool:
        c = self.normalized()
        return bool(c.api_key and c.secret_key and c.passphrase)

    def masked(self) -> Dict[str, Any]:
        c = self.normalized()
        last4 = c.api_key[-4:] if c.api_key else ""
        return {
            "configured": c.is_configured(),
            "demo_mode": bool(c.demo_mode),
            "api_key_last4": last4,
            "updated_at": c.updated_at,
        }


class OkxCredentialsStore:
    REDIS_KEY = "trading:okx:credentials"

    def __init__(self, redis_url: str | None = None, redis_client: Optional[redis.Redis] = None):
        self.redis_url = redis_url or get_infra_config().redis_url
        self._redis = redis_client

    async def _connect(self) -> Optional[redis.Redis]:
        if self._redis is not None:
            return self._redis
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            return self._redis
        except Exception as e:
            logger.warning(f"[OkxCredentialsStore] Redis unavailable: {e}")
            self._redis = None
            return None

    async def get(self) -> Optional[OkxCredentials]:
        r = await self._connect()
        if not r:
            return None
        raw = await r.get(self.REDIS_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return OkxCredentials(
                api_key=data.get("api_key", ""),
                secret_key=data.get("secret_key", ""),
                passphrase=data.get("passphrase", ""),
                demo_mode=bool(data.get("demo_mode", True)),
                updated_at=data.get("updated_at", ""),
            ).normalized()
        except Exception:
            return None

    async def get_masked(self) -> Dict[str, Any]:
        creds = await self.get()
        if not creds:
            return {"configured": False, "demo_mode": True, "api_key_last4": "", "updated_at": ""}
        return creds.masked()

    async def set(self, creds: OkxCredentials) -> bool:
        r = await self._connect()
        if not r:
            return False
        c = creds.normalized()
        payload = asdict(c)
        # Never log secrets.
        try:
            await r.set(self.REDIS_KEY, json.dumps(payload, ensure_ascii=False))
            return True
        except Exception:
            return False

    async def clear(self) -> bool:
        r = await self._connect()
        if not r:
            return False
        try:
            await r.delete(self.REDIS_KEY)
            return True
        except Exception:
            return False


_store: Optional[OkxCredentialsStore] = None


def get_okx_credentials_store() -> OkxCredentialsStore:
    global _store
    if _store is None:
        _store = OkxCredentialsStore()
    return _store

