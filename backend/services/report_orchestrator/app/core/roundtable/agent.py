"""
Agent: The fundamental actor in the multi-agent system
"""
from typing import List, Dict, Any, Optional
from .message import Message, MessageType
from .tool import Tool
from .message_bus import MessageBus
import httpx
import json


class Agent:
    """
    Agent Abstract Base Class

    Represents an autonomous entity in the system, responsible for:
    - Processing received messages
    - Using tools to gather information
    - Interacting with LLM for reasoning
    - Generating and sending new messages
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
        Initialize Agent

        Args:
            name: Agent's display name
            role_prompt: System prompt defining Agent's personality, expertise, and goals
            llm_gateway_url: LLM gateway service URL
            model: Model name to use
            temperature: Generation temperature parameter
            id: Agent's unique identifier (optional, defaults to name)
            role: Agent's role description
            personality: Agent's personality description
            system_prompt: System prompt (interchangeable with role_prompt)
            expertise: List of Agent's expertise areas
            avatar: Agent's avatar icon
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

        # Tool registry
        self.tools: Dict[str, Tool] = {}

        # Message history (Agent's private memory)
        self.message_history: List[Message] = []

        # MessageBus reference (set by Meeting)
        self.message_bus: Optional[MessageBus] = None

        # AgentEventBus reference (set by Meeting for real-time progress)
        self.event_bus = None

        # Agent current state
        self.status = "idle"  # idle, thinking, tool_using, speaking

    def register_tool(self, tool: Tool):
        """
        Register a tool to Agent's toolbelt

        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool
        print(f"[Agent:{self.name}] Tool registered: {tool.name}")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Get schema of all tools (for LLM function calling)

        Returns:
            List of tool schemas
        """
        return [tool.to_schema() for tool in self.tools.values()]

    async def think_and_act(self) -> List[Message]:
        """
        Agent's main loop: process messages, make decisions, generate responses

        Returns:
            List of messages to send
        """
        if not self.message_bus:
            raise RuntimeError(f"Agent {self.name} not connected to MessageBus")

        # 1. Get pending messages
        new_messages = self.message_bus.get_messages(self.name)

        if not new_messages:
            return []

        # 2. Update message history
        self.message_history.extend(new_messages)

        # 3. Update status: thinking
        self.status = "thinking"

        # 4. Build LLM prompt
        prompt_messages = self._build_llm_prompt()

        # 5. Call LLM for reasoning
        llm_response = await self._call_llm(prompt_messages)

        # 6. Parse LLM response
        outgoing_messages = await self._parse_llm_response(llm_response)

        # 7. Update status: idle
        self.status = "idle"

        return outgoing_messages

    def _build_llm_prompt(self) -> List[Dict[str, str]]:
        """
        Build prompt messages to send to LLM

        Returns:
            List of messages in OpenAI format
        """
        messages = []

        # System prompt (defines role)
        messages.append({
            "role": "system",
            "content": self._get_system_prompt()
        })

        # Conversation history - keep more context to avoid losing key info
        for msg in self.message_history[-20:]:  # Keep last 20 messages
            # Determine role based on message sender
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
        Get complete system prompt

        Returns:
            System prompt string
        """
        base_prompt = f"""You are {self.name}, a member of an investment analysis expert team.

{self.role_prompt}

## How You Work:
1. **Carefully read** all received messages and discussion history
2. **Analyze problems** from your professional perspective
3. **Use tools** if you need data support, use your professional tools
4. **Express opinions**:
   - You can agree or disagree with other experts' views
   - You can ask questions to specific experts
   - You can request private chat with certain experts
   - You can share your thought process

## Message Format Guidelines:
- **Broadcast**: Send to "ALL", visible to all experts
- **Question**: Use @ExpertName to ask a specific expert
- **Private chat**: Explicitly state "private message to XXX" or "discuss privately with XXX"
- **Stance**: You can say "I agree with XXX's view" or "I disagree with XXX's opinion"

## Your Available Tools:
"""
        # Add tool descriptions
        if self.tools:
            for tool_name, tool in self.tools.items():
                base_prompt += f"\n- **{tool_name}**: {tool.description}"
            base_prompt += """

## How to Use Tools:
You have access to the tools listed above. When you need information, simply indicate your intent to use a tool and the system will automatically execute it for you via function calling.

### Tool Usage Guidelines:
- **Clearly state** when you need to search for information or query data
- **Be specific** about what you're looking for (e.g., "I need to search for Bitcoin's current market sentiment")
- The system will automatically invoke the appropriate tool based on your request

### Time-Sensitive Search Guidelines (Important!):
For questions requiring latest information, specify the time range needed:
- "Search for Bitcoin news from the last 24 hours"
- "Find market analysis from this week"  
- "Look up recent earnings reports from the past month"

After tool execution, you will receive results to continue the discussion.
"""
        else:
            base_prompt += "\n(No tools currently available)"

        base_prompt += """

## Important Reminders:
- Maintain a professional but natural communication style
- Provide valuable insights from your professional perspective
- Don't repeat points already made by other experts, unless you have a new angle
- If you need data to support your views, proactively use available tools
- If uncertain, honestly express it and seek more information
- Remember this is a collaborative discussion, the goal is to reach the best investment decision
"""
        return base_prompt

    async def _call_llm(self, messages: List[Dict[str, str]], max_retries: int = 3) -> Dict[str, Any]:
        """
        Call LLM gateway for reasoning (with retry mechanism, supports Tool Calling)

        Args:
            messages: List of messages in OpenAI format
            max_retries: Maximum number of retries

        Returns:
            LLM response
        """
        import asyncio

        last_exception = None

        # Check if tools are available
        has_tools = len(self.tools) > 0

        # If tools available, use new Tool Calling endpoint
        if has_tools:
            # Use OpenAI compatible /v1/chat/completions endpoint
            tools_schema = self.get_tools_schema()

            request_data = {
                "messages": messages,  # Pass OpenAI format messages directly
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

            # All retries failed
            print(f"[Agent:{self.name}] All {max_retries} LLM call attempts failed")
            raise last_exception

        else:
            # No tools, use old /chat endpoint (backward compatibility)
            # Convert to LLM Gateway format
            # LLM Gateway expects: {"history": [{"role": "user", "parts": ["text"]}]}
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
                "temperature": self.temperature  # Pass temperature parameter
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

                        # Debug: print response type and content
                        print(f"[Agent:{self.name}] LLM response type: {type(result)}")

                        # Convert response format to be compatible with OpenAI format parsing
                        # LLM Gateway returns: {"content": "text"}
                        # Convert to: {"choices": [{"message": {"content": "text"}}]}

                        # Handle two possible response formats
                        if isinstance(result, str):
                            # If result is string, use directly
                            content = result
                        elif isinstance(result, dict):
                            # If dict, extract content field
                            content = result.get("content", str(result))
                        else:
                            # Other types, convert to string
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
                        # Exponential backoff: 2s, 4s, 8s...
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

            # All retries failed
            print(f"[Agent:{self.name}] All {max_retries} LLM call attempts failed")
            raise last_exception

    async def _parse_llm_response(self, llm_response: Dict[str, Any]) -> List[Message]:
        """
        Parse LLM response and generate messages (supports native Tool Calling)

        Args:
            llm_response: LLM's raw response

        Returns:
            List of messages to send
        """
        messages_to_send = []

        try:
            choice = llm_response["choices"][0]
            message = choice["message"]

            # Check if there are native tool_calls (OpenAI format)
            if message.get("tool_calls") and self.tools:
                # Native Tool Calling
                self.status = "tool_using"
                tool_results = []

                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    if tool_name in self.tools:
                        print(f"[Agent:{self.name}] Native Tool Calling: {tool_name}")

                        try:
                            # Parse JSON arguments
                            import json
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str

                            print(f"[Agent:{self.name}] Tool arguments: {tool_args}")

                            # Execute tool
                            tool_result = await self.tools[tool_name].execute(**tool_args)
                            print(f"[Agent:{self.name}] Tool {tool_name} result: {tool_result}")

                            # Collect tool results
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name} Result]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name} Result]: {str(tool_result)[:500]}")

                        except Exception as e:
                            print(f"[Agent:{self.name}] Tool execution failed: {e}")
                            tool_results.append(f"\n[{tool_name} Error]: {str(e)}")
                    else:
                        print(f"[Agent:{self.name}] Unknown tool: {tool_name}")

                # Return tool results as message
                if tool_results:
                    combined_result = "".join(tool_results)
                    messages_to_send.append(Message(
                        agent_name=self.name,
                        content=combined_result,
                        message_type=MessageType.INFORMATION
                    ))

                self.status = "idle"
                return messages_to_send

            # Extract text content
            content = message.get("content", "")

            # Backward compatibility: detect custom format tool calls [USE_TOOL: tool_name(params)]
            import re
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content)

            if tool_matches and self.tools:
                # Tool call detected (DEPRECATED backward compatibility mode)
                print(f"[Agent:{self.name}] ⚠️ DEPRECATED: Legacy [USE_TOOL:] format detected. "
                      "This will be removed in future versions. LLM should use native tool_calls.")
                self.status = "tool_using"
                tool_results = []

                for tool_name, params_str in tool_matches:
                    if tool_name in self.tools:
                        print(f"[Agent:{self.name}] Legacy tool calling: {tool_name}")

                        # Parse arguments
                        try:
                            # Support double and single quotes: key="value" or key='value'
                            params = {}
                            # Try double quotes first
                            param_pattern_double = r'(\w+)="([^"]*)"'
                            param_matches = re.findall(param_pattern_double, params_str)
                            # Then try single quotes
                            if not param_matches:
                                param_pattern_single = r"(\w+)='([^']*)'"
                                param_matches = re.findall(param_pattern_single, params_str)

                            for key, value in param_matches:
                                params[key] = value

                            # Execute tool
                            tool_result = await self.tools[tool_name].execute(**params)
                            print(f"[Agent:{self.name}] Tool {tool_name} result: {tool_result}")

                            # Collect tool results
                            if isinstance(tool_result, dict) and "summary" in tool_result:
                                tool_results.append(f"\n[{tool_name} Result]: {tool_result['summary']}")
                            else:
                                tool_results.append(f"\n[{tool_name} Result]: {str(tool_result)[:500]}")

                        except Exception as tool_error:
                            print(f"[Agent:{self.name}] Tool {tool_name} error: {tool_error}")
                            tool_results.append(f"\n[{tool_name} Error]: {str(tool_error)}")

                # If there are tool results, add them to content
                if tool_results:
                    content += "\n\n" + "\n".join(tool_results)

            if content:
                # Analyze message type and target recipient
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
        Analyze message content to determine message type and recipient

        Args:
            content: Message content

        Returns:
            (message_type, recipient_name)
        """
        content_lower = content.lower()

        # Detect private message intent (English only)
        if "private" in content_lower or "privately" in content_lower:
            # Try to extract target Agent
            for agent_name in self.message_bus.registered_agents:
                if agent_name.lower() in content_lower and agent_name != self.name:
                    return (MessageType.PRIVATE, agent_name)
            return (MessageType.PRIVATE, "ALL")

        # Detect question intent
        if "@" in content or "question" in content_lower or "ask" in content_lower:
            # Try to extract target Agent
            for agent_name in self.message_bus.registered_agents:
                if agent_name in content and agent_name != self.name:
                    return (MessageType.QUESTION, agent_name)
            return (MessageType.QUESTION, "ALL")

        # Detect agreement/disagreement
        if "agree" in content_lower or "concur" in content_lower:
            return (MessageType.AGREEMENT, "ALL")
        if "disagree" in content_lower or "oppose" in content_lower:
            return (MessageType.DISAGREEMENT, "ALL")

        # Default to broadcast message
        return (MessageType.BROADCAST, "ALL")

    def get_conversation_context(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get conversation context (for debugging or display)

        Args:
            limit: Maximum number of messages to return

        Returns:
            Message history list
        """
        return [msg.to_dict() for msg in self.message_history[-limit:]]

    async def analyze(self, target: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute analysis independently (compatible with BaseOrchestrator interface)

        This is an adapter method that allows Agent to execute analysis independently
        within BaseOrchestrator's workflow, without needing a complete roundtable meeting.

        Args:
            target: Analysis target data
            context: Context information (optional, may contain bp_parser_result)

        Returns:
            Analysis result dictionary
        """
        context = context or {}
        
        # Check if BP data is available from bp_parser step
        bp_parser_result = context.get('bp_parser_result', {})
        bp_data = bp_parser_result.get('bp_data', {}) if bp_parser_result else {}
        
        # Build analysis prompt based on whether BP data is available
        if bp_data:
            # BP-CENTRIC ANALYSIS: Use BP as the primary data source
            analysis_prompt = f"""## 商业计划书 (BP) 核心分析

**重要**: 以下分析必须以商业计划书内容为核心数据来源。你的任务是验证和扩展 BP 中的信息，而非搜索公司名称获取无关信息。

### 📋 BP 结构化数据:
{json.dumps(bp_data, ensure_ascii=False, indent=2)}

### 🎯 分析目标:
{json.dumps(target, ensure_ascii=False, indent=2)}

### 📌 分析指南:
1. **基于 BP 内容分析**: 专注于 BP 中提到的具体信息（团队、产品、市场、竞品等）
2. **验证 BP 声明**: 使用工具搜索来验证 BP 中的关键声明是否属实
3. **扩展 BP 信息**: 对 BP 提到的行业/竞品/团队成员进行深入研究
4. **识别缺失信息**: 指出 BP 中缺少但投资决策需要的关键信息

### ⚠️ 禁止行为:
- 不要仅基于公司名称进行泛搜索
- 所有搜索必须围绕 BP 中提到的具体内容
- 如找到与 BP 矛盾的信息，需特别标注

请从你的专业角度提供分析，包括:
1. BP 内容关键发现
2. BP 声明验证结果
3. 风险因素
4. 优势分析
5. 评分 (1-10)
6. 投资建议"""
        else:
            # Fallback: Original prompt without BP data
            analysis_prompt = f"""Please analyze the following investment target:

{json.dumps(target, ensure_ascii=False, indent=2)}

Please provide analysis from your professional perspective, including:
1. Key findings
2. Risk factors
3. Strengths analysis
4. Score (1-10)
5. Investment recommendation

Please use tools to obtain necessary data to support your analysis."""

        # Create a virtual analysis message
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

        # Call LLM for analysis
        try:
            llm_response = await self._call_llm(messages)

            # Detailed log: print response type and content
            print(f"[Agent:{self.name}] 🔍 DEBUG: llm_response type = {type(llm_response)}")
            print(f"[Agent:{self.name}] 🔍 DEBUG: llm_response = {str(llm_response)[:200]}")

            # Safely extract content - handle possible type issues
            if isinstance(llm_response, str):
                # If response is string, use directly
                print(f"[Agent:{self.name}] ✅ Response is string, using directly")
                content = llm_response
            elif isinstance(llm_response, dict) and "choices" in llm_response:
                # Standard format
                print(f"[Agent:{self.name}] ✅ Response is dict with 'choices', extracting content")
                choice = llm_response["choices"][0]
                content = choice["message"].get("content", "")
            else:
                # Unknown format, try to convert to string
                print(f"[Agent:{self.name}] ⚠️ WARNING: Unexpected llm_response type: {type(llm_response)}")
                print(f"[Agent:{self.name}] ⚠️ WARNING: Full response: {llm_response}")
                content = str(llm_response)

            # Detect and execute tool calls
            import re
            tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
            tool_matches = re.findall(tool_pattern, content)

            if tool_matches and self.tools:
                tool_results = []
                for tool_name, params_str in tool_matches:
                    if tool_name in self.tools:
                        try:
                            # Parse arguments
                            params = {}
                            param_pattern = r'(\w+)="([^"]*)"'
                            param_matches = re.findall(param_pattern, params_str)
                            for key, value in param_matches:
                                params[key] = value

                            # Execute tool
                            tool_result = await self.tools[tool_name].execute(**params)
                            tool_results.append(f"[{tool_name}]: {tool_result}")
                        except Exception as e:
                            tool_results.append(f"[{tool_name} Error]: {str(e)}")

                # If there are tool results, perform second round analysis
                if tool_results:
                    follow_up_messages = messages + [
                        {
                            "role": "assistant",
                            "content": content
                        },
                        {
                            "role": "user",
                            "content": f"Tool results:\n{chr(10).join(tool_results)}\n\nPlease provide final analysis conclusion based on this data."
                        }
                    ]
                    llm_response = await self._call_llm(follow_up_messages)
                    
                    # Safely handle second round response
                    if isinstance(llm_response, str):
                        content = llm_response
                    elif isinstance(llm_response, dict) and "choices" in llm_response:
                        content = llm_response["choices"][0]["message"].get("content", "")
                    else:
                        content = str(llm_response)

            # Return structured result
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
                "analysis": f"Analysis failed: {str(e)}"
            }

    def _extract_score(self, content: str) -> float:
        """Extract score from analysis content"""
        import re
        # Try to match "Score: 8/10" or "Rating: 8" etc. formats (English only)
        score_patterns = [
            r'[Ss]core[::]\s*(\d+\.?\d*)',  # Score
            r'[Rr]ating[::]\s*(\d+\.?\d*)',  # Rating
            r'(\d+\.?\d*)/10',
            r'(\d+\.?\d*)\s*out of\s*10',  # X out of 10 format
        ]
        for pattern in score_patterns:
            match = re.search(pattern, content)
            if match:
                score = float(match.group(1))
                return min(score / 10.0 if score > 10 else score, 1.0)
        return 0.5  # Default medium score

    def _extract_recommendation(self, content: str) -> str:
        """Extract recommendation from analysis content"""
        content_lower = content.lower()
        # Check for buy recommendation (English only)
        if "recommend buy" in content_lower or "recommend investment" in content_lower:
            return "BUY"
        # Check for hold recommendation
        elif "hold" in content_lower or "watch" in content_lower or "observe" in content_lower:
            return "HOLD"
        # Check for pass recommendation
        elif "not recommend" in content_lower or "pass" in content_lower or "avoid" in content_lower:
            return "PASS"
        else:
            return "FURTHER_DD"
