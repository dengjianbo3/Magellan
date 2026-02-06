"""
Feature Flags for Gradual Rollout

This module provides feature flag management for gradual rollout
and emergency kill-switch capabilities.

Usage:
    from core.feature_flags import FeatureFlagManager, FeatureFlag
    
    ff = FeatureFlagManager(redis_client)
    
    if await ff.is_enabled(FeatureFlag.PARALLEL_AGENTS):
        await parallel_execution()
    else:
        await sequential_execution()
"""

import os
from enum import Enum
from typing import Optional, Dict
from dataclasses import dataclass
import redis.asyncio as redis

from app.core.observability.logging import get_logger

logger = get_logger(__name__)


class FeatureFlag(Enum):
    """Available feature flags."""
    
    # Phase 0: Observability
    STRUCTURED_LOGGING = "structured_logging"
    CIRCUIT_BREAKER = "circuit_breaker"
    
    # Phase 1: Parallel & Mode
    PARALLEL_AGENTS = "parallel_agents"
    SEMI_AUTO_MODE = "semi_auto_mode"
    MANUAL_MODE = "manual_mode"
    
    # Phase 2: Mode Enhancement
    ATR_STOP_LOSS = "atr_stop_loss"
    NOTIFICATION_SYSTEM = "notification_system"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    
    # Phase 3: Intelligence
    MULTI_TIMEFRAME = "multi_timeframe"
    AGENT_WEIGHT_LEARNING = "agent_weight_learning"
    USER_PREFERENCE_LEARNING = "user_preference_learning"


@dataclass
class FlagConfig:
    """Configuration for a feature flag."""
    default: bool = False
    description: str = ""
    rollout_percentage: int = 0  # 0-100, for gradual rollout


# Default configurations for all flags
DEFAULT_FLAG_CONFIGS: Dict[FeatureFlag, FlagConfig] = {
    # Phase 0 - Enabled by default
    FeatureFlag.STRUCTURED_LOGGING: FlagConfig(
        default=True,
        description="Use structlog for JSON-formatted logging"
    ),
    FeatureFlag.CIRCUIT_BREAKER: FlagConfig(
        default=True,
        description="Enable circuit breaker for external APIs"
    ),
    
    # Phase 1 - Gradual rollout
    FeatureFlag.PARALLEL_AGENTS: FlagConfig(
        default=False,
        description="Execute agents in parallel with rate limiting"
    ),
    FeatureFlag.SEMI_AUTO_MODE: FlagConfig(
        default=False,
        description="Enable Semi-Auto trading mode"
    ),
    FeatureFlag.MANUAL_MODE: FlagConfig(
        default=False,
        description="Enable Manual trading mode"
    ),
    
    # Phase 2 - Off by default
    FeatureFlag.ATR_STOP_LOSS: FlagConfig(
        default=False,
        description="Use ATR-based dynamic stop loss"
    ),
    FeatureFlag.NOTIFICATION_SYSTEM: FlagConfig(
        default=False,
        description="Enable multi-channel notification system"
    ),
    FeatureFlag.GRACEFUL_DEGRADATION: FlagConfig(
        default=True,
        description="Enable graceful degradation when services fail"
    ),
    
    # Phase 3 - Off by default
    FeatureFlag.MULTI_TIMEFRAME: FlagConfig(
        default=False,
        description="Enable multi-timeframe analysis"
    ),
    FeatureFlag.AGENT_WEIGHT_LEARNING: FlagConfig(
        default=False,
        description="Enable automatic agent weight adjustment"
    ),
    FeatureFlag.USER_PREFERENCE_LEARNING: FlagConfig(
        default=False,
        description="Learn user preferences from confirmations"
    ),
}


