"""
Agent: The fundamental actor in the multi-agent system
Agent: 多智能体系统中的基本行动者
"""
from typing import List, Dict, Any, Optional
from .message import Message, MessageType
from .tool import Tool
from .message_bus import MessageBus
import httpx
import json


class Agent:
    """
    Agent抽象基类

    代表系统中的自主实体,负责:
    - 处理收到的消息
    - 使用工具获取信息
    - 与LLM交互进行推理
    - 生成并发送新消息
    """

    def __init__(
        self,
        name: str,
        role_prompt: str,
        llm_gateway_url: str = "http://llm_gateway:8003",
        model: str = "gpt-4",
        temperature: float = 0.7
    ):
        """
        初始化Agent

        Args:
            name: Agent的唯一标识符(如"MarketAnalyst")
            role_prompt: 定义Agent的人格、专长和目标的系统提示
            llm_gateway_url: LLM网关服务的URL
            model: 使用的模型名称
            temperature: 生成温度参数
        """
        self.name = name
        self.role_prompt = role_prompt
        self.llm_gateway_url = llm_gateway_url
        self.model = model
        self.temperature = temperature

        # 工具注册表
        self.tools: Dict[str, Tool] = {}

        # 消息历史（Agent的私有记忆）
        self.message_history: List[Message] = []

        # MessageBus引用（由Meeting设置）
        self.message_bus: Optional[MessageBus] = None

        # Agent当前状态
        self.status = "idle"  # idle, thinking, tool_using, speaking

    def register_tool(self, tool: Tool):
        """
        注册工具到Agent的工具带

        Args:
            tool: 要注册的工具
        """
        self.tools[tool.name] = tool
        print(f"[Agent:{self.name}] Tool registered: {tool.name}")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的Schema（用于LLM function calling）

        Returns:
            工具Schema列表
        """
        return [tool.to_schema() for tool in self.tools.values()]

    async def think_and_act(self) -> List[Message]:
        """
        Agent的主循环：处理消息、决策、生成响应

        Returns:
            要发送的消息列表
        """
        if not self.message_bus:
            raise RuntimeError(f"Agent {self.name} not connected to MessageBus")

        # 1. 获取待处理消息
        new_messages = self.message_bus.get_messages(self.name)

        if not new_messages:
            return []

        # 2. 更新消息历史
        self.message_history.extend(new_messages)

        # 3. 状态更新：思考中
        self.status = "thinking"

        # 4. 构建LLM提示
        prompt_messages = self._build_llm_prompt()

        # 5. 调用LLM进行推理
        llm_response = await self._call_llm(prompt_messages)

        # 6. 解析LLM响应
        outgoing_messages = await self._parse_llm_response(llm_response)

        # 7. 状态更新：空闲
        self.status = "idle"

        return outgoing_messages

    def _build_llm_prompt(self) -> List[Dict[str, str]]:
        """
        构建发送给LLM的提示消息

        Returns:
            符合OpenAI格式的消息列表
        """
        messages = []

        # 系统提示（定义角色）
        messages.append({
            "role": "system",
            "content": self._get_system_prompt()
        })

        # 对话历史
        for msg in self.message_history[-10:]:  # 只保留最近10条
            # 根据消息发送者确定角色
            if msg.sender == self.name:
                role = "assistant"
            else:
                role = "user"

            content = f"[{msg.sender} → {msg.recipient}] {msg.content}"
            messages.append({
                "role": role,
                "content": content
            })

        return messages

    def _get_system_prompt(self) -> str:
        """
        获取完整的系统提示

        Returns:
            系统提示字符串
        """
        base_prompt = f"""你是 {self.name}，一个投资分析专家团队的成员。

{self.role_prompt}

## 你的工作方式:
1. **仔细阅读**所有收到的消息和讨论历史
2. **分析问题**从你的专业角度思考
3. **使用工具**如果需要数据支持，使用你的专业工具
4. **表达观点**:
   - 可以同意或反对其他专家的观点
   - 可以向特定专家提问
   - 可以请求与某个专家私聊
   - 可以分享你的思考过程

## 消息格式规范:
- **广播发言**: 发送给 "ALL"，所有专家都能看到
- **提问**: 使用 @专家名 提问特定专家
- **私聊**: 明确说明 "私聊给XXX" 或 "私下与XXX讨论"
- **表态**: 可以说"我同意XXX的观点"或"我不同意XXX的看法"

## 你可用的工具:
"""
        # 添加工具描述
        if self.tools:
            for tool_name, tool in self.tools.items():
                base_prompt += f"\n- **{tool_name}**: {tool.description}"
            base_prompt += """

## 如何使用工具:
当你需要使用工具获取信息时，请在回复中使用以下格式：
[USE_TOOL: tool_name(param1="value1", param2="value2")]

例如：
- 搜索信息: [USE_TOOL: tavily_search(query="特斯拉2024年Q4销量")]
- 查询公司数据: [USE_TOOL: get_public_company_data(company_name="特斯拉")]
- 搜索知识库: [USE_TOOL: search_knowledge_base(query="特斯拉财务分析")]

使用工具后，你会收到工具返回的结果，然后基于这些结果继续讨论。
"""
        else:
            base_prompt += "\n（当前没有可用工具）"

        base_prompt += """

