"""
Meeting: The orchestrator that manages the multi-agent discussion
Meeting: 管理多智能体讨论的编排器
"""
from typing import List, Optional, Dict, Any, Callable, Awaitable, TYPE_CHECKING
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
        max_turns: int = 5,
        max_duration_seconds: int = 300,
        llm_service: Any = None,
        on_message: Optional[Callable] = None
    ):
        """
        初始化Meeting

        Args:
            agents: 参与讨论的Agent列表
            agent_event_bus: 用于实时推送的事件总线
            max_turns: 最大轮次数
            max_duration_seconds: 最大持续时间（秒）
            llm_service: LLM服务接口（可选）
            on_message: 消息回调函数（可选）
        """
        self.agents = {agent.name: agent for agent in agents}
        self.message_bus = MessageBus()
        self.agent_event_bus = agent_event_bus
        self.max_turns = max_turns
        self.max_duration_seconds = max_duration_seconds
        self.llm_service = llm_service
        self.on_message_callback = on_message

        # Message list for TradingMeeting compatibility
        self.messages: List[Dict[str, Any]] = []

        # 将MessageBus和EventBus注入到每个Agent
        for agent in agents:
            agent.message_bus = self.message_bus
            agent.event_bus = self.agent_event_bus  # Inject event_bus for real-time progress
            self.message_bus.register_agent(agent.name)

        # 讨论状态
        self.is_running = False
        self.current_turn = 0
        self.start_time = None
        self.should_conclude = False  # Leader调用end_meeting工具时设为True
        self.conclusion_reason = ""  # 结束原因

        # Human-in-the-Loop 状态
        self.waiting_for_human = False  # 是否正在等待用户输入
        self.human_intervention_event = None  # 用于等待用户输入的异步事件

        # 设置消息监听器（用于实时推送）
        self.message_bus.add_listener(self._on_message)

    def conclude_meeting(self, reason: str = "Leader决定结束会议") -> str:
        """
        结束会议的方法，供end_meeting工具调用

        Args:
            reason: 结束原因

        Returns:
            确认消息
        """
        self.should_conclude = True
        self.conclusion_reason = reason
        print(f"[Meeting] conclude_meeting called: {reason}")
        return f"会议将在当前轮次结束后终止。原因: {reason}"

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

                # 检查Leader是否调用了end_meeting工具
                # 支持两种方式: 直接设置should_conclude 或 通过_temp_state
                if hasattr(self, '_temp_state') and self._temp_state.get("should_conclude"):
                    self.should_conclude = True
                    self.conclusion_reason = self._temp_state.get("conclusion_reason", "")

                if self.should_conclude:
                    print(f"[Meeting] Leader called end_meeting tool, concluding discussion. Reason: {self.conclusion_reason}")
                    break

                # 让每个Agent思考和行动
                turn_complete = await self._execute_turn()

                if not turn_complete:
                    # 没有Agent产生新消息，讨论结束
                    print("[Meeting] No new messages, discussion complete")
                    break

                # 再次检查（工具可能在turn中被调用）
                if hasattr(self, '_temp_state') and self._temp_state.get("should_conclude"):
                    self.should_conclude = True
                    self.conclusion_reason = self._temp_state.get("conclusion_reason", "")

                if self.should_conclude:
                    print(f"[Meeting] Leader called end_meeting tool during turn, concluding discussion. Reason: {self.conclusion_reason}")
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
        重要：Leader总是在最后处理，确保能看到其他专家的发言

        Returns:
            是否有Agent产生了新消息
        """
        has_new_messages = False

        # 将agents分为两组：普通专家 和 Leader
        # Leader必须在最后处理，否则会因为消息尚未到达而被跳过
        other_agents = {name: agent for name, agent in self.agents.items() if name != "Leader"}
        leader_agent = self.agents.get("Leader")

        # 第一步：让所有非Leader专家发言
        for agent_name, agent in other_agents.items():
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

        # 第二步：Leader在最后发言（确保能看到所有专家的观点）
        # Leader每隔几轮参与一次，或者当有足够多的新消息时参与
        if leader_agent:
            pending = self.message_bus.peek_messages("Leader")
            
            # Leader参与条件：
            # 1. 有pending消息（其他专家@了Leader）
            # 2. 或者当前轮次是3的倍数（定期主持）
            # 3. 或者超过5轮没有Leader发言
            should_leader_speak = (
                len(pending) > 0 or 
                self.current_turn % 3 == 2 or  # 第2, 5, 8, 11... 轮
                self.current_turn >= self.max_turns - 2  # 接近结束时
            )
            
            if should_leader_speak:
                # 如果没有pending消息，创建一个汇总请求让Leader思考
                if not pending:
                    # 获取最近的对话历史
                    recent_history = self.message_bus.get_conversation_history(limit=10)
                    history_text = "\n".join([
                        f"{msg.sender}: {msg.content[:200]}..." 
                        for msg in recent_history[-5:]
                    ])
                    
                    # 创建一个虚拟消息让Leader参与
                    from .message import Message
                    virtual_message = Message(
                        sender="Meeting Orchestrator",
                        recipient="Leader",
                        content=f"""作为主持人，请对当前讨论进行**阶段性总结和引导**：

## 你的主要任务（每轮必做）：
1. **总结本轮进展**：各专家提出了哪些关键观点？
2. **识别分歧点**：专家之间是否存在不同看法？
3. **引导下一轮方向**：接下来应该深入讨论哪些问题？
4. **提出深度问题**：向特定专家提问，推动讨论深入