class FeatureFlagManager:
    """
    Feature flag manager with Redis backend.
    
    Supports:
    - Global flags (affect all users)
    - User-specific flags (for gradual rollout)
    - Environment variable overrides
    - Emergency kill-switch
    """
    
    REDIS_KEY_PREFIX = "ff:"
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self._local_cache: Dict[str, bool] = {}
    
    async def is_enabled(
        self,
        flag: FeatureFlag,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if a feature flag is enabled.
        
        Priority order:
        1. Environment variable override (FF_<FLAG_NAME>=1/0)
        2. Redis user-specific override
        3. Redis global override
        4. Default value from config
        
        Args:
            flag: The feature flag to check
            user_id: Optional user ID for user-specific checks
        
        Returns:
            True if feature is enabled, False otherwise
        """
        # 1. Check environment variable override
        env_key = f"FF_{flag.value.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value.lower() in ("1", "true", "yes", "on")
        
        # 2. Check Redis if available
        if self.redis:
            try:
                # Check user-specific override
                if user_id:
                    user_key = f"{self.REDIS_KEY_PREFIX}user:{user_id}:{flag.value}"
                    user_value = await self.redis.get(user_key)
                    if user_value is not None:
                        return user_value.decode() == "1"
                
                # Check global override
                global_key = f"{self.REDIS_KEY_PREFIX}global:{flag.value}"
                global_value = await self.redis.get(global_key)
                if global_value is not None:
                    return global_value.decode() == "1"
            except Exception as e:
                logger.warning(
                    "feature_flag_redis_error",
                    flag=flag.value,
                    error=str(e)
                )
        
        # 3. Check local cache
        if flag.value in self._local_cache:
            return self._local_cache[flag.value]
        
        # 4. Return default
        config = DEFAULT_FLAG_CONFIGS.get(flag, FlagConfig())
        return config.default
    
    async def set_flag(
        self,
        flag: FeatureFlag,
        enabled: bool,
        user_id: Optional[str] = None
    ):
        """
        Set a feature flag value.
        
        This is used for:
        - Emergency kill-switch (disable a feature globally)
        - Gradual rollout (enable for specific users)
        
        Args:
            flag: The feature flag to set
            enabled: Whether to enable or disable
            user_id: Optional user ID for user-specific setting
        """
        if user_id:
            key = f"{self.REDIS_KEY_PREFIX}user:{user_id}:{flag.value}"
        else:
            key = f"{self.REDIS_KEY_PREFIX}global:{flag.value}"
        
        if self.redis:
            try:
                await self.redis.set(key, "1" if enabled else "0")
            except Exception as e:
                logger.error(
                    "feature_flag_set_error",
                    flag=flag.value,
                    enabled=enabled,
                    error=str(e)
                )
                raise
        else:
            # Fallback to local cache
            self._local_cache[flag.value] = enabled
        
        logger.warning(
            "feature_flag_changed",
            flag=flag.value,
            enabled=enabled,
            user_id=user_id,
            scope="user" if user_id else "global"
        )
    
    async def delete_flag(
        self,
        flag: FeatureFlag,
        user_id: Optional[str] = None
    ):
        """
        Delete a feature flag override, reverting to default.
        
        Args:
            flag: The feature flag to delete
            user_id: Optional user ID for user-specific deletion
        """
        if user_id:
            key = f"{self.REDIS_KEY_PREFIX}user:{user_id}:{flag.value}"
        else:
            key = f"{self.REDIS_KEY_PREFIX}global:{flag.value}"
        
        if self.redis:
            await self.redis.delete(key)
        elif flag.value in self._local_cache:
            del self._local_cache[flag.value]
        
        logger.info(
            "feature_flag_deleted",
            flag=flag.value,
            user_id=user_id
        )
    
    async def get_all_flags(self, user_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Get the status of all feature flags.
        
        Args:
            user_id: Optional user ID for user-specific values
        
        Returns:
            Dictionary mapping flag names to their enabled status
        """
        result = {}
        for flag in FeatureFlag:
            result[flag.value] = await self.is_enabled(flag, user_id)
        return result
    
    def set_local(self, flag: FeatureFlag, enabled: bool):
        """
        Set a flag locally (for testing or when Redis is unavailable).
        
        Args:
            flag: The feature flag to set
            enabled: Whether to enable or disable
        """
        self._local_cache[flag.value] = enabled


# Singleton instance
_feature_flag_manager: Optional[FeatureFlagManager] = None


async def get_feature_flag_manager_async() -> FeatureFlagManager:
    """Get the singleton feature flag manager with Redis connection."""
    global _feature_flag_manager
    if _feature_flag_manager is None or _feature_flag_manager.redis is None:
        # Auto-connect to Redis using environment variable
        import os
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
        try:
            redis_client = redis.from_url(redis_url)
            _feature_flag_manager = FeatureFlagManager(redis_client)
        except Exception as e:
            logger.warning(f"feature_flag_redis_connect_error: {e}")
            _feature_flag_manager = FeatureFlagManager(None)
    return _feature_flag_manager


def get_feature_flag_manager(
    redis_client: Optional[redis.Redis] = None
) -> FeatureFlagManager:
    """Get the singleton feature flag manager instance."""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager(redis_client)
    return _feature_flag_manager


async def is_feature_enabled(
    flag: FeatureFlag,
    user_id: Optional[str] = None
) -> bool:
    """
    Convenience function to check if a feature is enabled.
    
    Usage:
        if await is_feature_enabled(FeatureFlag.PARALLEL_AGENTS):
            ...
    """
    manager = await get_feature_flag_manager_async()
    return await manager.is_enabled(flag, user_id)

