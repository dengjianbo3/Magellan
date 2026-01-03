"""
Trigger Lock - 触发器锁机制

管理 TriggerAgent 和主分析之间的互斥关系。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Literal
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LockStatus:
    """锁状态"""
    state: str
    can_trigger: bool
    reason: str
    cooldown_remaining_seconds: int = 0
    last_analysis_time: Optional[str] = None


class TriggerLock:
    """
    触发器锁管理
    
    状态机:
    IDLE -> ANALYZING -> COOLDOWN -> IDLE
    
    - IDLE: 可以触发
    - ANALYZING: 主分析运行中，不可触发
    - COOLDOWN: 冷却期，不可触发
    """
    
    def __init__(self, cooldown_minutes: int = 30):
        self.cooldown_minutes = cooldown_minutes
        self._state: Literal["idle", "checking", "analyzing", "cooldown"] = "idle"
        self._lock = asyncio.Lock()
        self._cooldown_until: Optional[datetime] = None
        self._last_analysis_time: Optional[datetime] = None
    
    @property
    def state(self) -> str:
        # 自动检查冷却是否过期
        if self._state == "cooldown" and self._cooldown_until:
            if datetime.now() >= self._cooldown_until:
                self._state = "idle"
                self._cooldown_until = None
                logger.info("[Lock] Cooldown expired, state -> idle")
        return self._state
    
    async def acquire_check(self) -> bool:
        """
        尝试获取 Trigger Check 锁 (Transient)
        只在 IDLE 状态下成功
        """
        async with self._lock:
            # 必须 check self.state property 以触发过期
            if self.state != "idle":
                return False
            
            self._state = "checking"
            logger.debug("[Lock] Check acquired, state -> checking")
            return True

    def release_check(self):
        """释放 Trigger Check 锁"""
        if self._state == "checking":
            self._state = "idle"
            logger.debug("[Lock] Check released, state -> idle")

    def can_trigger(self) -> Tuple[bool, str]:
        """
        检查是否可以触发
        
        Returns:
            (can_trigger, reason)
        """
        current_state = self.state  # 触发自动过期检查
        
        if current_state == "analyzing":
            return False, "Main analysis in progress"
        
        if current_state == "cooldown":
            remaining = int((self._cooldown_until - datetime.now()).total_seconds())
            mins = remaining // 60
            secs = remaining % 60
            return False, f"Cooldown ({mins}m {secs}s remaining)"
        
        return True, ""

    async def acquire(self, timeout: int = 60) -> bool:
        """
        获取主分析锁，进入 ANALYZING 状态
        
        如果当前是 Trigger Check (checking)，会等待其结束。
        如果当前是 Cooldown，会强制打断冷却。
        """
        start_time = datetime.now()
        
        while True:
            async with self._lock:
                current_state = self.state
                
                # 1. 如果是 Checking，等待或超时强制获取
                if current_state == "checking":
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > timeout:
                        logger.warning("[Lock] Wait for checking timed out, forcing acquire")
                        # 超时强制获取 - 直接覆盖 checking 状态
                        self._state = "analyzing"
                        self._last_analysis_time = datetime.now()
                        self._cooldown_until = None
                        return True
                    else:
                        logger.info("[Lock] Waiting for trigger check to finish...")
                        # 释放锁并等待一小段时间再重试
                
                # 2. 正常获取逻辑 - 已经在分析中
                elif current_state == "analyzing":
                    return False  # 已经在运行
                
                # 3. IDLE 或 COOLDOWN (强制覆盖)
                else:
                    self._state = "analyzing"
                    self._last_analysis_time = datetime.now()
                    self._cooldown_until = None  # 清除冷却
                    logger.info(f"[Lock] Acquired (from {current_state}), state -> analyzing")
                    return True
            
            # 在锁外等待，避免死锁
            await asyncio.sleep(2)
    
    def release(self, cooldown_minutes: Optional[int] = None):
        """
        释放锁，进入 COOLDOWN 状态
        
        Args:
            cooldown_minutes: 冷却时间（分钟），None 使用默认值
        """
        if cooldown_minutes is None:
            cooldown_minutes = self.cooldown_minutes
        
        self._state = "cooldown"
        self._cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        logger.info(f"[Lock] Released, state -> cooldown ({cooldown_minutes}min)")
    
    def force_release(self):
        """强制释放锁，直接进入 IDLE 状态"""
        self._state = "idle"
        self._cooldown_until = None
        logger.info("[Lock] Force released, state -> idle")
    
    def get_status(self) -> LockStatus:
        """获取锁状态"""
        current_state = self.state
        can, reason = self.can_trigger()
        
        remaining = 0
        if current_state == "cooldown" and self._cooldown_until:
            remaining = max(0, int((self._cooldown_until - datetime.now()).total_seconds()))
        
        return LockStatus(
            state=current_state,
            can_trigger=can,
            reason=reason,
            cooldown_remaining_seconds=remaining,
            last_analysis_time=self._last_analysis_time.isoformat() if self._last_analysis_time else None
        )


# 测试入口
if __name__ == "__main__":
    import asyncio
    
    async def test():
        lock = TriggerLock(cooldown_minutes=1)  # 1 分钟冷却用于测试
        
        print("Initial state:", lock.get_status())
        
        # 测试获取锁
        print("\nAcquiring lock...")
        result = await lock.acquire()
        print(f"Acquired: {result}, State: {lock.state}")
        
        # 测试释放锁
        print("\nReleasing lock...")
        lock.release(cooldown_minutes=1)
        print(f"State: {lock.state}")
        
        # 测试冷却期
        can, reason = lock.can_trigger()
        print(f"Can trigger: {can}, Reason: {reason}")
        
        # 测试强制释放
        print("\nForce releasing...")
        lock.force_release()
        print(f"State: {lock.state}")
        
        can, reason = lock.can_trigger()
        print(f"Can trigger: {can}")
    
    asyncio.run(test())
