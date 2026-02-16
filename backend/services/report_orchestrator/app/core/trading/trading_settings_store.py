"""
Trading Settings Store (Redis)

Persist user-modified trading settings across /api/trading/reset.
We keep secrets (OKX keys) in a separate store.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict

import redis.asyncio as redis

from .trading_config import get_infra_config

logger = logging.getLogger(__name__)


@dataclass
class TradingSettings:
    analysis_interval_hours: Optional[int] = None
    max_leverage: Optional[int] = None
    max_position_percent: Optional[float] = None
    enabled: Optional[bool] = None
    use_okx_trading: Optional[bool] = None
    okx_demo_mode: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TradingSettings":
        return cls(
            analysis_interval_hours=d.get("analysis_interval_hours"),
            max_leverage=d.get("max_leverage"),
            max_position_percent=d.get("max_position_percent"),
            enabled=d.get("enabled"),
            use_okx_trading=d.get("use_okx_trading"),
            okx_demo_mode=d.get("okx_demo_mode"),
        )


class TradingSettingsStore:
    REDIS_KEY = "trading:settings"

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
            logger.warning(f"[TradingSettingsStore] Redis unavailable: {e}")
            self._redis = None
            return None

    async def get(self) -> TradingSettings:
        r = await self._connect()
        if not r:
            return TradingSettings()
        raw = await r.get(self.REDIS_KEY)
        if not raw:
            return TradingSettings()
        try:
            return TradingSettings.from_dict(json.loads(raw))
        except Exception:
            return TradingSettings()

    async def update(self, patch: TradingSettings) -> TradingSettings:
        r = await self._connect()
        current = await self.get()
        merged = TradingSettings(
            analysis_interval_hours=patch.analysis_interval_hours if patch.analysis_interval_hours is not None else current.analysis_interval_hours,
            max_leverage=patch.max_leverage if patch.max_leverage is not None else current.max_leverage,
            max_position_percent=patch.max_position_percent if patch.max_position_percent is not None else current.max_position_percent,
            enabled=patch.enabled if patch.enabled is not None else current.enabled,
            use_okx_trading=patch.use_okx_trading if patch.use_okx_trading is not None else current.use_okx_trading,
            okx_demo_mode=patch.okx_demo_mode if patch.okx_demo_mode is not None else current.okx_demo_mode,
        )
        if r:
            try:
                await r.set(self.REDIS_KEY, json.dumps(merged.to_dict(), ensure_ascii=False))
            except Exception:
                pass
        return merged

    async def clear(self) -> bool:
        r = await self._connect()
        if not r:
            return False
        try:
            await r.delete(self.REDIS_KEY)
            return True
        except Exception:
            return False


_store: Optional[TradingSettingsStore] = None


def get_trading_settings_store() -> TradingSettingsStore:
    global _store
    if _store is None:
        _store = TradingSettingsStore()
    return _store

