"""
ReWOO Agent Implementation
Reasoning WithOut Observation - 更高效的Agent架构

ReWOO三阶段执行:
1. Plan: 一次性生成所有工具调用计划
2. Execute: 并行执行所有工具调用
3. Solve: 基于所有结果综合分析

优势:
- 减少LLM调用次数 (vs ReAct的多次Think-Act循环)
- 并行执行工具，提升效率
- 更结构化的推理过程
"""
import asyncio
import json
import re
import logging
from typing import List, Dict, Any
from .agent import Agent
import httpx

# Import timeout configurations
from ..config_timeouts import (
    TOOL_EXECUTION_TIMEOUT,
    HTTP_CLIENT_TIMEOUT
)

# Context Engineering Note:
# Tool result compression was removed - agents need FULL data for current decisions.
# Compression should only apply to HISTORICAL data (MeetingCompactor, AgentMemory)
# not to current tool call results within a decision cycle.

# 配置日志
logger = logging.getLogger(__name__)


class ReWOOAgent(Agent):
    """
    ReWOO架构的Agent

    与传统ReAct不同，ReWOO一次性规划所有步骤，然后并行执行，最后综合分析
    适合需要批量数据获取的任务（如财务分析、市场研究）
    """

    def __init__(
        self,
        name: str,
        role_prompt: str,
        llm_gateway_url: str = "http://llm_gateway:8003",
        model: str = "gpt-4",
        temperature: float = 0.7
    ):
        super().__init__(name, role_prompt, llm_gateway_url, model, temperature)
        self.planning_temperature = 0.3  # 规划阶段使用更低温度
        self.solving_temperature = temperature  # 综合阶段使用正常温度

    async def think_and_act(self) -> List:
        """
        Override base Agent's think_and_act to use ReWOO workflow

        This is called by the Meeting/Roundtable system. Instead of using the base
        Agent's simple tool calling, we use the ReWOO three-phase approach.

        Returns:
            List of Message objects to send
        """
        from .message import Message

        if not self.message_bus:
            raise RuntimeError(f"Agent {self.name} not connected to MessageBus")

        # 1. Get new messages
        new_messages = self.message_bus.get_messages(self.name)

        if not new_messages:
            return []

        # 2. Update message history
        self.message_history.extend(new_messages)

        # 3. Extract query and context from messages
        # Combine all message content as the query
        query_parts = []
        for msg in new_messages:
            query_parts.append(f"[{msg.sender}]: {msg.content}")

        query = "\n\n".join(query_parts)

        # Build context from all conversation history
        context = {
            "conversation_history": [msg.to_dict() for msg in self.message_history[-10:]],
            "available_agents": list(self.message_bus.registered_agents) if self.message_bus else []
        }

        # 4. Run ReWOO analysis
        print(f"[{self.name}] Running ReWOO analysis...")
        try:
            result = await self.analyze_with_rewoo(query, context)

            # 5. Create response message
            if result:
                # Analyze message intent to determine recipient
                message_type, recipient = self._analyze_message_intent(result)

                msg = Message(
                    sender=self.name,
                    recipient=recipient,
                    content=result,
                    message_type=message_type
                )

                self.message_history.append(msg)
                return [msg]
            else:
                print(f"[{self.name}] ReWOO analysis returned no result")
                return []

        except Exception as e:
            print(f"[{self.name}] ReWOO analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def analyze_with_rewoo(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """
        使用ReWOO三阶段进行分析

        Args:
            query: 分析任务
            context: 上下文信息

        Returns:
            分析结果
        """
        print(f"[{self.name}] Starting ReWOO analysis for: {query[:50]}...")

        # Phase 1: Plan
        plan = await self._plan_phase(query, context)

        if not plan:
            print(f"[{self.name}] Planning failed, falling back to direct analysis")
            return await self._fallback_direct_analysis(query, context)

        # Phase 2: Execute (并行)
        observations = await self._execute_phase(plan)

        # Phase 3: Solve
        result = await self._solve_phase(query, context, plan, observations)

        return result

    async def _plan_phase(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        阶段1: 规划

        生成需要执行的工具调用列表
        """
        print(f"[{self.name}] Phase 1: Planning...")

        # Emit planning started event
        if self.event_bus:
            await self.event_bus.publish_thinking(
                agent_name=self.name,
                message="🧠 正在规划分析步骤..."
            )

        # 构建规划Prompt
        planning_prompt = self._create_planning_prompt()

        messages = [
            {"role": "system", "content": planning_prompt},
            {"role": "user", "content": self._format_planning_query(query, context)}
        ]

        # 调用LLM生成计划
        try:
            # Emit log: calling LLM
            if self.event_bus:
                await self.event_bus.publish_log(
                    agent_name=self.name,
                    log_text=f"[Plan] 调用LLM生成分析计划..."
                )

            response = await self._call_llm(
                messages,
                temperature=self.planning_temperature
            )

            # Emit log: LLM response received
            if self.event_bus:
                await self.event_bus.publish_log(
                    agent_name=self.name,
                    log_text=f"[Plan] LLM响应已收到，解析计划中..."
                )

            # 解析计划
            plan = self._parse_plan(response)

            print(f"[{self.name}] Generated plan with {len(plan)} steps")
            
            # Emit plan generated event with step details
            if self.event_bus and plan:
                step_details = [f"{s.get('tool', '?')}" for s in plan]
                await self.event_bus.publish_progress(
                    agent_name=self.name,
                    message=f"📋 生成了 {len(plan)} 个分析步骤: {', '.join(step_details)}",
                    progress=0.2
                )

            for i, step in enumerate(plan, 1):
                step_log = f"  • Step {i}: {step.get('tool', 'unknown')}({step.get('params', {})})"
                print(step_log)
                # Emit each step as log
                if self.event_bus:
                    await self.event_bus.publish_log(
                        agent_name=self.name,
                        log_text=f"[Plan] Step {i}: {step.get('tool')}({step.get('params', {})})"
                    )

            return plan

        except Exception as e:
            print(f"[{self.name}] Planning failed: {e}")
            return []

    async def _execute_phase(
        self,
        plan: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        阶段2: 执行（带超时和错误处理）

        并行执行所有工具调用
        """
        logger.info(f"[{self.name}] Phase 2: Executing {len(plan)} tools in parallel...")

        # Emit execution started event
        if self.event_bus:
            await self.event_bus.publish_progress(
                agent_name=self.name,
                message=f"⚡ 开始并行执行 {len(plan)} 个工具调用...",
                progress=0.3
            )

        # 创建异步任务列表
        tasks = []
        for i, step in enumerate(plan):
            tool_name = step.get("tool")
            tool_params = step.get("params", {})
            purpose = step.get("purpose", "")

            # 查找工具
            tool = self.tools.get(tool_name)
            if not tool:
                # Tool not found, add error result
                logger.warning(f"[{self.name}] Tool '{tool_name}' not found for step {i+1}")
                error_result = {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                    "summary": f"Tool '{tool_name}' not found"
                }
                tasks.append(self._create_completed_future(error_result))
                continue

            # Create task with timeout
            try:
                # Emit log for each tool
                if self.event_bus:
                    params_str = ', '.join([f"{k}={repr(v)[:30]}" for k,v in tool_params.items()])
                    await self.event_bus.publish_log(
                        agent_name=self.name,
                        log_text=f"[Exec] 工具调用: {tool_name}({params_str})"
                    )

                # Use configured tool execution timeout
                task = asyncio.wait_for(
                    tool.execute(**tool_params),
                    timeout=TOOL_EXECUTION_TIMEOUT
                )
                tasks.append(task)
                logger.debug(f"[{self.name}] Step {i+1}: {tool_name}({tool_params}) - {purpose} (timeout: {TOOL_EXECUTION_TIMEOUT}s)")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to create task for {tool_name}: {e}")
                error_result = {
                    "success": False,
                    "error": str(e),
                    "summary": f"Task creation failed: {str(e)}"
                }
                tasks.append(self._create_completed_future(error_result))


        # Execute all tasks in parallel
        observations = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and exceptions
        processed_observations = []
        for i, obs in enumerate(observations):
            if isinstance(obs, asyncio.TimeoutError):
                logger.error(f"[{self.name}] Step {i+1} timed out after {TOOL_EXECUTION_TIMEOUT}s")
                processed_observations.append({
                    "success": False,
                    "error": "Tool execution timeout",
                    "summary": f"Tool execution timeout ({TOOL_EXECUTION_TIMEOUT}s)"
                })
            elif isinstance(obs, Exception):
                logger.error(f"[{self.name}] Step {i+1} failed with exception: {obs}")
                processed_observations.append({
                    "success": False,
                    "error": str(obs),
                    "summary": f"Tool execution error: {str(obs)}"
                })
            elif isinstance(obs, str):
                # Tool returned a string instead of dict - wrap it
                processed_observations.append({
                    "success": True,
                    "summary": obs[:2000] if len(obs) > 2000 else obs,
                    "raw_result": obs
                })
            elif isinstance(obs, dict):
                # Pass through full tool result - agents need complete data for decisions
                # Context Engineering note: compression should only apply to HISTORICAL data
                # (previous meeting transcripts, old reflections), not current tool results
                processed_observations.append(obs)
            else:
                # Unknown type - convert to string
                processed_observations.append({
                    "success": True,
                    "summary": str(obs)[:2000],
                    "raw_result": str(obs)
                })

        # Count successes - handle both dict and other types safely
        success_count = 0
        for o in processed_observations:
            if isinstance(o, dict) and o.get('success', False):
                success_count += 1
        success_rate = success_count / len(plan) if plan else 0

        logger.info(f"[{self.name}] Execution complete: {success_count}/{len(plan)} successful ({success_rate:.1%})")

        # Emit log for execution completion
        if self.event_bus:
            await self.event_bus.publish_log(
                agent_name=self.name,
                log_text=f"[Exec] 执行完成: {success_count}/{len(plan)} 成功 ({success_rate:.1%})"
            )

        # If success rate is too low, log warning
        if success_rate < 0.3 and len(plan) > 0:
            logger.warning(f"[{self.name}] Low success rate ({success_rate:.1%}), analysis quality may be affected")

        return processed_observations

    async def _create_completed_future(self, result: Any):
        """创建一个已完成的future"""
        return result

    async def _solve_phase(
        self,
        query: str,
        context: Dict[str, Any],
        plan: List[Dict[str, Any]],
        observations: List[Dict[str, Any]]
    ) -> str:
        """
        阶段3: 综合

        基于所有观察结果生成最终分析
        """
        print(f"[{self.name}] Phase 3: Solving...")

        # Emit solving started event
        if self.event_bus:
            await self.event_bus.publish_analyzing(
                agent_name=self.name,
                message="📊 综合分析所有数据中...",
                progress=0.8
            )

        # 构建综合Prompt
        solving_prompt = self._create_solving_prompt()

        messages = [
            {"role": "system", "content": solving_prompt},
            {"role": "user", "content": self._format_solving_query(
                query, context, plan, observations
            )}
        ]

        # 调用LLM生成最终分析
        try:
            result = await self._call_llm(
                messages,
                temperature=self.solving_temperature
            )

            print(f"[{self.name}] Analysis complete ({len(result)} chars)")
            return result

        except Exception as e:
            print(f"[{self.name}] Solving failed: {e}")
            return f"分析失败: {str(e)}"

    def _create_planning_prompt(self) -> str:
        """创建规划阶段的Prompt (强化JSON输出)"""
        tools_desc = self._format_tools_description()

        return f"""You are {self.name}, planning tool calls for an analysis task.

{self.role_prompt}

## Available Tools:
{tools_desc}

## Planning Task:
For the given analysis task, you need to:
1. Understand the goal
2. Determine what information is needed
3. Select appropriate tools to gather this information
4. Arrange tool calls in logical order

## OUTPUT FORMAT (CRITICAL - MUST FOLLOW EXACTLY):

You MUST output ONLY a JSON array in this exact format. NO other text, NO explanation, NO markdown formatting.

Valid output examples:

Example 1 (with tools):
[
  {{"step": 1, "tool": "yahoo_finance", "params": {{"symbol": "TSLA", "action": "price"}}, "purpose": "Get current stock price"}},
  {{"step": 2, "tool": "sec_edgar", "params": {{"ticker": "TSLA", "form_type": "10-K"}}, "purpose": "Get annual report"}},
  {{"step": 3, "tool": "tavily_search", "params": {{"query": "Tesla market share 2024"}}, "purpose": "Get market position"}}
]

Example 2 (no tools needed):
[]

## CRITICAL RULES:
1. Output ONLY the JSON array - nothing before, nothing after
2. Tool names MUST exactly match available tools
3. Params MUST match tool requirements
4. Typically plan 3-6 steps
5. Steps can execute in parallel

DO NOT add explanations. DO NOT use markdown code blocks. JUST the raw JSON array.
"""

    def _create_solving_prompt(self) -> str:
        """Create the solving phase prompt"""
        return f"""You are {self.name}, generating the final analysis based on tool execution results.

{self.role_prompt}

## Synthesis Task:
You have executed a series of tool calls and obtained observation results. Now you need to:
1. Integrate all observation results
2. Conduct in-depth analysis
3. Draw conclusions and recommendations
4. Generate a structured analysis report

## Output Requirements:
- **Structured**: Use Markdown format with headings, lists, and data tables
- **Data-Driven**: Reference specific data sources and values
- **In-Depth**: Not just data listing, include insights and judgments
- **Objective**: Clearly distinguish between facts and inferences
- **English Output**: Use concise, professional English
- **Direct Output**: Do not add "TO: ALL", "CC:" or other email format prefixes

## Analysis Framework:
Apply the appropriate analysis framework based on your role (e.g., DuPont analysis for finance, SWOT for market analysis)
"""

    def _format_tools_description(self) -> str:
        """Format tool descriptions"""
        if not self.tools:
            return "No tools available"

        descriptions = []
        for tool in self.tools.values():
            schema = tool.to_schema()
            params = schema.get("parameters", {})
            params_desc = json.dumps(params.get("properties", {}), ensure_ascii=False, indent=2)

            descriptions.append(
                f"\n**{schema['name']}**:\n"
                f"  Description: {schema['description']}\n"
                f"  Parameters: {params_desc}"
            )

        return "\n".join(descriptions)

    def _format_planning_query(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """格式化规划查询"""
        context_str = self._format_context(context)

        return f"""# Analysis Task
{query}

# Context Information
{context_str}

Please create a tool call plan for this task (JSON format).
"""

    def _format_solving_query(
        self,
        query: str,
        context: Dict[str, Any],
        plan: List[Dict[str, Any]],
        observations: List[Dict[str, Any]]
    ) -> str:
        """格式化综合查询"""
        context_str = self._format_context(context)

        # Format execution results
        results_text = ""
        for i, (step, obs) in enumerate(zip(plan, observations), 1):
            tool_name = step.get("tool", "unknown")
            params = step.get("params", {})
            purpose = step.get("purpose", "")

            results_text += f"\n## Step {i}: {tool_name}\n"
            results_text += f"**Purpose**: {purpose}\n"
            results_text += f"**Params**: {json.dumps(params, ensure_ascii=False)}\n"

            # Handle both dict and string observations
            if isinstance(obs, dict):
                if obs.get("success"):
                    results_text += f"**Result**: {obs.get('summary', 'N/A')}\n"
                else:
                    results_text += f"**Error**: {obs.get('error', 'Unknown error')}\n"
            elif isinstance(obs, str):
                # Tool returned raw string
                results_text += f"**Result**: {obs[:2000]}\n"
            else:
                results_text += f"**Result**: {str(obs)[:2000]}\n"

        return f"""# Original Task
{query}

# Context Information
{context_str}

# Execution Plan and Results
{results_text}

Please synthesize all the above information and generate a structured analysis report.
"""

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information"""
        if not context:
            return "None"

        parts = []
        for key, value in context.items():
            # 处理不同类型的值
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                value_str = str(value)

            parts.append(f"- **{key}**: {value_str}")

        return "\n".join(parts)

    def _parse_plan(self, llm_response: str) -> List[Dict[str, Any]]:
        """解析LLM生成的计划（增强版，支持多种格式）"""
        json_str = llm_response.strip()

        # 尝试多种JSON提取模式
        patterns = [
            r'```json\s*(\[.*?\])\s*```',  # ```json [...] ```
            r'```\s*(\[.*?\])\s*```',      # ``` [...] ```
            r'(\[.*\])',                    # 直接找JSON数组
        ]

        for pattern in patterns:
            match = re.search(pattern, json_str, re.DOTALL)
            if match:
                try:
                    plan = json.loads(match.group(1).strip())
                    if isinstance(plan, list):
                        logger.info(f"[{self.name}] Successfully parsed plan with {len(plan)} steps")
                        return plan
                except json.JSONDecodeError:
                    continue

        # 最后尝试直接解析整个响应
        try:
            plan = json.loads(json_str)
            if isinstance(plan, list):
                logger.info(f"[{self.name}] Parsed plan directly: {len(plan)} steps")
                return plan
            else:
                logger.warning(f"[{self.name}] Parsed JSON is not a list: {type(plan)}")
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] Failed to parse plan JSON: {e}")
            logger.error(f"[{self.name}] Response preview: {llm_response[:300]}...")

        # 解析失败，返回空列表（会触发fallback）
        logger.warning(f"[{self.name}] Plan parsing failed, will use fallback")
        return []

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_retries: int = 3
    ) -> str:
        """调用LLM（带重试机制）"""
        if temperature is None:
            temperature = self.temperature

        last_error = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=HTTP_CLIENT_TIMEOUT) as client:
                    # 转换消息格式为LLM Gateway期待的格式
                    # Gemini只支持 "user" 和 "model" role,不支持 "system"
                    history = []
                    for msg in messages:
                        role = msg.get("role", "user")
                        # 将 "system" 转换为 "user" (Gemini不支持system role)
                        if role == "system":
                            role = "user"
                        elif role == "assistant":
                            role = "model"  # Gemini使用 "model" 而非 "assistant"

                        history.append({
                            "role": role,
                            "parts": [msg.get("content", "")]
                        })

                    # Debug: Print what we're sending
                    print(f"[ReWOO:{self.name}] Sending to LLM Gateway: {json.dumps({'history': history}, indent=2)}")

                    response = await client.post(
                        f"{self.llm_gateway_url}/chat",
                        json={
                            "history": history
                        }
                    )
                    response.raise_for_status()
                    result = response.json()

                    # 提取LLM回复 (LLM Gateway返回 {"content": "..."})
                    content = result.get("content", "")

                    if not content:
                        raise ValueError("Empty response from LLM")

                    logger.info(f"[{self.name}] LLM call succeeded on attempt {attempt + 1}")
                    return content

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"[{self.name}] LLM timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避: 1s, 2s, 4s
                continue

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:  # Rate limit
                    logger.warning(f"[{self.name}] Rate limited, retrying... (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)  # 等待5s后重试
                    continue
                elif e.response.status_code >= 500:  # Server error
                    logger.error(f"[{self.name}] Server error {e.response.status_code}, retrying...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"[{self.name}] HTTP error {e.response.status_code}: {e}")
                    raise  # 客户端错误不重试

            except Exception as e:
                last_error = e
                logger.error(f"[{self.name}] LLM call failed on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                continue

        # 所有重试都失败
        logger.error(f"[{self.name}] All {max_retries} LLM call attempts failed")
        raise last_error if last_error else Exception("LLM call failed")

    async def _fallback_direct_analysis(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """回退到直接分析（无工具）"""
        print(f"[{self.name}] Using direct analysis (no tools)")

        context_str = self._format_context(context)

        messages = [
            {"role": "system", "content": self.role_prompt},
            {"role": "user", "content": f"""# 分析任务
{query}

# 上下文信息
{context_str}

请基于现有信息进行分析。
"""}
        ]

        return await self._call_llm(messages, temperature=self.temperature)