## 重要提醒:
- 保持专业但自然的沟通风格
- 从你的专业角度提供有价值的见解
- 不要重复其他专家已经说过的观点，除非你有新的角度
- 如果需要数据支持你的观点，主动使用可用的工具
- 如果不确定，可以坦诚表达并寻求更多信息
- 记住这是一个协作讨论，目标是得出最佳投资决策
"""
        return base_prompt

    async def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        调用LLM网关进行推理

        Args:
            messages: 符合OpenAI格式的消息列表

        Returns:
            LLM的响应
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 转换为 LLM Gateway 格式
            # LLM Gateway 期望: {"history": [{"role": "user", "parts": ["text"]}]}
            history = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                # Convert role: system/user/assistant -> user/model
                if role == "system" or role == "user":
                    history.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    history.append({"role": "model", "parts": [content]})

            request_data = {
                "history": history
            }

            try:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json=request_data
                )
                response.raise_for_status()
                result = response.json()

                # 转换响应格式，使其兼容 OpenAI 格式的解析
                # LLM Gateway 返回: {"content": "text"}
                # 转换为: {"choices": [{"message": {"content": "text"}}]}
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": result["content"]
                            }
                        }
                    ]
                }
            except Exception as e:
                print(f"[Agent:{self.name}] LLM call failed: {e}")
                raise

    async def _parse_llm_response(self, llm_response: Dict[str, Any]) -> List[Message]:
        """
        解析LLM的响应并生成消息

        Args:
            llm_response: LLM的原始响应

        Returns:
            要发送的消息列表
        """
        messages_to_send = []

        try:
            choice = llm_response["choices"][0]
            message = choice["message"]

            # 提取文本内容
            content = message.get("content", "")

            # 检测工具调用 - 使用自定义格式 [USE_TOOL: tool_name(params)]
            import re
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content)

            if tool_matches and self.tools:
                # 有工具调用
                self.status = "tool_using"
                tool_results = []

                for tool_name, params_str in tool_matches:
                    if tool_name in self.tools:
                        print(f"[Agent:{self.name}] Using tool: {tool_name}")

                        # 解析参数
                        try:
                            # 支持双引号和单引号: key="value" 或 key='value'
                            params = {}
                            # 先尝试双引号
                            param_pattern_double = r'(\w+)="([^"]*)"'
                            param_matches = re.findall(param_pattern_double, params_str)
                            # 再尝试单引号
                            if not param_matches:
                                param_pattern_single = r"(\w+)='([^']*)'"
                                param_matches = re.findall(param_pattern_single, params_str)

                            for key, value in param_matches:
                                params[key] = value

                            # 执行工具
                            tool_result = await self.tools[tool_name].execute(**params)
                            print(f"[Agent:{self.name}] Tool {tool_name} result: {tool_result}")

                            # 收集工具结果
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name}结果]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name}结果]: {str(tool_result)[:500]}")

                        except Exception as tool_error:
                            print(f"[Agent:{self.name}] Tool {tool_name} error: {tool_error}")
                            tool_results.append(f"\n[{tool_name}错误]: {str(tool_error)}")

                # 如果有工具结果，将其添加到内容中
                if tool_results:
                    content += "\n\n" + "\n".join(tool_results)

            if content:
                # 分析消息类型和目标接收者
                message_type, recipient = self._analyze_message_intent(content)

                msg = Message(
                    sender=self.name,
                    recipient=recipient,
                    content=content,
                    message_type=message_type
                )

                messages_to_send.append(msg)
                self.message_history.append(msg)

        except Exception as e:
            print(f"[Agent:{self.name}] Failed to parse LLM response: {e}")
            import traceback
            traceback.print_exc()

        return messages_to_send

    def _analyze_message_intent(self, content: str) -> tuple[MessageType, str]:
        """
        分析消息内容，确定消息类型和接收者

        Args:
            content: 消息内容

        Returns:
            (消息类型, 接收者名称)
        """
        content_lower = content.lower()

        # 检测私聊意图
        if "私聊" in content or "私下" in content or "单独" in content:
            # 尝试提取目标Agent（简化处理）
            for agent_name in self.message_bus.registered_agents:
                if agent_name.lower() in content_lower and agent_name != self.name:
                    return (MessageType.PRIVATE, agent_name)
            return (MessageType.PRIVATE, "ALL")

        # 检测提问意图
        if "@" in content or "请问" in content or "想问" in content:
            # 尝试提取目标Agent
            for agent_name in self.message_bus.registered_agents:
                if agent_name in content and agent_name != self.name:
                    return (MessageType.QUESTION, agent_name)
            return (MessageType.QUESTION, "ALL")

        # 检测赞同/反对
        if "同意" in content or "赞同" in content:
            return (MessageType.AGREEMENT, "ALL")
        if "不同意" in content or "反对" in content:
            return (MessageType.DISAGREEMENT, "ALL")

        # 默认为广播消息
        return (MessageType.BROADCAST, "ALL")

    def get_conversation_context(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取对话上下文（用于调试或展示）

        Args:
            limit: 返回的最大消息数

        Returns:
            消息历史列表
        """
        return [msg.to_dict() for msg in self.message_history[-limit:]]
