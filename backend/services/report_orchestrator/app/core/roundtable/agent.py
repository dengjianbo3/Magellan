"""
Agent: The fundamental actor in the multi-agent system
"""
import os
import time
from typing import List, Dict, Any, Optional
from .message import Message, MessageType
from .tool import Tool
from .message_bus import MessageBus
import httpx
import json
from ..config_timeouts import HTTP_CLIENT_TIMEOUT
from ..metrics import record_llm_context_usage, record_tool_call
from ..model_policy import resolve_model_for_role

AGENT_MAX_SYSTEM_PROMPT_CHARS = max(1024, int(os.getenv("AGENT_MAX_SYSTEM_PROMPT_CHARS", "6000")))
AGENT_MAX_HISTORY_MESSAGE_CHARS = max(512, int(os.getenv("AGENT_MAX_HISTORY_MESSAGE_CHARS", "2000")))
AGENT_MAX_PROMPT_TOTAL_CHARS = max(4096, int(os.getenv("AGENT_MAX_PROMPT_TOTAL_CHARS", "50000")))
AGENT_EVIDENCE_MAX_ITEMS = max(1, int(os.getenv("AGENT_EVIDENCE_MAX_ITEMS", "24")))


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
        # Raw execution evidence chain for current turn.
        self._latest_tool_trace: List[Dict[str, Any]] = []

    def _resolve_request_model(self) -> Optional[str]:
        """
        Resolve model override for llm_gateway.
        Returns None to use gateway default tier.
        """
        configured = str(self.model or "").strip()
        lowered = configured.lower()
        if lowered in {"pro", "flash"}:
            return lowered
        if configured.startswith("gemini-"):
            return configured
        is_leader = str(self.id).lower() == "leader" or str(self.name).lower() == "leader"
        return resolve_model_for_role("leader_chat" if is_leader else "specialist_chat")

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
        self._latest_tool_trace = []

        # 4. Build LLM prompt
        prompt_messages = self._build_llm_prompt()

        # 5. Call LLM for reasoning
        llm_response = await self._call_llm(prompt_messages)

        # 6. Parse LLM response
        outgoing_messages = await self._parse_llm_response(llm_response)

        # 7. Update status: idle
        self.status = "idle"

        return outgoing_messages

    @staticmethod
    def _extract_urls(text: str, limit: int = 10) -> List[str]:
        import re
        if not text:
            return []
        hits = re.findall(r"https?://[^\s<>\]\)\"']+", str(text))
        out: List[str] = []
        for raw in hits:
            url = str(raw).rstrip(".,;:!?)")
            if url and url not in out:
                out.append(url)
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _extract_numeric_snippets(text: str, limit: int = 10) -> List[str]:
        import re
        if not text:
            return []
        pattern = re.compile(r"(?:[$€¥£]|USD|CNY|RMB|HKD|BTC|ETH)?\s*[+-]?\d[\d,]*(?:\.\d+)?\s*(?:%|bp|bps|x|倍|万|亿|trillion|billion|million|k|m|bn)?", re.IGNORECASE)
        out: List[str] = []
        for line in str(text).splitlines():
            compact = " ".join(line.strip().split())
            if not compact:
                continue
            if not pattern.search(compact):
                continue
            out.append(compact[:220])
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _safe_preview(value: Any, max_chars: int = 1800) -> str:
        import json
        try:
            if isinstance(value, (dict, list)):
                text = json.dumps(value, ensure_ascii=False, default=str)
            else:
                text = str(value)
        except Exception:
            text = str(value)
        return text[:max_chars]

    def _append_tool_trace(
        self,
        *,
        tool_name: str,
        params: Dict[str, Any],
        status: str,
        duration_ms: int,
        output: Any = None,
        error: str = "",
    ) -> None:
        preview = self._safe_preview(output if output is not None else error, max_chars=1800)
        entry = {
            "kind": "tool_call",
            "tool": str(tool_name or ""),
            "status": str(status or "unknown"),
            "params": params if isinstance(params, dict) else {},
            "duration_ms": int(max(0, duration_ms)),
            "output_preview": preview,
            "sources": self._extract_urls(preview, limit=8),
            "numeric_outputs": self._extract_numeric_snippets(preview, limit=8),
            "error": str(error or ""),
            "timestamp": time.time(),
        }
        self._latest_tool_trace.append(entry)
        if len(self._latest_tool_trace) > AGENT_EVIDENCE_MAX_ITEMS:
            self._latest_tool_trace = self._latest_tool_trace[-AGENT_EVIDENCE_MAX_ITEMS:]

    def get_last_evidence_chain(self, limit: int = AGENT_EVIDENCE_MAX_ITEMS) -> List[Dict[str, Any]]:
        if not self._latest_tool_trace:
            return []
        safe_limit = max(1, int(limit or AGENT_EVIDENCE_MAX_ITEMS))
        return [dict(item) for item in self._latest_tool_trace[-safe_limit:]]

    def _build_llm_prompt(self) -> List[Dict[str, str]]:
        """
        Build prompt messages to send to LLM

        Returns:
            List of messages in OpenAI format
        """
        messages = []
        total_chars = 0

        # System prompt (defines role)
        system_prompt = self._truncate_text(
            self._get_system_prompt(),
            AGENT_MAX_SYSTEM_PROMPT_CHARS,
        )
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        total_chars += len(system_prompt)

        # Conversation history:
        # keep the most recent context while preventing payload oversize (400 in llm_gateway).
        history_candidates: List[Dict[str, str]] = []
        for msg in self.message_history[-30:]:
            role = "assistant" if msg.sender == self.name else "user"
            content = self._truncate_text(
                f"[{msg.sender} → {msg.recipient}] {msg.content}",
                AGENT_MAX_HISTORY_MESSAGE_CHARS,
            )
            history_candidates.append({
                "role": role,
                "content": content
            })

        selected_reversed: List[Dict[str, str]] = []
        for item in reversed(history_candidates):
            item_len = len(item["content"])
            if total_chars + item_len > AGENT_MAX_PROMPT_TOTAL_CHARS:
                continue
            selected_reversed.append(item)
            total_chars += item_len

        messages.extend(reversed(selected_reversed))
        return messages

    @staticmethod
    def _truncate_text(text: str, max_chars: int) -> str:
        if text is None:
            return ""
        if len(text) <= max_chars:
            return text
        suffix = "\n...[truncated]"
        keep = max(0, max_chars - len(suffix))
        return text[:keep] + suffix

    def _get_system_prompt(self) -> str:
        """
        Get complete system prompt

        Returns:
            System prompt string
        """
        # CRITICAL: Inject current timestamp to prevent searching outdated information
        from datetime import datetime
        current_time = datetime.now()
        time_context = f"""## ⏰ CURRENT TIME (IMPORTANT!)
**Current Date/Time**: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8, Beijing Time)
**Current Date**: {current_time.strftime('%B %d, %Y')}

> ⚠️ **TIME-AWARE ANALYSIS REQUIRED**: When searching for information or analyzing data, 
> you MUST focus on the MOST RECENT information available. Always specify time ranges 
> in your searches (e.g., "last 24 hours", "today", "this week").
> Do NOT rely on outdated information. Current market conditions change rapidly.

"""
        
        base_prompt = f"""{time_context}You are {self.name}, a member of an investment analysis expert team.

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

### Time-Sensitive Search Guidelines (CRITICAL!):
⚠️ **ALWAYS specify time ranges** when searching for recent information:
- "Search for Bitcoin news from the last 24 hours"
- "Find market analysis from this week"  
- "Look up today's trading data"
- "Get the most recent earnings reports"

**BAD examples (avoid these)**:
- ❌ "Search for Bitcoin news" (no time range - may get outdated results)
- ❌ "Find market analysis" (too vague)

**GOOD examples (use these)**:
- ✅ "Search for Bitcoin news from the past 24 hours"
- ✅ "Find market analysis published today or yesterday"

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
- **ALWAYS verify information is current and recent before using it**
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
        # Check if tools are available
        has_tools = len(self.tools) > 0

        if has_tools:
            return await self._call_llm_with_tools(messages, max_retries)
        else:
            return await self._call_llm_without_tools(messages, max_retries)

    async def _call_llm_with_tools(self, messages: List[Dict[str, str]], max_retries: int) -> Dict[str, Any]:
        """Call LLM with tool calling support."""
        import asyncio

        tools_schema = self.get_tools_schema()
        request_data = {
            "messages": messages,
            "tools": tools_schema,
            "tool_choice": "auto",
            "temperature": self.temperature
        }
        request_model = self._resolve_request_model()
        if request_model:
            request_data["model"] = request_model

        print(f"[Agent:{self.name}] Using Tool Calling with {len(tools_schema)} tools")

        return await self._execute_llm_request(
            f"{self.llm_gateway_url}/v1/chat/completions",
            request_data,
            max_retries
        )

    async def _call_llm_without_tools(self, messages: List[Dict[str, str]], max_retries: int) -> Dict[str, Any]:
        """Call LLM without tools (backward compatibility)."""
        # Convert to LLM Gateway format
        history = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system" or role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})

        request_data = {
            "history": history,
            "temperature": self.temperature
        }
        request_model = self._resolve_request_model()
        if request_model:
            request_data["model"] = request_model

        result = await self._execute_llm_request(
            f"{self.llm_gateway_url}/chat",
            request_data,
            max_retries
        )

        # Convert response format to OpenAI compatible format
        return self._convert_to_openai_format(result)

    def _convert_to_openai_format(self, result: Any) -> Dict[str, Any]:
        """Convert LLM Gateway response to OpenAI format."""
        if isinstance(result, str):
            content = result
        elif isinstance(result, dict):
            # If already in OpenAI format, return as-is
            if "choices" in result:
                return result
            content = result.get("content", str(result))
        else:
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

    async def _execute_llm_request(self, url: str, request_data: Dict, max_retries: int) -> Dict[str, Any]:
        """Execute LLM request with retry logic."""
        import asyncio

        last_exception = None
        prompt_texts: List[str] = []

        if isinstance(request_data.get("messages"), list):
            for msg in request_data.get("messages", []):
                if isinstance(msg, dict):
                    prompt_texts.append(str(msg.get("content", "")))
        elif isinstance(request_data.get("history"), list):
            for msg in request_data.get("history", []):
                if not isinstance(msg, dict):
                    continue
                parts = msg.get("parts")
                if isinstance(parts, list):
                    prompt_texts.extend([str(part) for part in parts if part is not None])

        resolved_model = str(request_data.get("model") or self._resolve_request_model() or self.model or "default")

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=HTTP_CLIENT_TIMEOUT) as client:
                    response = await client.post(url, json=request_data)
                    response.raise_for_status()
                    result = response.json()
                    print(f"[Agent:{self.name}] LLM response type: {type(result)}")
                    completion_text = ""
                    if isinstance(result, dict):
                        completion_text = str(
                            (
                                result.get("choices", [{}])[0].get("message", {}).get("content")
                                if "choices" in result
                                else result.get("content", "")
                            )
                            or ""
                        )
                    record_llm_context_usage(
                        source="roundtable_agent",
                        model=resolved_model,
                        usage=result.get("usage") if isinstance(result, dict) else None,
                        prompt_texts=prompt_texts,
                        completion_text=completion_text,
                    )
                    return result

            except httpx.ReadTimeout as e:
                last_exception = e
                print(
                    f"[Agent:{self.name}] LLM timeout on attempt "
                    f"{attempt + 1}/{max_retries} (timeout={HTTP_CLIENT_TIMEOUT}s)"
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"[Agent:{self.name}] Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                continue

            except httpx.HTTPStatusError as e:
                last_exception = e
                response_preview = ""
                try:
                    response_preview = (e.response.text or "")[:500]
                except Exception:
                    response_preview = ""
                print(
                    f"[Agent:{self.name}] LLM HTTP error on attempt {attempt + 1}/{max_retries}: "
                    f"status={e.response.status_code} detail={response_preview}"
                )
                # 4xx is usually not retryable for the same payload.
                if 400 <= e.response.status_code < 500:
                    break
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                continue

            except Exception as e:
                last_exception = e
                print(f"[Agent:{self.name}] LLM call failed on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                continue

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
                return await self._handle_native_tool_calls(message["tool_calls"])

            # Extract text content
            content = message.get("content", "")

            # Backward compatibility: detect custom format tool calls
            content = await self._handle_legacy_tool_calls(content)

            if content:
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

    async def _handle_native_tool_calls(self, tool_calls: List[Dict]) -> List[Message]:
        """Handle native OpenAI format tool calls."""
        import json

        messages_to_send = []
        self.status = "tool_using"
        tool_results = []

        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args_str = tool_call["function"]["arguments"]

            if tool_name in self.tools:
                print(f"[Agent:{self.name}] Native Tool Calling: {tool_name}")
                result = await self._execute_single_tool(tool_name, tool_args_str)
                tool_results.append(result)
            else:
                print(f"[Agent:{self.name}] Unknown tool: {tool_name}")

        if tool_results:
            combined_result = "".join(tool_results)
            messages_to_send.append(Message(
                agent_name=self.name,
                content=combined_result,
                message_type=MessageType.INFORMATION
            ))

        self.status = "idle"
        return messages_to_send

    async def _execute_single_tool(self, tool_name: str, tool_args: Any) -> str:
        """Execute a single tool and return formatted result."""
        import json

        started_at = time.perf_counter()
        try:
            # Parse JSON arguments if string
            if isinstance(tool_args, str):
                tool_args = json.loads(tool_args)

            print(f"[Agent:{self.name}] Tool arguments: {tool_args}")

            # Execute tool
            tool_result = await self.tools[tool_name].execute(**tool_args)
            print(f"[Agent:{self.name}] Tool {tool_name} result: {tool_result}")
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._append_tool_trace(
                tool_name=tool_name,
                params=tool_args if isinstance(tool_args, dict) else {},
                status="success",
                duration_ms=duration_ms,
                output=tool_result,
            )
            record_tool_call(
                channel="roundtable_agent",
                agent=self.name,
                tool=tool_name,
                status="success",
                duration_seconds=time.perf_counter() - started_at,
            )

            # Format result
            if isinstance(tool_result, dict) and "summary" in tool_result:
                return f"\n[{tool_name} Result]: {tool_result['summary']}"
            else:
                return f"\n[{tool_name} Result]: {str(tool_result)[:500]}"

        except Exception as e:
            print(f"[Agent:{self.name}] Tool execution failed: {e}")
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._append_tool_trace(
                tool_name=tool_name,
                params=tool_args if isinstance(tool_args, dict) else {},
                status="error",
                duration_ms=duration_ms,
                output=None,
                error=str(e),
            )
            record_tool_call(
                channel="roundtable_agent",
                agent=self.name,
                tool=tool_name,
                status="error",
                duration_seconds=time.perf_counter() - started_at,
            )
            return f"\n[{tool_name} Error]: {str(e)}"

    async def _handle_legacy_tool_calls(self, content: str) -> str:
        """Handle legacy [USE_TOOL:] format (deprecated)."""
        import re

        if not self.tools:
            return content

        tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
        tool_matches = re.findall(tool_pattern, content)

        if not tool_matches:
            return content

        print(f"[Agent:{self.name}] ⚠️ DEPRECATED: Legacy [USE_TOOL:] format detected. "
              "This will be removed in future versions. LLM should use native tool_calls.")

        self.status = "tool_using"
        tool_results = []

        for tool_name, params_str in tool_matches:
            if tool_name in self.tools:
                print(f"[Agent:{self.name}] Legacy tool calling: {tool_name}")
                result = await self._execute_legacy_tool(tool_name, params_str)
                tool_results.append(result)

        if tool_results:
            content += "\n\n" + "\n".join(tool_results)

        return content

    async def _execute_legacy_tool(self, tool_name: str, params_str: str) -> str:
        """Execute a legacy format tool call."""
        import re

        started_at = time.perf_counter()
        try:
            # Parse arguments - support double and single quotes
            params = {}
            param_pattern_double = r'(\w+)="([^"]*)"'
            param_matches = re.findall(param_pattern_double, params_str)

            if not param_matches:
                param_pattern_single = r"(\w+)='([^']*)'"
                param_matches = re.findall(param_pattern_single, params_str)

            for key, value in param_matches:
                params[key] = value

            # Execute tool
            tool_result = await self.tools[tool_name].execute(**params)
            print(f"[Agent:{self.name}] Tool {tool_name} result: {tool_result}")
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._append_tool_trace(
                tool_name=tool_name,
                params=params,
                status="success",
                duration_ms=duration_ms,
                output=tool_result,
            )
            record_tool_call(
                channel="roundtable_agent_legacy",
                agent=self.name,
                tool=tool_name,
                status="success",
                duration_seconds=time.perf_counter() - started_at,
            )

            # Format result
            if isinstance(tool_result, dict) and "summary" in tool_result:
                return f"[{tool_name} Result]: {tool_result['summary']}"
            else:
                return f"[{tool_name} Result]: {str(tool_result)[:500]}"

        except Exception as tool_error:
            print(f"[Agent:{self.name}] Tool {tool_name} error: {tool_error}")
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            self._append_tool_trace(
                tool_name=tool_name,
                params=params if isinstance(params, dict) else {},
                status="error",
                duration_ms=duration_ms,
                output=None,
                error=str(tool_error),
            )
            record_tool_call(
                channel="roundtable_agent_legacy",
                agent=self.name,
                tool=tool_name,
                status="error",
                duration_seconds=time.perf_counter() - started_at,
            )
            return f"[{tool_name} Error]: {str(tool_error)}"

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

        # Build analysis prompt
        analysis_prompt = self._build_analysis_prompt(target, context)

        # Create messages for LLM
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": analysis_prompt}
        ]

        try:
            # Call LLM for analysis
            llm_response = await self._call_llm(messages)
            content = self._extract_llm_content(llm_response)

            # Handle tool calls if present
            content = await self._process_analyze_tool_calls(content, messages)

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

    def _build_analysis_prompt(self, target: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build analysis prompt based on available data."""
        bp_parser_result = context.get('bp_parser_result', {})
        bp_data = bp_parser_result.get('bp_data', {}) if bp_parser_result else {}

        if bp_data:
            return self._build_bp_centric_prompt(target, bp_data)
        else:
            return self._build_standard_prompt(target)

    def _build_bp_centric_prompt(self, target: Dict[str, Any], bp_data: Dict) -> str:
        """Build BP-centric analysis prompt."""
        return f"""## 商业计划书 (BP) 核心分析

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

    def _build_standard_prompt(self, target: Dict[str, Any]) -> str:
        """Build standard analysis prompt without BP data."""
        return f"""Please analyze the following investment target:

