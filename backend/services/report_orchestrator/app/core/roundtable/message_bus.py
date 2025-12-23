"""
MessageBus: The communication backbone of the multi-agent system
消息总线: 多智能体系统的通信骨干
"""
from typing import Dict, List, Callable, Awaitable, Optional
from .message import Message


class MessageBus:
    """
    消息总线

    职责:
    1. 接收来自一个Agent的消息
    2. 将消息路由到目标Agent(s)
    3. 解耦Agent之间的依赖关系
    """

    def __init__(self):
        # Agent消息队列: {agent_name: [messages]}
        self.agent_queues: Dict[str, List[Message]] = {}

        # Agent列表（用于广播）
        self.registered_agents: List[str] = []

        # 消息历史（用于审计和调试）
        self.message_history: List[Message] = []

        # 消息监听器（用于实时推送到前端）
        self.listeners: List[Callable[[Message], Awaitable[None]]] = []

    def register_agent(self, agent_name: str):
        """
        注册Agent到消息总线

        Args:
            agent_name: Agent的名称
        """
        if agent_name not in self.registered_agents:
            self.registered_agents.append(agent_name)
            self.agent_queues[agent_name] = []
            print(f"[MessageBus] Agent registered: {agent_name}")

    def unregister_agent(self, agent_name: str):
        """
        注销Agent

        Args:
            agent_name: Agent的名称
        """
        if agent_name in self.registered_agents:
            self.registered_agents.remove(agent_name)
            if agent_name in self.agent_queues:
                del self.agent_queues[agent_name]
            print(f"[MessageBus] Agent unregistered: {agent_name}")

    async def send(self, message: Message):
        """
        发送消息

        根据消息的recipient将消息路由到对应的Agent队列

        Args:
            message: 要发送的消息
        """
        # 记录到历史
        self.message_history.append(message)

        # 通知所有监听器
        await self._notify_listeners(message)

        # 路由消息
        if message.is_broadcast():
            # 广播给所有Agent（除了发送者）
            for agent_name in self.registered_agents:
                if agent_name != message.sender:
                    self.agent_queues[agent_name].append(message)
            print(f"[MessageBus] Broadcast from {message.sender}: {message.content[:50]}...")
        else:
            # 点对点消息
            if message.recipient in self.agent_queues:
                self.agent_queues[message.recipient].append(message)
                print(f"[MessageBus] Message from {message.sender} to {message.recipient}: {message.content[:50]}...")
            else:
                print(f"[MessageBus] Warning: Recipient {message.recipient} not found")

    def get_messages(self, agent_name: str) -> List[Message]:
        """
        获取Agent的待处理消息队列

        Args:
            agent_name: Agent名称

        Returns:
            消息列表
        """
        if agent_name in self.agent_queues:
            messages = self.agent_queues[agent_name].copy()
            self.agent_queues[agent_name].clear()  # 清空队列
            return messages
        return []

    def peek_messages(self, agent_name: str) -> List[Message]:
        """
        查看Agent的消息队列但不清空

        Args:
            agent_name: Agent名称

        Returns:
            消息列表
        """
        return self.agent_queues.get(agent_name, []).copy()

    def add_listener(self, listener: Callable[[Message], Awaitable[None]]):
        """
        添加消息监听器（用于实时推送到前端）

        Args:
            listener: 异步回调函数
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Message], Awaitable[None]]):
        """
        移除消息监听器

        Args:
            listener: 要移除的监听器
        """
        if listener in self.listeners:
            self.listeners.remove(listener)

    async def _notify_listeners(self, message: Message):
        """
        通知所有监听器有新消息

        Args:
            message: 新消息
        """
        for listener in self.listeners:
            try:
                await listener(message)
            except Exception as e:
                print(f"[MessageBus] Error in listener: {e}")

    def get_conversation_history(
        self,
        agent_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Message]:
        """
        获取对话历史

        Args:
            agent_name: 如果指定，只返回与该Agent相关的消息
            limit: 返回的最大消息数

        Returns:
            消息历史列表
        """
        history = self.message_history

        if agent_name:
            history = [
                msg for msg in history
                if msg.sender == agent_name or msg.recipient == agent_name or msg.is_broadcast()
            ]

        return history[-limit:]

    def clear_history(self):
        """清空消息历史"""
        self.message_history.clear()
        print("[MessageBus] Message history cleared")

    def get_stats(self) -> Dict[str, any]:
        """
        获取消息总线统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_agents": len(self.registered_agents),
            "agents": self.registered_agents,
            "total_messages": len(self.message_history),
            "pending_messages": {
                agent: len(msgs)
                for agent, msgs in self.agent_queues.items()
            }
        }
