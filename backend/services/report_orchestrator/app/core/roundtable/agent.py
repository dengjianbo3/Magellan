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
        role_prompt: str = None,
        llm_gateway_url: str = "http://llm_gateway:8003",
        model: str = "gpt-4",
        temperature: float = 0.7,
        # Extended parameters for trading agents
        id: str = None,
        role: str = None,
        personality: str = None,
        system_prompt: str = None,
        expertise: List[str] = None,
        avatar: str = None
    ):
        """
        初始化Agent

        Args:
            name: Agent的显示名称
            role_prompt: 定义Agent的人格、专长和目标的系统提示
            llm_gateway_url: LLM网关服务的URL
            model: 使用的模型名称
            temperature: 生成温度参数
            id: Agent的唯一标识符（可选，默认使用name）
            role: Agent的角色描述
            personality: Agent的个性描述
            system_prompt: 系统提示（与role_prompt可互换）
            expertise: Agent的专长领域列表
            avatar: Agent的头像图标
        """
        self.id = id or name  # Use id if provided, otherwise use name
        self.name = name
        self.role = role or name
        self.personality = personality or ""
        self.expertise = expertise or []
        self.avatar = avatar or "person"

        # System prompt can be specified as role_prompt or system_prompt
        self.role_prompt = role_prompt or system_prompt or ""
        self.system_prompt = self.role_prompt  # Alias for compatibility

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

        # 对话历史 - 保留更多上下文以避免丢失关键信息
        for msg in self.message_history[-20:]:  # 保留最近20条
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

### ⚠️ 时效性搜索指引 (重要!):
对于需要最新信息的问题，**必须**使用时间过滤参数：
- 最近24小时: [USE_TOOL: tavily_search(query="比特币价格", time_range="day")]
- 最近一周: [USE_TOOL: tavily_search(query="市场新闻", time_range="week")]
- 最近一个月: [USE_TOOL: tavily_search(query="财报分析", time_range="month")]
- 新闻搜索(指定天数): [USE_TOOL: tavily_search(query="股票动态", topic="news", days=3)]