{json.dumps(target, ensure_ascii=False, indent=2)}

Please provide analysis from your professional perspective, including:
1. Key findings
2. Risk factors
3. Strengths analysis
4. Score (1-10)
5. Investment recommendation

Please use tools to obtain necessary data to support your analysis."""

    def _extract_llm_content(self, llm_response: Any) -> str:
        """Extract content from LLM response with type handling."""
        print(f"[Agent:{self.name}] 🔍 DEBUG: llm_response type = {type(llm_response)}")

        if isinstance(llm_response, str):
            print(f"[Agent:{self.name}] ✅ Response is string, using directly")
            return llm_response
        elif isinstance(llm_response, dict) and "choices" in llm_response:
            print(f"[Agent:{self.name}] ✅ Response is dict with 'choices', extracting content")
            return llm_response["choices"][0]["message"].get("content", "")
        else:
            print(f"[Agent:{self.name}] ⚠️ WARNING: Unexpected llm_response type: {type(llm_response)}")
            return str(llm_response)

    async def _process_analyze_tool_calls(self, content: str, messages: List[Dict]) -> str:
        """Process tool calls in analyze() and return updated content."""
        import re

        if not self.tools:
            return content

        tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
        tool_matches = re.findall(tool_pattern, content)

        if not tool_matches:
            return content

        tool_results = []
        for tool_name, params_str in tool_matches:
            if tool_name in self.tools:
                result = await self._execute_legacy_tool(tool_name, params_str)
                tool_results.append(f"[{tool_name}]: {result}")

        # If there are tool results, perform second round analysis
        if tool_results:
            follow_up_messages = messages + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Tool results:\n{chr(10).join(tool_results)}\n\nPlease provide final analysis conclusion based on this data."}
            ]
            llm_response = await self._call_llm(follow_up_messages)
            content = self._extract_llm_content(llm_response)

        return content

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
