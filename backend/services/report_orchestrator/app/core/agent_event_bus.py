"""
Agent Event Bus for V4
Agent事件总线 - 实时推送Agent工作状态

用于在分析过程中实时向前端推送Agent的思考过程和中间结果
"""
import asyncio
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
from fastapi import WebSocket
from starlette.websockets import WebSocketState


class AgentEventType(str, Enum):
    """Agent事件类型"""
    STARTED = "started"           # Agent开始工作
    THINKING = "thinking"         # Agent思考中
    SEARCHING = "searching"       # 正在搜索
    ANALYZING = "analyzing"       # 正在分析
    PROGRESS = "progress"         # 进度更新
    RESULT = "result"             # 中间结果
    COMPLETED = "completed"       # 完成
    ERROR = "error"               # 错误


class AgentEvent(BaseModel):
    """Agent事件"""
    agent_name: str              # Agent名称
    event_type: AgentEventType   # 事件类型
    message: str                 # 消息内容
    progress: Optional[float] = None  # 进度 (0-1)
    data: Optional[Dict[str, Any]] = None  # 附加数据
    timestamp: str = None        # 时间戳

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)


class AgentEventBus:
    """
    Agent事件总线

    负责：
    1. Agent发布事件
    2. 通过WebSocket实时推送给前端
    3. 支持多个WebSocket订阅者
    """

    def __init__(self):
        self.subscribers: List[WebSocket] = []
        self.event_history: List[AgentEvent] = []  # 事件历史（用于断线重连）
        self.max_history = 100  # 最多保留100条历史事件

    async def subscribe(self, websocket: WebSocket):
        """
        订阅事件（添加WebSocket连接）

        Args:
            websocket: WebSocket连接
        """
        if websocket not in self.subscribers:
            self.subscribers.append(websocket)
            print(f"[AgentEventBus] New subscriber added. Total: {len(self.subscribers)}")

    async def unsubscribe(self, websocket: WebSocket):
        """
        取消订阅

        Args:
            websocket: WebSocket连接
        """
        if websocket in self.subscribers:
            self.subscribers.remove(websocket)
            print(f"[AgentEventBus] Subscriber removed. Total: {len(self.subscribers)}")

    async def publish(self, event: AgentEvent):
        """
        发布事件到所有订阅者

        Args:
            event: Agent事件
        """
        # 记录事件历史
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        print(f"[AgentEventBus] Publishing event: {event.agent_name} - {event.event_type} - {event.message}")

        # 推送给所有订阅者
        disconnected = []
        for ws in self.subscribers:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json({
                        "type": "agent_event",
                        "event": event.dict()
                    })
                else:
                    print(f"[AgentEventBus] Subscriber not connected (state: {ws.client_state}), skipping", flush=True)
                    disconnected.append(ws)
            except Exception as e:
                print(f"[AgentEventBus] Error sending to subscriber: {e}")
                disconnected.append(ws)

        # 清理断开的连接
        for ws in disconnected:
            if ws in self.subscribers:
                self.subscribers.remove(ws)

    async def publish_started(self, agent_name: str, message: str):
        """快捷方法：发布Agent开始事件"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.STARTED,
            message=message,
            progress=0.0
        ))

    async def publish_thinking(self, agent_name: str, message: str, progress: Optional[float] = None):
        """快捷方法：发布Agent思考事件"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.THINKING,
            message=message,
            progress=progress
        ))

    async def publish_searching(self, agent_name: str, query: str, progress: Optional[float] = None):
        """快捷方法：发布搜索事件"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.SEARCHING,
            message=f"正在搜索: {query}",
            progress=progress,
            data={"query": query}
        ))

    async def publish_analyzing(self, agent_name: str, message: str, progress: Optional[float] = None):
        """快捷方法：发布分析事件"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.ANALYZING,
            message=message,
            progress=progress
        ))

    async def publish_progress(self, agent_name: str, message: str, progress: float):
        """快捷方法：发布进度更新"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.PROGRESS,
            message=message,
            progress=progress
        ))

    async def publish_result(self, agent_name: str, message: str, data: Optional[Dict] = None):
        """快捷方法：发布中间结果"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.RESULT,
            message=message,
            progress=1.0,
            data=data
        ))

    async def publish_completed(self, agent_name: str, message: str = "完成"):
        """快捷方法：发布完成事件"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.COMPLETED,
            message=message,
            progress=1.0
        ))

    async def publish_error(self, agent_name: str, error_message: str):
        """快捷方法：发布错误事件"""
        await self.publish(AgentEvent(
            agent_name=agent_name,
            event_type=AgentEventType.ERROR,
            message=error_message
        ))

    def get_history(self, agent_name: Optional[str] = None) -> List[AgentEvent]:
        """
        获取事件历史

        Args:
            agent_name: 如果指定，只返回该Agent的事件

        Returns:
            事件历史列表
        """
        if agent_name:
            return [e for e in self.event_history if e.agent_name == agent_name]
        return self.event_history.copy()

    def clear_history(self):
        """清空事件历史"""
        self.event_history.clear()


# 全局单例
_global_event_bus: Optional[AgentEventBus] = None


def get_event_bus() -> AgentEventBus:
    """获取全局事件总线实例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = AgentEventBus()
    return _global_event_bus
