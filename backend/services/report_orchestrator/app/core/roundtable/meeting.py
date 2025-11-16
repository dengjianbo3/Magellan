"""
Meeting: The orchestrator that manages the multi-agent discussion
Meeting: 管理多智能体讨论的编排器
"""
from typing import List, Optional, Dict, Any, Callable, Awaitable
from .agent import Agent
from .message import Message, MessageType
from .message_bus import MessageBus
from ..agent_event_bus import AgentEventBus
import asyncio
import time


class Meeting:
    """
    Meeting编排器

    职责:
    1. 初始化Agents和MessageBus
    2. 发起初始消息来启动讨论
    3. 管理turn-based或异步执行流程
    4. 通过AgentEventBus实时推送状态给前端
    5. 决定何时终止讨论
    """

    def __init__(
        self,
        agents: List[Agent],
        agent_event_bus: Optional[AgentEventBus] = None,
        max_turns: int = 20,
        max_duration_seconds: int = 300
    ):
        """
        初始化Meeting

        Args:
            agents: 参与讨论的Agent列表
            agent_event_bus: 用于实时推送的事件总线
            max_turns: 最大轮次数
            max_duration_seconds: 最大持续时间（秒）
        """
        self.agents = {agent.name: agent for agent in agents}
        self.message_bus = MessageBus()
        self.agent_event_bus = agent_event_bus
        self.max_turns = max_turns
        self.max_duration_seconds = max_duration_seconds

        # 将MessageBus注入到每个Agent
        for agent in agents:
            agent.message_bus = self.message_bus
            self.message_bus.register_agent(agent.name)

        # 讨论状态
        self.is_running = False
        self.current_turn = 0
        self.start_time = None

        # 设置消息监听器（用于实时推送）
        self.message_bus.add_listener(self._on_message)

    async def run(
        self,
        initial_message: Message,
        termination_condition: Optional[Callable[[int, List[Message]], bool]] = None
    ) -> Dict[str, Any]:
        """
        运行讨论会议

        Args:
            initial_message: 启动讨论的初始消息
            termination_condition: 可选的终止条件函数

        Returns:
            讨论结果字典
        """
        self.is_running = True
        self.start_time = time.time()
        self.current_turn = 0

        # 推送meeting开始事件
        if self.agent_event_bus:
            await self.agent_event_bus.publish_started(
                agent_name="Meeting Orchestrator",
                message=f"圆桌讨论开始，共{len(self.agents)}位专家参与"
            )

        # 发送初始消息
        await self.message_bus.send(initial_message)

        try:
            # 主循环
            while self.is_running and self.current_turn < self.max_turns:
                # 检查是否超时
                if time.time() - self.start_time > self.max_duration_seconds:
                    print("[Meeting] Timeout reached")
                    break

                # 让每个Agent思考和行动
                turn_complete = await self._execute_turn()

                if not turn_complete:
                    # 没有Agent产生新消息，讨论结束
                    print("[Meeting] No new messages, discussion complete")
                    break

                # 检查自定义终止条件
                if termination_condition:
                    history = self.message_bus.message_history
                    if termination_condition(self.current_turn, history):
                        print("[Meeting] Custom termination condition met")
                        break

                self.current_turn += 1

                # 短暂延迟，避免过快循环
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[Meeting] Error during execution: {e}")
            if self.agent_event_bus:
                await self.agent_event_bus.publish_error(
                    agent_name="Meeting Orchestrator",
                    error_message=f"讨论过程中出现错误: {str(e)}"
                )

        finally:
            self.is_running = False

            # 生成Leader最终总结
            meeting_minutes = await self._generate_leader_summary()

            # 推送meeting结束事件
            if self.agent_event_bus:
                await self.agent_event_bus.publish_completed(
                    agent_name="Meeting Orchestrator",
                    message=f"圆桌讨论结束，共进行{self.current_turn}轮对话"
                )

        # 生成讨论摘要，包含会议纪要
        summary = self._generate_summary()
        summary["meeting_minutes"] = meeting_minutes
        return summary

    async def _execute_turn(self) -> bool:
        """
        执行一轮对话

        让所有Agent依次或并发地思考和发言

        Returns:
            是否有Agent产生了新消息
        """
        has_new_messages = False

        # 策略1: 顺序执行（更可控）
        for agent_name, agent in self.agents.items():
            # 检查Agent是否有待处理消息
            pending = self.message_bus.peek_messages(agent_name)

            if not pending:
                continue

            # 推送Agent开始思考事件
            if self.agent_event_bus:
                await self.agent_event_bus.publish_thinking(
                    agent_name=agent_name,
                    message=f"{agent_name}正在思考...",
                    progress=self.current_turn / self.max_turns
                )

            # 让Agent思考并生成响应
            new_messages = await agent.think_and_act()

            if new_messages:
                has_new_messages = True

                # 发送Agent生成的所有消息
                for msg in new_messages:
                    await self.message_bus.send(msg)

                # 推送Agent发言完成事件
                if self.agent_event_bus:
                    await self.agent_event_bus.publish_result(
                        agent_name=agent_name,
                        message=f"{agent_name}发表了观点",
                        data={
                            "messages": [msg.to_dict() for msg in new_messages]
                        }
                    )

        # 策略2: 并发执行（更快但需要仔细处理）
        # tasks = []
        # for agent_name, agent in self.agents.items():
        #     pending = self.message_bus.peek_messages(agent_name)
        #     if pending:
        #         tasks.append(agent.think_and_act())
        #
        # results = await asyncio.gather(*tasks, return_exceptions=True)
        # ...

        return has_new_messages

    async def _on_message(self, message: Message):
        """
        消息监听器回调：将消息实时推送到前端

        Args:
            message: 新消息
        """
        if self.agent_event_bus:
            # 推送消息事件到前端
            from ..agent_event_bus import AgentEvent, AgentEventType
            await self.agent_event_bus.publish(
                AgentEvent(
                    agent_name=message.sender,
                    event_type=AgentEventType.RESULT,
                    message=message.content,
                    data={
                        "recipient": message.recipient,
                        "message_type": message.message_type,
                        "timestamp": message.timestamp,
                        "message_id": message.message_id,
                    }
                )
            )

    async def _generate_leader_summary(self) -> str:
        """
        让Leader生成最终总结

        Returns:
            Leader的总结性发言（Markdown格式）
        """
        print("[Meeting] Requesting Leader to generate final summary...")

        # 获取Leader
        leader = self.agents.get("Leader")
        if not leader:
            print("[Meeting] No Leader found, skipping summary generation")
            return "讨论已结束。"

        # 构建总结请求
        summary_request = Message(
            sender="Meeting Orchestrator",
            recipient="Leader",
            content="""请作为主持人，对本次圆桌讨论进行总结。

总结要求：
1. 回顾讨论的核心议题和各专家的主要观点
2. 综合各专家意见，给出平衡的结论
3. 指出意见分歧点（如果有）
4. 提供最终投资建议或决策建议
5. 使用Markdown格式，结构清晰

请生成完整的会议纪要。""",
            message_type=MessageType.QUESTION
        )

        # 发送给Leader
        self.message_bus.send_message(summary_request)

        # 让Leader思考和回复
        try:
            if self.agent_event_bus:
                await self.agent_event_bus.publish_thinking(
                    agent_name="Leader",
                    message="正在生成会议纪要..."
                )

            messages = await leader.think_and_act()

            if messages and len(messages) > 0:
                summary_content = messages[0].content

                # 发布Leader的总结
                if self.agent_event_bus:
                    await self.agent_event_bus.publish_result(
                        agent_name="Leader",
                        message=summary_content,
                        data={"message_type": "meeting_minutes"}
                    )

                print(f"[Meeting] Leader summary generated: {len(summary_content)} chars")
                return summary_content
            else:
                print("[Meeting] Leader did not generate summary")
                return "讨论已结束，但未能生成总结。"

        except Exception as e:
            print(f"[Meeting] Error generating leader summary: {e}")
            import traceback
            traceback.print_exc()
            return f"讨论已结束。（总结生成失败：{str(e)}）"

    def _generate_summary(self) -> Dict[str, Any]:
        """
        生成讨论摘要

        Returns:
            包含讨论结果的字典
        """
        message_history = self.message_bus.message_history

        # 统计各Agent的发言次数
        agent_stats = {}
        for agent_name in self.agents.keys():
            agent_messages = [msg for msg in message_history if msg.sender == agent_name]
            agent_stats[agent_name] = {
                "total_messages": len(agent_messages),
                "broadcast": len([m for m in agent_messages if m.is_broadcast()]),
                "private": len([m for m in agent_messages if m.is_private()]),
                "questions": len([m for m in agent_messages if m.is_question()]),
            }

        # 统计消息类型分布
        message_type_stats = {}
        for msg_type in MessageType:
            count = len([msg for msg in message_history if msg.message_type == msg_type])
            message_type_stats[msg_type.value] = count

        return {
            "total_turns": self.current_turn,
            "total_messages": len(message_history),
            "total_duration_seconds": time.time() - self.start_time if self.start_time else 0,
            "agent_stats": agent_stats,
            "message_type_stats": message_type_stats,
            "conversation_history": [msg.to_dict() for msg in message_history],
            "participating_agents": list(self.agents.keys()),
        }

    def pause(self):
        """暂停讨论"""
        self.is_running = False
        print("[Meeting] Discussion paused")

    def resume(self):
        """恢复讨论"""
        self.is_running = True
        print("[Meeting] Discussion resumed")

    def stop(self):
        """停止讨论"""
        self.is_running = False
        print("[Meeting] Discussion stopped")

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        获取完整对话历史

        Returns:
            消息历史列表
        """
        return [msg.to_dict() for msg in self.message_bus.message_history]

    def get_agent_context(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        获取特定Agent的对话上下文

        Args:
            agent_name: Agent名称

        Returns:
            该Agent的消息历史
        """
        if agent_name in self.agents:
            return self.agents[agent_name].get_conversation_context()
        return []


# 辅助函数：创建预设的投资分析Meeting
def create_investment_analysis_meeting(
    topic: str,
    company_name: str,
    agent_event_bus: Optional[AgentEventBus] = None
) -> Meeting:
    """
    创建一个投资分析圆桌讨论Meeting

    Args:
        topic: 讨论主题
        company_name: 公司名称
        agent_event_bus: 事件总线

    Returns:
        配置好的Meeting实例
    """
    from ..roundtable.investment_agents import (
        create_market_analyst,
        create_financial_expert,
        create_team_evaluator,
        create_risk_assessor,
        create_leader
    )

    # 创建专家团队
    agents = [
        create_leader(),
        create_market_analyst(),
        create_financial_expert(),
        create_team_evaluator(),
        create_risk_assessor(),
    ]

    # 创建Meeting
    meeting = Meeting(
        agents=agents,
        agent_event_bus=agent_event_bus,
        max_turns=15,
        max_duration_seconds=180
    )

    return meeting