**判断标准**: 如果问题涉及"最近"、"最新"、"今天"、"本周"、"当前价格"等时间敏感词汇，
或涉及短期预测（如"未来3天"），必须使用time_range或days参数限制搜索范围。

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

    async def _call_llm(self, messages: List[Dict[str, str]], max_retries: int = 3) -> Dict[str, Any]:
        """
        调用LLM网关进行推理（带重试机制，支持 Tool Calling）

        Args:
            messages: 符合OpenAI格式的消息列表
            max_retries: 最大重试次数

        Returns:
            LLM的响应
        """
        import asyncio

        last_exception = None

        # 检查是否有工具可用
        has_tools = len(self.tools) > 0

        # 如果有工具，使用新的 Tool Calling 端点
        if has_tools:
            # 使用 OpenAI 兼容的 /v1/chat/completions 端点
            tools_schema = self.get_tools_schema()

            request_data = {
                "messages": messages,  # 直接传递 OpenAI 格式的 messages
                "tools": tools_schema,
                "tool_choice": "auto",
                "temperature": self.temperature
            }

            print(f"[Agent:{self.name}] Using Tool Calling with {len(tools_schema)} tools")

            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=180.0) as client:
                        response = await client.post(
                            f"{self.llm_gateway_url}/v1/chat/completions",
                            json=request_data
                        )
                        response.raise_for_status()
                        result = response.json()

                        # result is already in OpenAI format
                        return result

                except httpx.ReadTimeout as e:
                    last_exception = e
                    print(f"[Agent:{self.name}] LLM timeout on attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** (attempt + 1)
                        print(f"[Agent:{self.name}] Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    continue

                except Exception as e:
                    last_exception = e
                    print(f"[Agent:{self.name}] LLM call failed on attempt {attempt + 1}/{max_retries}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    continue

            # 所有重试都失败
            print(f"[Agent:{self.name}] All {max_retries} LLM call attempts failed")
            raise last_exception

        else:
            # 没有工具，使用旧的 /chat 端点（向后兼容）
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
                "history": history,
                "temperature": self.temperature  # 传递temperature参数
            }

            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=180.0) as client:
                        response = await client.post(
                            f"{self.llm_gateway_url}/chat",
                            json=request_data
                        )
                        response.raise_for_status()
                        result = response.json()

                        # 调试：打印响应类型和内容
                        print(f"[Agent:{self.name}] LLM response type: {type(result)}")

                        # 转换响应格式，使其兼容 OpenAI 格式的解析
                        # LLM Gateway 返回: {"content": "text"}
                        # 转换为: {"choices": [{"message": {"content": "text"}}]}

                        # 处理两种可能的响应格式
                        if isinstance(result, str):
                            # 如果result是字符串，直接使用
                            content = result
                        elif isinstance(result, dict):
                            # 如果是字典，提取content字段
                            content = result.get("content", str(result))
                        else:
                            # 其他类型，转为字符串
                            content = str(result)

                        return {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": content
                                    }
                                }
                            ]
                        }

                except httpx.ReadTimeout as e:
                    last_exception = e
                    print(f"[Agent:{self.name}] LLM timeout on attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        # 指数退避：2秒, 4秒, 8秒...
                        wait_time = 2 ** (attempt + 1)
                        print(f"[Agent:{self.name}] Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    continue

                except Exception as e:
                    last_exception = e
                    print(f"[Agent:{self.name}] LLM call failed on attempt {attempt + 1}/{max_retries}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    continue

            # 所有重试都失败
            print(f"[Agent:{self.name}] All {max_retries} LLM call attempts failed")
            raise last_exception

    async def _parse_llm_response(self, llm_response: Dict[str, Any]) -> List[Message]:
        """
        解析LLM的响应并生成消息（支持原生 Tool Calling）

        Args:
            llm_response: LLM的原始响应

        Returns:
            要发送的消息列表
        """
        messages_to_send = []

        try:
            choice = llm_response["choices"][0]
            message = choice["message"]

            # 检查是否有原生的 tool_calls (OpenAI 格式)
            if message.get("tool_calls") and self.tools:
                # 原生 Tool Calling
                self.status = "tool_using"
                tool_results = []

                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    if tool_name in self.tools:
                        print(f"[Agent:{self.name}] Native Tool Calling: {tool_name}")

                        try:
                            # 解析 JSON 参数
                            import json
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str

                            print(f"[Agent:{self.name}] Tool arguments: {tool_args}")

                            # 执行工具
                            tool_result = await self.tools[tool_name].execute(**tool_args)
                            print(f"[Agent:{self.name}] Tool {tool_name} result: {tool_result}")

                            # 收集工具结果
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name}结果]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name}结果]: {str(tool_result)[:500]}")

                        except Exception as e:
                            print(f"[Agent:{self.name}] Tool execution failed: {e}")
                            tool_results.append(f"\n[{tool_name}错误]: {str(e)}")
                    else:
                        print(f"[Agent:{self.name}] Unknown tool: {tool_name}")

                # 返回工具结果作为消息
                if tool_results:
                    combined_result = "".join(tool_results)
                    messages_to_send.append(Message(
                        agent_name=self.name,
                        content=combined_result,
                        message_type=MessageType.INFORMATION
                    ))

                self.status = "idle"
                return messages_to_send

            # 提取文本内容
            content = message.get("content", "")

            # 向后兼容：检测自定义格式的工具调用 [USE_TOOL: tool_name(params)]
            import re
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content)

            if tool_matches and self.tools:
                # 有工具调用（向后兼容模式）
                self.status = "tool_using"
                tool_results = []

                for tool_name, params_str in tool_matches:
                    if tool_name in self.tools:
                        print(f"[Agent:{self.name}] Legacy tool calling: {tool_name}")

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

    async def analyze(self, target: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        单独执行分析（兼容BaseOrchestrator接口）

        这是一个适配方法，允许Agent在BaseOrchestrator的workflow中独立执行分析，
        而不需要完整的roundtable meeting环境。

        Args:
            target: 分析目标数据
            context: 上下文信息（可选）

        Returns:
            分析结果字典
        """
        # 构建分析提示
        analysis_prompt = f"""请分析以下投资标的:

{json.dumps(target, ensure_ascii=False, indent=2)}

请从你的专业角度提供分析，包括:
1. 关键发现
2. 风险因素
3. 优势分析
4. 评分(1-10分)
5. 投资建议

请使用工具获取必要的数据支持你的分析。"""

        # 创建一个虚拟的分析消息
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            },
            {
                "role": "user",
                "content": analysis_prompt
            }
        ]

        # 调用LLM进行分析
        try:
            llm_response = await self._call_llm(messages)

            # 详细日志：打印响应类型和内容
            print(f"[Agent:{self.name}] 🔍 DEBUG: llm_response type = {type(llm_response)}")
            print(f"[Agent:{self.name}] 🔍 DEBUG: llm_response = {str(llm_response)[:200]}")

            # 安全提取content - 处理可能的类型问题
            if isinstance(llm_response, str):
                # 如果响应是字符串，直接使用
                print(f"[Agent:{self.name}] ✅ Response is string, using directly")
                content = llm_response
            elif isinstance(llm_response, dict) and "choices" in llm_response:
                # 标准格式
                print(f"[Agent:{self.name}] ✅ Response is dict with 'choices', extracting content")
                choice = llm_response["choices"][0]
                content = choice["message"].get("content", "")
            else:
                # 未知格式，尝试转为字符串
                print(f"[Agent:{self.name}] ⚠️ WARNING: Unexpected llm_response type: {type(llm_response)}")
                print(f"[Agent:{self.name}] ⚠️ WARNING: Full response: {llm_response}")
                content = str(llm_response)

            # 检测并执行工具调用
            import re
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content)

            if tool_matches and self.tools:
                tool_results = []
                for tool_name, params_str in tool_matches:
                    if tool_name in self.tools:
                        try:
                            # 解析参数
                            params = {}
                            param_pattern = r'(\w+)="([^"]*)"'
                            param_matches = re.findall(param_pattern, params_str)
                            for key, value in param_matches:
                                params[key] = value

                            # 执行工具
                            tool_result = await self.tools[tool_name].execute(**params)
                            tool_results.append(f"[{tool_name}]: {tool_result}")
                        except Exception as e:
                            tool_results.append(f"[{tool_name} Error]: {str(e)}")

                # 如果有工具结果，进行第二轮分析
                if tool_results:
                    follow_up_messages = messages + [
                        {
                            "role": "assistant",
                            "content": content
                        },
                        {
                            "role": "user",
                            "content": f"工具返回结果:\n{chr(10).join(tool_results)}\n\n请基于这些数据给出最终分析结论。"
                        }
                    ]
                    llm_response = await self._call_llm(follow_up_messages)
                    
                    # 安全处理第二轮响应
                    if isinstance(llm_response, str):
                        content = llm_response
                    elif isinstance(llm_response, dict) and "choices" in llm_response:
                        content = llm_response["choices"][0]["message"].get("content", "")
                    else:
                        content = str(llm_response)

            # 返回结构化结果
            return {
                "agent": self.name,
                "analysis": content,
                "score": self._extract_score(content),
                "recommendation": self._extract_recommendation(content),
                "raw_output": content
            }

        except Exception as e:
            print(f"[Agent:{self.name}] analyze() failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "agent": self.name,
                "error": str(e),
                "analysis": f"分析失败: {str(e)}"
            }

    def _extract_score(self, content: str) -> float:
        """从分析内容中提取评分"""
        import re
        # 尝试匹配 "评分: 8/10" 或 "得分: 8分" 等格式
        score_patterns = [
            r'评分[:：]\s*(\d+\.?\d*)',
            r'得分[:：]\s*(\d+\.?\d*)',
            r'分数[:：]\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)/10',
            r'(\d+\.?\d*)分'
        ]
        for pattern in score_patterns:
            match = re.search(pattern, content)
            if match:
                score = float(match.group(1))
                return min(score / 10.0 if score > 10 else score, 1.0)
        return 0.5  # 默认中等评分

    def _extract_recommendation(self, content: str) -> str:
        """从分析内容中提取建议"""
        content_lower = content.lower()
        if "建议投资" in content_lower or "推荐买入" in content_lower:
            return "BUY"
        elif "建议观察" in content_lower or "继续关注" in content_lower:
            return "HOLD"
        elif "不建议" in content_lower or "建议放弃" in content_lower:
            return "PASS"
        else:
            return "FURTHER_DD"