## ⚠️ 关于结束会议（极其谨慎）：
**只有当以下ALL条件都满足时，才考虑调用 `end_meeting` 工具：**
- ✅ 已进行至少2-3轮深入讨论（不是泛泛而谈）
- ✅ 所有领域专家都基于数据发表了实质性观点
- ✅ 关键分歧点已充分辩论并达成共识
- ✅ 已形成明确、有说服力的投资建议
- ✅ 当前轮次接近 max_turns (比如 {self.max_turns - 2}/{self.max_turns} 以上)

**如果不满足上述条件，请：**
- 继续引导讨论
- 指出还需要深入的问题
- 邀请专家补充观点

最近讨论摘要：
{history_text}

当前轮次：{self.current_turn + 1}/{self.max_turns}
"""
                    )
                    self.message_bus.agent_queues["Leader"].append(virtual_message)
                
                # 推送Leader开始思考事件
                if self.agent_event_bus:
                    await self.agent_event_bus.publish_thinking(
                        agent_name="Leader",
                        message="Leader正在主持讨论...",
                        progress=self.current_turn / self.max_turns
                    )

                # 让Leader思考并生成响应
                new_messages = await leader_agent.think_and_act()

                if new_messages:
                    has_new_messages = True

                    for msg in new_messages:
                        await self.message_bus.send(msg)

                    if self.agent_event_bus:
                        await self.agent_event_bus.publish_result(
                            agent_name="Leader",
                            message="Leader发表了主持意见",
                            data={
                                "messages": [msg.to_dict() for msg in new_messages]
                            }
                        )

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

        # 临时禁用 end_meeting 工具，避免Leader在生成总结时又调用它
        # 保存当前工具，生成完毕后恢复
        saved_tools = leader.tools.copy()
        if "end_meeting" in leader.tools:
            del leader.tools["end_meeting"]
            print("[Meeting] Temporarily disabled end_meeting tool for summary generation")

        # 构建总结请求 - 明确告诉Leader会议已结束，不要调用任何工具
        summary_request = Message(
            sender="Meeting Orchestrator",
            recipient="Leader",
            content="""会议已经结束。请作为主持人，对本次圆桌讨论进行**最终总结**。

⚠️ 重要提示：
- 会议已经结束，你无需调用任何工具
- 直接用文字生成完整的会议纪要
- 不要再次尝试结束会议

总结要求：
1. 回顾讨论的核心议题和各专家的主要观点
2. 综合各专家意见，给出平衡的结论
3. 指出意见分歧点（如果有）
4. 提供最终投资建议或决策建议
5. 使用Markdown格式，结构清晰

请直接输出会议纪要内容：""",
            message_type=MessageType.QUESTION
        )

        # 发送给Leader
        await self.message_bus.send(summary_request)

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
                # 如果仍然失败，尝试使用conclusion_reason作为备选总结
                if self.conclusion_reason:
                    return f"## 会议总结\n\n{self.conclusion_reason}"
                return "讨论已结束，但未能生成总结。"

        except Exception as e:
            print(f"[Meeting] Error generating leader summary: {e}")
            import traceback
            traceback.print_exc()
            return f"讨论已结束。（总结生成失败：{str(e)}）"
        
        finally:
            # 恢复工具（虽然会议已结束，但保持代码完整性）
            leader.tools = saved_tools
            print("[Meeting] Restored Leader tools")

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

    async def request_human_intervention(self) -> str:
        """
        请求人工介入，暂停会议并等待用户输入

        Returns:
            用户输入的内容
        """
        print("[Meeting] Requesting human intervention...")
        self.waiting_for_human = True
        self.human_intervention_event = asyncio.Event()

        # 推送事件到前端，通知需要用户输入
        if self.agent_event_bus:
            await self.agent_event_bus.publish_thinking(
                agent_name="Meeting Orchestrator",
                message="⏸️ 会议已暂停，等待用户补充信息...",
                progress=self.current_turn / self.max_turns
            )

        # 等待用户输入（通过inject_human_input方法触发）
        await self.human_intervention_event.wait()

        self.waiting_for_human = False
        print("[Meeting] Human intervention received, resuming...")

        # 返回用户输入（从最新的Human消息中获取）
        human_messages = [msg for msg in self.message_bus.message_history if msg.sender == "Human"]
        if human_messages:
            return human_messages[-1].content
        return ""

    async def inject_human_input(self, content: str):
        """
        注入用户输入到讨论中（支持主动打断）

        Args:
            content: 用户补充的内容
        """
        print(f"[Meeting] Injecting human input: {content[:100]}...")

        # 创建Human消息并广播给所有Agent（特别是Leader）
        from .message import Message, MessageType
        human_message = Message(
            sender="Human",
            recipient="ALL",  # 广播给所有人
            content=f"""## 👤 用户补充信息

{content}

**重要**: 用户主动打断了讨论并补充了上述信息。

**@Leader**: 请根据这个补充信息，重新评估当前讨论进展并规划接下来的议程。具体要求：
1. 先确认收到并理解用户补充的内容
2. 评估这个补充信息对当前讨论的影响
3. 如果需要，调整后续的讨论方向和重点
4. 指派相关专家根据这个新信息进行分析

**@其他专家**: 请注意用户的补充信息，在后续发言中：
1. 如果这个信息与你的专业领域相关，请优先分析和回应
2. 如果发现用户信息与之前的分析有冲突，请指出并重新评估
3. 将这个新信息纳入到你的专业判断中""",
            message_type=MessageType.STATEMENT
        )

        # 发送到MessageBus（这样Leader和其他Agent在下次think_and_act时会看到）
        await self.message_bus.send(human_message)

        # 推送到前端
        if self.agent_event_bus:
            await self.agent_event_bus.publish_result(
                agent_name="Human",
                message=content,
                data={"message_type": "human_intervention"}
            )

        print(f"[Meeting] Human input injected successfully into message bus")

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
