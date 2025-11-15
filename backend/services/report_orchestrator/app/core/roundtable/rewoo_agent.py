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
from typing import List, Dict, Any, Optional
from .agent import Agent
from .tool import Tool
import httpx


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

        # 构建规划Prompt
        planning_prompt = self._create_planning_prompt()

        messages = [
            {"role": "system", "content": planning_prompt},
            {"role": "user", "content": self._format_planning_query(query, context)}
        ]

        # 调用LLM生成计划
        try:
            response = await self._call_llm(
                messages,
                temperature=self.planning_temperature
            )

            # 解析计划
            plan = self._parse_plan(response)

            print(f"[{self.name}] Generated plan with {len(plan)} steps")
            for i, step in enumerate(plan, 1):
                print(f"  Step {i}: {step.get('tool', 'unknown')}({step.get('params', {})})")

            return plan

        except Exception as e:
            print(f"[{self.name}] Planning failed: {e}")
            return []

    async def _execute_phase(
        self,
        plan: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        阶段2: 执行

        并行执行所有工具调用
        """
        print(f"[{self.name}] Phase 2: Executing {len(plan)} tools in parallel...")

        # 创建异步任务列表
        tasks = []
        for step in plan:
            tool_name = step.get("tool")
            tool_params = step.get("params", {})

            # 查找工具
            tool = self.tools.get(tool_name)
            if tool:
                task = tool.execute(**tool_params)
                tasks.append(task)
            else:
                # 工具不存在，添加错误结果
                error_result = {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                    "summary": f"工具'{tool_name}'未找到"
                }
                tasks.append(asyncio.coroutine(lambda e=error_result: e)())

        # 并行执行所有任务
        observations = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_observations = []
        for i, obs in enumerate(observations):
            if isinstance(obs, Exception):
                processed_observations.append({
                    "success": False,
                    "error": str(obs),
                    "summary": f"工具执行异常: {str(obs)}"
                })
            else:
                processed_observations.append(obs)

        success_count = sum(1 for o in processed_observations if o.get('success', False))
        print(f"[{self.name}] Execution complete. {success_count}/{len(plan)} successful.")

        return processed_observations

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
        """创建规划阶段的Prompt"""
        tools_desc = self._format_tools_description()

        return f"""你是 {self.name}，需要为分析任务制定工具调用计划。

{self.role_prompt}

## 你的工具:
{tools_desc}

## 规划任务:
给定一个分析任务，你需要:
1. 理解任务目标
2. 确定需要哪些信息
3. 选择合适的工具获取这些信息
4. 按逻辑顺序排列工具调用

## 输出格式 (JSON数组):
```json
[
  {{
    "step": 1,
    "tool": "tool_name",
    "params": {{"param1": "value1", "param2": "value2"}},
    "purpose": "为什么需要这个工具调用"
  }},
  {{
    "step": 2,
    "tool": "another_tool",
    "params": {{"query": "search query"}},
    "purpose": "获取行业数据"
  }}
]
```

## 重要规则:
1. **只输出JSON数组，不要其他文字**
2. **tool名称必须完全匹配**可用工具列表
3. **params必须符合工具要求**
4. **合理规划步骤数量**(通常3-6步即可)
5. **步骤之间可以并行执行**，因此顺序不是很重要

如果无需使用工具，返回空数组 `[]`
"""

    def _create_solving_prompt(self) -> str:
        """创建综合阶段的Prompt"""
        return f"""你是 {self.name}，需要基于工具调用结果生成最终分析。

{self.role_prompt}

## 综合任务:
你已经执行了一系列工具调用并获得了观察结果。现在需要:
1. 整合所有观察结果
2. 进行深入分析
3. 得出结论和建议
4. 生成结构化的分析报告

## 输出要求:
- **结构化**: 使用Markdown格式，包含标题、列表、数据表格
- **数据支撑**: 引用具体数据来源和数值
- **深度分析**: 不只是数据罗列，要有洞察和判断
- **客观准确**: 明确区分事实和推断
- **中文输出**: 使用简洁专业的中文

## 分析框架:
根据你的角色特点，采用相应的分析框架（如财务分析的杜邦分析、市场分析的SWOT等）
"""

    def _format_tools_description(self) -> str:
        """格式化工具描述"""
        if not self.tools:
            return "无可用工具"

        descriptions = []
        for tool in self.tools.values():
            schema = tool.to_schema()
            params = schema.get("parameters", {})
            params_desc = json.dumps(params.get("properties", {}), ensure_ascii=False, indent=2)

            descriptions.append(
                f"\n**{schema['name']}**:\n"
                f"  描述: {schema['description']}\n"
                f"  参数: {params_desc}"
            )

        return "\n".join(descriptions)

    def _format_planning_query(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """格式化规划查询"""
        context_str = self._format_context(context)

        return f"""# 分析任务
{query}

# 上下文信息
{context_str}

请为此任务制定工具调用计划（JSON格式）。
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

        # 格式化执行结果
        results_text = ""
        for i, (step, obs) in enumerate(zip(plan, observations), 1):
            tool_name = step.get("tool", "unknown")
            params = step.get("params", {})
            purpose = step.get("purpose", "")

            results_text += f"\n## Step {i}: {tool_name}\n"
            results_text += f"**目的**: {purpose}\n"
            results_text += f"**参数**: {json.dumps(params, ensure_ascii=False)}\n"

            if obs.get("success"):
                results_text += f"**结果**: {obs.get('summary', 'N/A')}\n"
            else:
                results_text += f"**错误**: {obs.get('error', 'Unknown error')}\n"

        return f"""# 原始任务
{query}

# 上下文信息
{context_str}

# 执行计划与结果
{results_text}

请基于以上所有信息进行综合分析，生成结构化报告。
"""

    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        if not context:
            return "无"

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
        """解析LLM生成的计划"""
        # 提取JSON (可能被包裹在```json ```中)
        json_str = llm_response.strip()

        # 移除markdown代码块标记
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]

        # 尝试解析JSON
        try:
            plan = json.loads(json_str.strip())

            if isinstance(plan, list):
                return plan
            else:
                print(f"[{self.name}] Plan is not a list: {type(plan)}")
                return []

        except json.JSONDecodeError as e:
            print(f"[{self.name}] Failed to parse plan JSON: {e}")
            print(f"[{self.name}] Raw response: {llm_response[:200]}...")
            return []

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None
    ) -> str:
        """调用LLM"""
        if temperature is None:
            temperature = self.temperature

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                result = response.json()

                # 提取LLM回复
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content

        except Exception as e:
            print(f"[{self.name}] LLM call failed: {e}")
            raise

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
