"""
Trigger Scheduler - 触发器调度器

三层触发架构：
  Layer 1: FastMonitor (每次检查，无LLM) - 硬条件检测
  Layer 2: TriggerAgent (条件触发，LLM) - 深度分析
  Layer 3: Full Analysis (触发后，完整分析)
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
    from .fast_monitor import FastMonitor, FastTriggerResult
    from ..exceptions import TriggerError, LLMError
except ImportError:
    from agent import TriggerAgent, TriggerContext
    from lock import TriggerLock
    from fast_monitor import FastMonitor, FastTriggerResult
    TriggerError = Exception
    LLMError = Exception

logger = logging.getLogger(__name__)


class SchedulerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class TriggerScheduler:
    """
    三层触发器调度器
    
    Layer 1: FastMonitor (硬条件检测，无 LLM)
    Layer 2: TriggerAgent (LLM 深度分析)
    Layer 3: Full Analysis (完整多 Agent 分析)
    """
    
    def __init__(
        self,
        trigger_agent: Optional[TriggerAgent] = None,
        trigger_lock: Optional[TriggerLock] = None,
        fast_monitor: Optional[FastMonitor] = None,
        interval_minutes: int = None,
        cooldown_minutes: int = None,
        on_trigger: Optional[Callable[[TriggerContext], Awaitable[None]]] = None
    ):
        # 从环境变量读取配置
        self.interval_minutes = interval_minutes or int(os.getenv("TRIGGER_INTERVAL_MINUTES", "5"))  # 默认5分钟
        cooldown = cooldown_minutes or int(os.getenv("TRIGGER_COOLDOWN_MINUTES", "30"))
        
        self.trigger_agent = trigger_agent or TriggerAgent()
        self.trigger_lock = trigger_lock or TriggerLock(cooldown_minutes=cooldown)
        self.fast_monitor = fast_monitor or FastMonitor()  # Layer 1: 快速监控
        self.on_trigger = on_trigger  # 触发时的回调
        
        # 配置: 是否启用 FastMonitor 硬条件检测
        self.fast_monitor_enabled = os.getenv("FAST_MONITOR_ENABLED", "true").lower() == "true"
        
        self._state = SchedulerState.IDLE
        self._task: Optional[asyncio.Task] = None
        self._check_count = 0
        self._trigger_count = 0
        self._fast_trigger_count = 0  # FastMonitor 触发计数
        self._last_check_time: Optional[datetime] = None
        
        logger.info(f"[TriggerScheduler] Initialized - FastMonitor: {'enabled' if self.fast_monitor_enabled else 'disabled'}")
    
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
        logger.info(f"[TriggerScheduler] Started, interval={self.interval_minutes}min, FastMonitor={self.fast_monitor_enabled}")
    
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
        while self._state == SchedulerState.RUNNING:
            try:
                await self.run_check()

            except TriggerError as e:
                logger.error(f"[TriggerScheduler] Trigger system error: {e}")
            except LLMError as e:
                logger.error(f"[TriggerScheduler] LLM error: {e}")
            except asyncio.CancelledError:
                logger.info("[TriggerScheduler] Loop cancelled")
                break
            except Exception as e:
                logger.error(f"[TriggerScheduler] Unexpected error: {type(e).__name__}: {e}")
            
            # 等待下一次检查
            await asyncio.sleep(self.interval_minutes * 60)
    
    async def run_check(self) -> Dict:
        """
        执行三层触发检查
        
        Layer 1: FastMonitor (硬条件，无 LLM)
        Layer 2: TriggerAgent (LLM 深度分析) - 仅当 Layer 1 触发时
        Layer 3: Full Analysis - 仅当 Layer 2 触发时
        
        Returns:
            检查结果字典
        """
        self._check_count += 1
        self._last_check_time = datetime.now()
        
        logger.info(f"[TriggerScheduler] Running check #{self._check_count}")
        
        # ========== Layer 1: FastMonitor 硬条件检测 ==========
        fast_result: Optional[FastTriggerResult] = None
        
        if self.fast_monitor_enabled:
            try:
                fast_result = await self.fast_monitor.check()
                
                if fast_result.should_trigger:
                    self._fast_trigger_count += 1
                    conditions_str = ", ".join([c.name for c in fast_result.conditions])
                    logger.info(f"[TriggerScheduler] [FAST] FastMonitor triggered: [{conditions_str}] urgency={fast_result.urgency}")
                else:
                    logger.debug("[TriggerScheduler] FastMonitor: No hard conditions triggered")
            except TriggerError as e:
                logger.error(f"[TriggerScheduler] FastMonitor trigger error: {e}")
                # FastMonitor 失败不阻塞后续流程
        
        # 决定是否需要运行 Layer 2 (TriggerAgent)
        # 条件: FastMonitor 触发，或者 FastMonitor 未启用/出错
        should_run_layer2 = (
            not self.fast_monitor_enabled or  # FastMonitor 未启用
            fast_result is None or            # FastMonitor 出错
            fast_result.should_trigger        # FastMonitor 触发
        )
        
        if not should_run_layer2:
            # FastMonitor 运行正常但未触发，跳过 Layer 2
            return {
                "skipped": False,
                "layer1_triggered": False,
                "layer2_skipped": True,
                "reason": "FastMonitor: market calm",
                "check_number": self._check_count
            }
        
        # ========== Layer 2: TriggerAgent LLM 分析 ==========
        
        # 尝试获取 CHECK 锁
        if not await self.trigger_lock.acquire_check():
            reason = f"Lock busy (State: {self.trigger_lock.state})"
            logger.info(f"[TriggerScheduler] Skipped Layer 2: {reason}")
            return {
                "skipped": True,
                "layer1_triggered": fast_result.should_trigger if fast_result else False,
                "reason": reason,
                "check_number": self._check_count
            }
        
        try:
            # 运行 TriggerAgent
            should_trigger, context = await self.trigger_agent.check()
            
            result = {
                "skipped": False,
                "layer1_triggered": fast_result.should_trigger if fast_result else False,
                "layer1_conditions": [c.name for c in fast_result.conditions] if fast_result else [],
                "should_trigger": should_trigger,
                "confidence": context.confidence,
                "urgency": context.urgency,
                "check_number": self._check_count,
                "context": context.to_dict()
            }
            
            if not should_trigger:
                logger.info(f"[TriggerScheduler] TriggerAgent: No trigger, confidence={context.confidence}%")
                self.trigger_lock.release_check()
                return result
            
            # ========== Layer 3: 触发完整分析 ==========
            self._trigger_count += 1
            logger.info(f"[TriggerScheduler] [TARGET] TRIGGER! Confidence={context.confidence}%, Urgency={context.urgency}")
            
            # 释放 Check 锁
            self.trigger_lock.release_check()
            
            if self.on_trigger:
                await self.on_trigger(context)
                result["callback_executed"] = True
            else:
                logger.info("[TriggerScheduler] No callback configured")
                result["callback_executed"] = False
            
            return result
            
        except LLMError as e:
            logger.error(f"[TriggerScheduler] LLM error during Layer 2 check: {e}")
            self.trigger_lock.release_check()
            raise TriggerError(f"LLM analysis failed: {e}") from e
        except TriggerError as e:
            logger.error(f"[TriggerScheduler] Trigger error during Layer 2 check: {e}")
            self.trigger_lock.release_check()
            raise
        except Exception as e:
            logger.error(f"[TriggerScheduler] Unexpected error during Layer 2 check: {type(e).__name__}: {e}")
            self.trigger_lock.release_check()
            raise TriggerError(f"Layer 2 check failed: {e}") from e
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        lock_status = self.trigger_lock.get_status()
        agent_status = self.trigger_agent.get_status()
        
        return {
            "state": self._state.value,
            "interval_minutes": self.interval_minutes,
            "fast_monitor_enabled": self.fast_monitor_enabled,
            "check_count": self._check_count,
            "trigger_count": self._trigger_count,
            "fast_trigger_count": self._fast_trigger_count,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "lock": {
                "state": lock_status.state,
                "can_trigger": lock_status.can_trigger,
                "cooldown_remaining": lock_status.cooldown_remaining_seconds
            },
            "agent": agent_status,
            "fast_monitor": self.fast_monitor.get_status() if self.fast_monitor else None
        }


# 测试入口
if __name__ == "__main__":
    async def test():
        print("\n" + "="*60)
        print("TriggerScheduler Test (with FastMonitor)")
        print("="*60)
        
        # 模拟触发回调
        async def mock_on_trigger(context: TriggerContext):
            print(f"\n[CALLBACK] Main analysis would be triggered!")
            print(f"  Confidence: {context.confidence}%")
            print(f"  Urgency: {context.urgency}")
        
        scheduler = TriggerScheduler(
            interval_minutes=1,  # 测试用 1 分钟
            on_trigger=mock_on_trigger
        )
        
        # 单次检查测试
        print("\n--- Running single check ---")
        result = await scheduler.run_check()
        
        print(f"\nResult:")
        print(f"  Skipped: {result.get('skipped', False)}")
        print(f"  Layer 1 Triggered: {result.get('layer1_triggered', 'N/A')}")
        print(f"  Layer 1 Conditions: {result.get('layer1_conditions', [])}")
        print(f"  Should Trigger: {result.get('should_trigger', False)}")
        print(f"  Confidence: {result.get('confidence', 'N/A')}")
        
        # 状态
        print(f"\nScheduler Status:")
        status = scheduler.get_status()
        print(f"  State: {status['state']}")
        print(f"  FastMonitor Enabled: {status['fast_monitor_enabled']}")
        print(f"  Check Count: {status['check_count']}")
        print(f"  Fast Trigger Count: {status['fast_trigger_count']}")
        print(f"  Lock State: {status['lock']['state']}")
        
        print("\n" + "="*60)
    
    asyncio.run(test())
