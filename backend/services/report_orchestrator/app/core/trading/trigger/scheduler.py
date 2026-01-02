"""
Trigger Scheduler - 触发器调度器

独立调度器，每 15 分钟运行 TriggerAgent 检查。
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Callable, Awaitable, Dict
from enum import Enum

# 支持独立运行和作为模块导入
try:
    from .agent import TriggerAgent, TriggerContext
    from .lock import TriggerLock
except ImportError:
    from agent import TriggerAgent, TriggerContext
    from lock import TriggerLock

logger = logging.getLogger(__name__)


class SchedulerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class TriggerScheduler:
    """
    触发器调度器
    
    每 N 分钟运行 TriggerAgent 检查，
    如果触发条件满足，调用回调函数。
    """
    
    def __init__(
        self,
        trigger_agent: Optional[TriggerAgent] = None,
        trigger_lock: Optional[TriggerLock] = None,
        interval_minutes: int = None,
        cooldown_minutes: int = None,
        on_trigger: Optional[Callable[[TriggerContext], Awaitable[None]]] = None
    ):
        # 从环境变量读取配置
        self.interval_minutes = interval_minutes or int(os.getenv("TRIGGER_INTERVAL_MINUTES", "15"))
        cooldown = cooldown_minutes or int(os.getenv("TRIGGER_COOLDOWN_MINUTES", "30"))
        
        self.trigger_agent = trigger_agent or TriggerAgent()
        self.trigger_lock = trigger_lock or TriggerLock(cooldown_minutes=cooldown)
        self.on_trigger = on_trigger  # 触发时的回调
        
        self._state = SchedulerState.IDLE
        self._task: Optional[asyncio.Task] = None
        self._check_count = 0
        self._trigger_count = 0
        self._last_check_time: Optional[datetime] = None
    
    @property
    def state(self) -> str:
        return self._state.value
    
    async def start(self):
        """启动调度器"""
        if self._state == SchedulerState.RUNNING:
            logger.warning("[TriggerScheduler] Already running")
            return
        
        self._state = SchedulerState.RUNNING
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"[TriggerScheduler] Started, interval={self.interval_minutes}min")
    
    async def stop(self):
        """停止调度器"""
        if self._state != SchedulerState.RUNNING:
            return
        
        self._state = SchedulerState.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[TriggerScheduler] Stopped")
    
    async def _run_loop(self):
        """调度循环"""
        # 初次启动时等待一个周期，因为系统启动时默认会执行一次全量分析
        logger.info(f"[TriggerScheduler] Waiting {self.interval_minutes}min before first check...")
        await asyncio.sleep(self.interval_minutes * 60)

        while self._state == SchedulerState.RUNNING:
            try:
                await self.run_check()
            except Exception as e:
                logger.error(f"[TriggerScheduler] Check error: {e}")
            
            # 等待下一次检查
            await asyncio.sleep(self.interval_minutes * 60)
    
    async def run_check(self) -> Dict:
        """
        执行一次检查
        
        Returns:
            检查结果字典
        """
        self._check_count += 1
        self._last_check_time = datetime.now()
        
        logger.info(f"[TriggerScheduler] Running check #{self._check_count}")
        
        # 1. 检查锁状态
        can_trigger, reason = self.trigger_lock.can_trigger()
        if not can_trigger:
            logger.info(f"[TriggerScheduler] Skipped: {reason}")
            return {
                "skipped": True,
                "reason": reason,
                "check_number": self._check_count
            }
        
        # 2. 运行 TriggerAgent (无 LLM, <5s)
        should_trigger, context = await self.trigger_agent.check()
        
        result = {
            "skipped": False,
            "should_trigger": should_trigger,
            "confidence": context.confidence,
            "urgency": context.urgency,
            "check_number": self._check_count,
            "context": context.to_dict()
        }
        
        if not should_trigger:
            logger.info(f"[TriggerScheduler] No trigger, confidence={context.confidence}%")
            return result
        
        # 3. 触发！
        self._trigger_count += 1
        logger.info(f"[TriggerScheduler] TRIGGER! Confidence={context.confidence}%, Urgency={context.urgency}")
        
        # 4. 获取锁
        acquired = await self.trigger_lock.acquire()
        if not acquired:
            logger.warning("[TriggerScheduler] Failed to acquire lock")
            result["lock_failed"] = True
            return result
        
        try:
            # 5. 调用回调 (如果有)
            if self.on_trigger:
                await self.on_trigger(context)
                result["callback_executed"] = True
            else:
                logger.info("[TriggerScheduler] No callback configured, skipping main analysis")
                result["callback_executed"] = False
                
        finally:
            # 6. 释放锁 + 冷却
            self.trigger_lock.release()
        
        return result
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        lock_status = self.trigger_lock.get_status()
        agent_status = self.trigger_agent.get_status()
        
        return {
            "state": self._state.value,
            "interval_minutes": self.interval_minutes,
            "check_count": self._check_count,
            "trigger_count": self._trigger_count,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "lock": {
                "state": lock_status.state,
                "can_trigger": lock_status.can_trigger,
                "cooldown_remaining": lock_status.cooldown_remaining_seconds
            },
            "agent": agent_status
        }


# 测试入口
if __name__ == "__main__":
    async def test():
        print("\n" + "="*60)
        print("TriggerScheduler Test")
        print("="*60)
        
        # 模拟触发回调
        async def mock_on_trigger(context: TriggerContext):
            print(f"\n[CALLBACK] Main analysis would be triggered!")
            print(f"  Score: {context.score}")
            print(f"  Price Change (15m): {context.price_change_15m}%")
        
        scheduler = TriggerScheduler(
            interval_minutes=1,  # 测试用 1 分钟
            on_trigger=mock_on_trigger
        )
        
        # 单次检查测试
        print("\n--- Running single check ---")
        result = await scheduler.run_check()
        
        print(f"\nResult:")
        print(f"  Skipped: {result.get('skipped', False)}")
        print(f"  Should Trigger: {result.get('should_trigger', False)}")
        print(f"  Score: {result.get('score', 0)}")
        
        # 状态
        print(f"\nScheduler Status:")
        status = scheduler.get_status()
        print(f"  State: {status['state']}")
        print(f"  Check Count: {status['check_count']}")
        print(f"  Lock State: {status['lock']['state']}")
        
        print("\n" + "="*60)
    
    asyncio.run(test())
