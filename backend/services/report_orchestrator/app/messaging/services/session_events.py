"""
Session Event Publisher
会话事件发布器

提供会话状态事件的发布能力，用于：
- 实时进度更新
- 分析状态通知
- WebSocket 集成
"""
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..messages import SessionEvent, MessageType
from ..topics import MagellanTopics
from ..kafka_client import get_kafka_client

logger = logging.getLogger(__name__)


class SessionEventType(str, Enum):
    """会话事件类型"""
    # 会话生命周期
    SESSION_STARTED = "session.started"
    SESSION_COMPLETED = "session.completed"
    SESSION_FAILED = "session.failed"
    SESSION_CANCELLED = "session.cancelled"

    # 分析进度
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_STEP_STARTED = "analysis.step.started"
    ANALYSIS_STEP_COMPLETED = "analysis.step.completed"
    ANALYSIS_STEP_FAILED = "analysis.step.failed"
    ANALYSIS_COMPLETED = "analysis.completed"

    # Agent 事件
    AGENT_STARTED = "agent.started"
    AGENT_THINKING = "agent.thinking"
    AGENT_TOOL_CALLING = "agent.tool_calling"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # 报告事件
    REPORT_GENERATING = "report.generating"
    REPORT_READY = "report.ready"


class SessionEventPublisher:
    """
    会话事件发布器

    用于发布会话相关的实时事件
    """

    def __init__(self):
        self._kafka_client = None
        self._local_handlers: List = []  # 本地事件处理器（用于 WebSocket）

    async def initialize(self):
        """初始化发布器"""
        self._kafka_client = get_kafka_client()
        logger.info("Session event publisher initialized")

    def add_local_handler(self, handler):
        """添加本地事件处理器"""
        self._local_handlers.append(handler)

    def remove_local_handler(self, handler):
        """移除本地事件处理器"""
        if handler in self._local_handlers:
            self._local_handlers.remove(handler)

    async def publish(
        self,
        session_id: str,
        event_type: SessionEventType,
        data: Dict[str, Any] = None,
        progress: float = None,
        status: str = None,
        trace_id: str = None
    ):
        """
        发布会话事件

        Args:
            session_id: 会话 ID
            event_type: 事件类型
            data: 事件数据
            progress: 进度 (0-100)
            status: 会话状态
            trace_id: 追踪 ID
        """
        event = SessionEvent(
            source="report_orchestrator",
            destination="session_listeners",
            session_id=session_id,
            trace_id=trace_id or str(uuid.uuid4()),
            event_type=event_type.value,
            event_data=data or {},
            progress=progress,
            session_status=status
        )

        # 发送到 Kafka
        if self._kafka_client and self._kafka_client.is_available:
            try:
                await self._kafka_client.send(MagellanTopics.SESSION_EVENTS, event)
            except Exception as e:
                logger.warning(f"Failed to publish event to Kafka: {e}")

        # 同时通知本地处理器（用于 WebSocket）
        for handler in self._local_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.warning(f"Local handler error: {e}")

    # 便捷方法

    async def session_started(
        self,
        session_id: str,
        scenario: str,
        target: Dict[str, Any],
        trace_id: str = None
    ):
        """发布会话开始事件"""
        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.SESSION_STARTED,
            data={
                "scenario": scenario,
                "target": target,
                "started_at": datetime.now().isoformat()
            },
            progress=0,
            status="active",
            trace_id=trace_id
        )

    async def session_completed(
        self,
        session_id: str,
        result: Dict[str, Any] = None,
        trace_id: str = None
    ):
        """发布会话完成事件"""
        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.SESSION_COMPLETED,
            data={
                "result": result,
                "completed_at": datetime.now().isoformat()
            },
            progress=100,
            status="completed",
            trace_id=trace_id
        )

    async def session_failed(
        self,
        session_id: str,
        error: str,
        trace_id: str = None
    ):
        """发布会话失败事件"""
        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.SESSION_FAILED,
            data={
                "error": error,
                "failed_at": datetime.now().isoformat()
            },
            status="failed",
            trace_id=trace_id
        )

    async def analysis_step_started(
        self,
        session_id: str,
        step_name: str,
        step_index: int,
        total_steps: int,
        trace_id: str = None
    ):
        """发布分析步骤开始事件"""
        progress = (step_index / total_steps) * 100 if total_steps > 0 else 0

        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.ANALYSIS_STEP_STARTED,
            data={
                "step_name": step_name,
                "step_index": step_index,
                "total_steps": total_steps
            },
            progress=progress,
            status="active",
            trace_id=trace_id
        )

    async def analysis_step_completed(
        self,
        session_id: str,
        step_name: str,
        step_index: int,
        total_steps: int,
        result: Dict[str, Any] = None,
        trace_id: str = None
    ):
        """发布分析步骤完成事件"""
        progress = ((step_index + 1) / total_steps) * 100 if total_steps > 0 else 100

        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.ANALYSIS_STEP_COMPLETED,
            data={
                "step_name": step_name,
                "step_index": step_index,
                "total_steps": total_steps,
                "result_summary": result.get("summary") if result else None
            },
            progress=progress,
            status="active",
            trace_id=trace_id
        )

    async def agent_started(
        self,
        session_id: str,
        agent_id: str,
        agent_name: str,
        trace_id: str = None
    ):
        """发布 Agent 开始事件"""
        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.AGENT_STARTED,
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "started_at": datetime.now().isoformat()
            },
            trace_id=trace_id
        )

    async def agent_completed(
        self,
        session_id: str,
        agent_id: str,
        agent_name: str,
        execution_time_ms: int = None,
        trace_id: str = None
    ):
        """发布 Agent 完成事件"""
        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.AGENT_COMPLETED,
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "execution_time_ms": execution_time_ms,
                "completed_at": datetime.now().isoformat()
            },
            trace_id=trace_id
        )

    async def report_ready(
        self,
        session_id: str,
        report_id: str,
        report_url: str = None,
        trace_id: str = None
    ):
        """发布报告就绪事件"""
        await self.publish(
            session_id=session_id,
            event_type=SessionEventType.REPORT_READY,
            data={
                "report_id": report_id,
                "report_url": report_url,
                "ready_at": datetime.now().isoformat()
            },
            progress=100,
            status="completed",
            trace_id=trace_id
        )


# 单例
_session_publisher: Optional[SessionEventPublisher] = None


async def get_session_publisher() -> SessionEventPublisher:
    """获取会话事件发布器单例"""
    global _session_publisher
    if _session_publisher is None:
        _session_publisher = SessionEventPublisher()
        await _session_publisher.initialize()
    return _session_publisher
