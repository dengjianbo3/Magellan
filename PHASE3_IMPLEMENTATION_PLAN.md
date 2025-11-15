# Phase 3: 详细实施计划
## Magellan AI Investment Analysis Platform - Agent Enhancement Implementation

**创建日期**: 2025-11-16
**状态**: 📋 Planning
**基于**: PHASE3_AGENT_ARCHITECTURE_RESEARCH.md

---

## 📊 执行摘要

本计划基于已完成的MCP服务和Agent架构调研，提供分5个阶段的详细实施路线图。重点是**MVP优先原则**，优先使用免费/稳定的MCP服务，逐步提升Agent分析能力。

**核心目标**:
- ✅ 已完成: Yahoo Finance工具集成
- 🎯 待完成: SEC EDGAR集成、Agent架构升级、Prompt优化
- 📈 预期效果: 上市公司分析准确率 >90%，财务数据获取成功率 >95%

**实施周期**: 预计 3-4 天
**优先级策略**: P0 (必须) → P1 (重要) → P2 (优化)

---

## 🎯 五阶段实施路线图

### 阶段 0: 当前状态盘点 ✅ DONE

#### 已完成的工作
1. ✅ Yahoo Finance工具创建 (`yahoo_finance_tool.py`)
2. ✅ Legal Advisor Agent创建
3. ✅ Tech Specialist Agent启用
4. ✅ Docker容器重建（包含yfinance依赖）
5. ✅ MCP工具分配逻辑更新
6. ✅ 全面调研文档完成

#### 当前Agent配置

**Roundtable Agents (7个)**:
```python
# /backend/services/report_orchestrator/app/core/roundtable/investment_agents.py
def create_all_agents():
    return [
        create_leader(),           # 主持人
        create_market_analyst(),   # 市场分析师 - ✅ Yahoo Finance
        create_financial_expert(), # 财务专家 - ✅ Yahoo Finance
        create_team_evaluator(),   # 团队评估师
        create_risk_assessor(),    # 风险评估师
        create_tech_specialist(),  # 技术专家 - ✅ 新启用
        create_legal_advisor(),    # 法律顾问 - ✅ 新创建
    ]
```

**DD Flow Agents (6个)**:
```
/backend/services/report_orchestrator/app/agents/
├── market_analysis_agent.py  - ⚠️ 需要优化
├── team_analysis_agent.py    - ⚠️ 需要优化
├── risk_agent.py             - ⚠️ 需要优化
├── valuation_agent.py        - ⚠️ 需要优化
├── exit_agent.py
└── preference_match_agent.py
```

---

### 阶段 1: SEC EDGAR集成 (P0 - 最高优先级)

**目标**: 为上市公司分析添加官方财报数据源

#### 1.1 创建SEC EDGAR MCP工具

**新文件**: `/backend/services/report_orchestrator/app/core/roundtable/sec_edgar_tool.py`

```python
"""
SEC EDGAR MCP Tool
获取美国上市公司官方财务披露文件
"""
import httpx
from typing import Any, Dict
from .tool import Tool


class SECEdgarTool(Tool):
    """
    SEC EDGAR API工具

    通过 SEC官方API 获取上市公司财务披露
    支持的文件类型: 10-K, 10-Q, 8-K, DEF 14A
    """

    def __init__(
        self,
        base_url: str = "https://data.sec.gov",
        user_agent: str = "Magellan AI Investment Platform (contact@example.com)"
    ):
        super().__init__(
            name="sec_edgar",
            description="获取美国上市公司的官方SEC财务披露文件，包括年报(10-K)、季报(10-Q)、重大事件(8-K)等。"
        )
        self.base_url = base_url
        self.headers = {
            "User-Agent": user_agent,  # SEC要求提供User-Agent
            "Accept-Encoding": "gzip, deflate"
        }

    async def execute(
        self,
        action: str,
        ticker: str = None,
        cik: str = None,
        form_type: str = "10-K",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行SEC EDGAR查询

        Args:
            action: 操作类型 (search_filings, get_company_facts)
            ticker: 股票代码 (如 AAPL)
            cik: CIK号码 (Central Index Key)
            form_type: 文件类型 (10-K, 10-Q, 8-K, DEF 14A)
            **kwargs: 其他参数

        Returns:
            查询结果
        """
        try:
            if action == "search_filings":
                return await self._search_filings(ticker, cik, form_type, **kwargs)
            elif action == "get_company_facts":
                return await self._get_company_facts(ticker, cik)
            elif action == "get_filing_content":
                filing_url = kwargs.get("filing_url")
                return await self._get_filing_content(filing_url)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "summary": f"不支持的操作: {action}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"SEC EDGAR查询失败: {str(e)}"
            }

    async def _search_filings(
        self,
        ticker: str,
        cik: str,
        form_type: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """搜索公司的财务披露文件"""
        # 如果提供ticker，先转换为CIK
        if ticker and not cik:
            cik = await self._ticker_to_cik(ticker)
            if not cik:
                return {
                    "success": False,
                    "summary": f"无法找到股票代码 {ticker} 对应的CIK"
                }

        # 格式化CIK (10位，前面补0)
        cik_padded = str(cik).zfill(10)

        # 搜索披露文件
        url = f"{self.base_url}/submissions/CIK{cik_padded}.json"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # 提取最近的指定类型文件
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        filing_dates = filings.get("filingDate", [])
        accession_numbers = filings.get("accessionNumber", [])

        # 过滤指定类型
        filtered_filings = []
        for i, form in enumerate(forms):
            if form == form_type and len(filtered_filings) < limit:
                filtered_filings.append({
                    "form_type": form,
                    "filing_date": filing_dates[i],
                    "accession_number": accession_numbers[i],
                    "url": f"{self.base_url}/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_numbers[i]}&xbrl_type=v"
                })

        # 构建摘要
        company_name = data.get("name", ticker or cik)
        summary = f"找到 {company_name} 的 {len(filtered_filings)} 个 {form_type} 文件:\n"
        for filing in filtered_filings:
            summary += f"\n- {filing['filing_date']}: {filing['url']}"

        return {
            "success": True,
            "summary": summary,
            "company_name": company_name,
            "cik": cik,
            "filings": filtered_filings
        }

    async def _get_company_facts(
        self,
        ticker: str,
        cik: str
    ) -> Dict[str, Any]:
        """获取公司的XBRL财务数据"""
        if ticker and not cik:
            cik = await self._ticker_to_cik(ticker)

        cik_padded = str(cik).zfill(10)
        url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik_padded}.json"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # 提取关键财务指标
        facts = data.get("facts", {})
        us_gaap = facts.get("us-gaap", {})

        # 常用指标
        key_metrics = {
            "Revenue": "Revenues",
            "NetIncome": "NetIncomeLoss",
            "Assets": "Assets",
            "Liabilities": "Liabilities",
            "StockholdersEquity": "StockholdersEquity",
            "OperatingCashFlow": "NetCashProvidedByUsedInOperatingActivities"
        }

        extracted_data = {}
        for metric_name, xbrl_tag in key_metrics.items():
            if xbrl_tag in us_gaap:
                metric_data = us_gaap[xbrl_tag]
                # 获取最新年度数据
                units = metric_data.get("units", {})
                usd_data = units.get("USD", [])
                if usd_data:
                    # 按日期排序，取最新
                    latest = sorted(usd_data, key=lambda x: x.get("end", ""), reverse=True)[0]
                    extracted_data[metric_name] = {
                        "value": latest.get("val"),
                        "date": latest.get("end"),
                        "form": latest.get("form")
                    }

        summary = f"提取了 {data.get('entityName', ticker)} 的关键财务指标:\n"
        for metric, info in extracted_data.items():
            summary += f"\n- {metric}: ${info['value']:,} (截至 {info['date']})"

        return {
            "success": True,
            "summary": summary,
            "company_name": data.get("entityName"),
            "cik": cik,
            "metrics": extracted_data
        }

    async def _ticker_to_cik(self, ticker: str) -> str:
        """将股票代码转换为CIK"""
        url = f"{self.base_url}/files/company_tickers.json"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # 查找ticker对应的CIK
        for item in data.values():
            if item.get("ticker", "").upper() == ticker.upper():
                return str(item.get("cik_str"))

        return None

    def to_schema(self) -> Dict[str, Any]:
        """返回工具的Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search_filings", "get_company_facts"],
                        "description": "操作类型: search_filings(搜索披露文件) 或 get_company_facts(获取财务数据)"
                    },
                    "ticker": {
                        "type": "string",
                        "description": "股票代码，如 AAPL, TSLA"
                    },
                    "cik": {
                        "type": "string",
                        "description": "公司CIK号码 (可选，如果提供ticker则自动查询)"
                    },
                    "form_type": {
                        "type": "string",
                        "enum": ["10-K", "10-Q", "8-K", "DEF 14A"],
                        "description": "文件类型: 10-K(年报), 10-Q(季报), 8-K(重大事件), DEF 14A(代理声明)",
                        "default": "10-K"
                    }
                },
                "required": ["action"]
            }
        }
```

#### 1.2 更新MCP工具分配

**修改文件**: `/backend/services/report_orchestrator/app/core/roundtable/mcp_tools.py`

```python
from .sec_edgar_tool import SECEdgarTool

def create_mcp_tools_for_agent(agent_role: str) -> List[Tool]:
    """根据 Agent 角色创建合适的 MCP 工具集"""
    tools = [TavilySearchTool()]  # 所有Agent都有搜索

    if agent_role in ["MarketAnalyst", "市场分析师"]:
        tools.append(PublicDataTool())
        tools.append(YahooFinanceTool())
        tools.append(SECEdgarTool())  # 新增: 官方市场数据

    elif agent_role in ["FinancialExpert", "财务专家"]:
        tools.append(PublicDataTool())
        tools.append(YahooFinanceTool())
        tools.append(SECEdgarTool())  # 新增: 官方财报数据

    elif agent_role in ["RiskAssessor", "风险评估"]:
        tools.append(SECEdgarTool())  # 新增: 披露的风险因素

    # ... 其他Agent

    tools.append(KnowledgeBaseTool())
    return tools
```

#### 1.3 测试SEC EDGAR工具

**测试场景**:
```bash
# 在Python环境中测试
from sec_edgar_tool import SECEdgarTool

tool = SECEdgarTool()

# 测试1: 搜索Tesla的10-K年报
result = await tool.execute(
    action="search_filings",
    ticker="TSLA",
    form_type="10-K",
    limit=3
)
print(result["summary"])

# 测试2: 获取Apple的财务数据
result = await tool.execute(
    action="get_company_facts",
    ticker="AAPL"
)
print(result["summary"])
```

**预期输出**:
```
找到 TESLA, INC. 的 3 个 10-K 文件:
- 2024-02-26: https://...
- 2023-01-31: https://...
- 2022-02-07: https://...
```

#### 1.4 交付物

- ✅ `sec_edgar_tool.py` 文件创建
- ✅ `mcp_tools.py` 更新
- ✅ 单元测试通过
- ✅ 更新 `PHASE3_PROGRESS_SUMMARY.md`

**预计时间**: 0.5天

---

### 阶段 2: Financial Expert Agent架构升级 (P0)

**目标**: 将Financial Expert从ReAct升级到ReWOO架构，提升财务数据提取效率

#### 2.1 理解ReWOO架构

**ReWOO三阶段**:
1. **Plan**: 规划所有需要的工具调用
2. **Execute**: 并行执行所有工具调用
3. **Solve**: 综合所有结果生成分析

**优势**:
- 减少LLM调用次数 (ReAct需要多次Think-Act循环)
- 并行执行工具，速度更快
- 更结构化的思考过程

#### 2.2 创建ReWOO Agent基类

**新文件**: `/backend/services/report_orchestrator/app/core/roundtable/rewoo_agent.py`

```python
"""
ReWOO Agent Implementation
Reasoning WithOut Observation
"""
from typing import List, Dict, Any, Optional
import asyncio
from .agent import Agent
from .tool import Tool


class ReWOOAgent(Agent):
    """
    ReWOO架构的Agent

    三阶段执行:
    1. Plan: 生成工具调用计划
    2. Execute: 并行执行所有工具
    3. Solve: 综合结果生成答案
    """

    def __init__(
        self,
        name: str,
        role_prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7
    ):
        super().__init__(name, role_prompt, model, temperature)
        self.planning_prompt = self._create_planning_prompt()
        self.solving_prompt = self._create_solving_prompt()

    async def analyze(self, query: str, context: Dict[str, Any]) -> str:
        """
        ReWOO三阶段分析

        Args:
            query: 分析任务
            context: 上下文信息

        Returns:
            分析结果
        """
        # Phase 1: Plan
        plan = await self._plan_phase(query, context)

        # Phase 2: Execute (并行)
        observations = await self._execute_phase(plan)

        # Phase 3: Solve
        result = await self._solve_phase(query, plan, observations)

        return result

    async def _plan_phase(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        阶段1: 规划

        生成需要执行的工具调用列表
        """
        planning_messages = [
            {"role": "system", "content": self.planning_prompt},
            {"role": "user", "content": self._format_planning_query(query, context)}
        ]

        # 调用LLM生成计划
        response = await self._call_llm(planning_messages, temperature=0.3)  # 低温度，确保结构化输出

        # 解析计划
        plan = self._parse_plan(response)

        print(f"[{self.name}] Plan generated: {len(plan)} steps")
        for i, step in enumerate(plan):
            print(f"  Step {i+1}: {step['tool']}({step['params']})")

        return plan

    async def _execute_phase(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        阶段2: 执行

        并行执行所有工具调用
        """
        print(f"[{self.name}] Executing {len(plan)} tools in parallel...")

        # 创建异步任务列表
        tasks = []
        for step in plan:
            tool_name = step["tool"]
            tool_params = step["params"]

            # 查找工具
            tool = self._find_tool(tool_name)
            if tool:
                task = tool.execute(**tool_params)
                tasks.append(task)
            else:
                # 工具不存在，返回错误
                tasks.append(asyncio.coroutine(lambda: {
                    "success": False,
                    "error": f"Tool {tool_name} not found"
                })())

        # 并行执行
        observations = await asyncio.gather(*tasks, return_exceptions=True)

        print(f"[{self.name}] Execution complete. {len([o for o in observations if o.get('success', False)])} successful.")

        return observations

    async def _solve_phase(
        self,
        query: str,
        plan: List[Dict[str, Any]],
        observations: List[Dict[str, Any]]
    ) -> str:
        """
        阶段3: 综合

        基于所有观察结果生成最终分析
        """
        solving_messages = [
            {"role": "system", "content": self.solving_prompt},
            {"role": "user", "content": self._format_solving_query(query, plan, observations)}
        ]

        # 调用LLM生成最终分析
        result = await self._call_llm(solving_messages, temperature=self.temperature)

        return result

    def _create_planning_prompt(self) -> str:
        """创建规划阶段的Prompt"""
        return f"""你是 {self.name}。你需要为分析任务制定工具调用计划。

{self.role_prompt}

**你的工具**:
{self._format_tools_description()}

**规划任务**:
给定一个分析任务，你需要:
1. 确定需要哪些信息
2. 选择合适的工具获取这些信息
3. 按逻辑顺序排列工具调用

**输出格式** (JSON):
```json
[
  {{
    "step": 1,
    "tool": "tool_name",
    "params": {{"param1": "value1"}},
    "purpose": "为什么需要这个工具调用"
  }},
  ...
]
```

**重要**: 只输出JSON，不要其他文字。
"""

    def _create_solving_prompt(self) -> str:
        """创建综合阶段的Prompt"""
        return f"""你是 {self.name}。你需要基于工具调用结果生成最终分析。

{self.role_prompt}

**综合任务**:
你已经执行了一系列工具调用并获得了观察结果。现在需要:
1. 整合所有观察结果
2. 进行深入分析
3. 得出结论和建议

**输出要求**:
- 结构化的分析报告
- 引用数据来源
- 明确结论和建议
- 中文输出
"""

    def _format_tools_description(self) -> str:
        """格式化工具描述"""
        descriptions = []
        for tool in self.tools:
            schema = tool.to_schema()
            descriptions.append(f"- {schema['name']}: {schema['description']}")
        return "\n".join(descriptions)

    def _find_tool(self, tool_name: str) -> Optional[Tool]:
        """查找工具"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def _parse_plan(self, llm_response: str) -> List[Dict[str, Any]]:
        """解析LLM生成的计划"""
        import json

        # 提取JSON (可能被包裹在```json ```中)
        json_str = llm_response
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]

        try:
            plan = json.loads(json_str.strip())
            return plan if isinstance(plan, list) else []
        except json.JSONDecodeError as e:
            print(f"[{self.name}] Failed to parse plan: {e}")
            return []

    def _format_planning_query(self, query: str, context: Dict[str, Any]) -> str:
        """格式化规划查询"""
        return f"""**分析任务**: {query}

**上下文信息**:
{self._format_context(context)}

请为此任务制定工具调用计划。
"""

    def _format_solving_query(
        self,
        query: str,
        plan: List[Dict[str, Any]],
        observations: List[Dict[str, Any]]
    ) -> str:
        """格式化综合查询"""
        obs_text = ""
        for i, (step, obs) in enumerate(zip(plan, observations)):
            obs_text += f"\n**Step {i+1}**: {step['tool']}({step['params']})\n"
            obs_text += f"结果: {obs.get('summary', str(obs))}\n"

        return f"""**原始任务**: {query}

**执行计划**:
{obs_text}

请基于以上结果进行综合分析。
"""

    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        parts = []
        for key, value in context.items():
            parts.append(f"- {key}: {value}")
        return "\n".join(parts)
```

#### 2.3 升级Financial Expert为ReWOO Agent

**修改文件**: `/backend/services/report_orchestrator/app/core/roundtable/investment_agents.py`

```python
from .rewoo_agent import ReWOOAgent

def create_financial_expert(language: str = "zh") -> Agent:
    """创建财务专家Agent (ReWOO架构)"""

    role_prompt = """你是**财务专家**，擅长财务报表分析和财务健康度评估。

## 你的专长:
- 财务报表分析 (利润表、资产负债表、现金流量表)
- 财务比率计算 (ROE、ROA、毛利率、净利率、流动比率等)
- 财务趋势分析 (YoY增长、季度环比)
- 财务健康度评估 (盈利能力、偿债能力、运营效率)
- 行业benchmark对比

## 分析框架:
1. **盈利能力**: 毛利率、净利率、ROE、ROA
2. **成长性**: 营收增长率、利润增长率
3. **偿债能力**: 流动比率、速动比率、资产负债率
4. **运营效率**: 存货周转率、应收账款周转率
5. **现金流**: 经营性现金流、自由现金流

## 工具使用策略:
### 上市公司分析:
1. 使用 `sec_edgar` 获取官方10-K/10-Q财报 (美股)
2. 使用 `yahoo_finance` 获取财务比率和历史数据
3. 使用 `tavily_search` 搜索行业benchmark数据

### 非上市公司分析:
1. 使用 `search_knowledge_base` 查询BP中的财务数据
2. 使用 `tavily_search` 搜索同行业公司对比

## 输出要求:
- 引用具体数据来源 (如 "根据2023年10-K报告")
- 计算关键财务比率并解释含义
- 与行业平均水平对比
- 识别财务异常或风险信号
- 给出1-10分的财务健康度评分
"""

    # 使用ReWOO架构
    agent = ReWOOAgent(
        name="FinancialExpert",
        role_prompt=role_prompt,
        model="gpt-4",
        temperature=0.5  # 财务分析需要相对精确
    )

    # 注册MCP工具
    mcp_tools = create_mcp_tools_for_agent("FinancialExpert")
    for tool in mcp_tools:
        agent.register_tool(tool)

    return agent
```

#### 2.4 测试ReWOO Financial Expert

**测试用例**:
```python
# 测试上市公司财务分析
agent = create_financial_expert()

query = "分析Tesla (TSLA)的财务健康度"
context = {
    "company_name": "Tesla",
    "ticker": "TSLA",
    "industry": "Electric Vehicles"
}

result = await agent.analyze(query, context)
print(result)
```

**预期执行流程**:
```
[FinancialExpert] Plan generated: 3 steps
  Step 1: sec_edgar(action='get_company_facts', ticker='TSLA')
  Step 2: yahoo_finance(action='financials', symbol='TSLA', statement='income')
  Step 3: tavily_search(query='electric vehicle industry average profit margin 2024')
[FinancialExpert] Executing 3 tools in parallel...
[FinancialExpert] Execution complete. 3 successful.
[FinancialExpert] Generating final analysis...
```

#### 2.5 交付物

- ✅ `rewoo_agent.py` 基类创建
- ✅ Financial Expert升级为ReWOO
- ✅ 端到端测试通过
- ✅ 性能对比: ReWOO vs ReAct (预期提速30-50%)

**预计时间**: 1天

---

### 阶段 3: Prompt优化 (P0-P1)

**目标**: 优化所有Agent的Prompt，提升分析质量和工具使用效率

#### 3.1 Market Analyst Prompt优化

**修改文件**: `/backend/services/report_orchestrator/app/core/roundtable/investment_agents.py`

**优化要点**:
1. 增加股票代码识别逻辑
2. 引导使用Yahoo Finance和SEC EDGAR
3. 增加TAM/SAM/SOM分析框架
4. 强化竞品分析

**优化后的Prompt**:
```python
def create_market_analyst(language: str = "zh") -> Agent:
    role_prompt = """你是**市场分析师**，专注于市场规模、行业趋势和竞争格局分析。

## 你的专长:
- 市场规模评估 (TAM/SAM/SOM)
- 行业趋势分析
- 竞争格局研究
- 市场进入壁垒评估
- 增长驱动因素识别

## 分析框架 - TAM/SAM/SOM:
1. **TAM (Total Addressable Market)**: 理论最大市场
   - 全球/全国范围
   - 所有潜在客户

2. **SAM (Serviceable Addressable Market)**: 可服务市场
   - 考虑地域、渠道限制
   - 当前可触达的客户

3. **SOM (Serviceable Obtainable Market)**: 可获得市场
   - 考虑竞争、市场份额
   - 未来3-5年可实际获得的市场

## 竞争分析 - Porter五力模型:
1. **现有竞争者**: 主要竞品、市场份额、差异化
2. **潜在进入者**: 进入壁垒、新玩家威胁
3. **替代品**: 其他解决方案的威胁
4. **供应商议价能力**: 上游依赖程度
5. **客户议价能力**: 客户集中度、转换成本

## 工具使用策略:

### 步骤1: 识别公司类型
```python
if 公司已上市:
    # 使用 yahoo_finance 获取市值和股价趋势
    yahoo_finance(action='price', symbol='TICKER')
    yahoo_finance(action='history', symbol='TICKER', period='1y')

    # 使用 sec_edgar 查看最新年报中的市场描述
    sec_edgar(action='search_filings', ticker='TICKER', form_type='10-K', limit=1)
else:
    # 使用知识库查询BP中的市场数据
    search_knowledge_base(query='市场规模 TAM SAM')
```

### 步骤2: 行业研究
```python
# 搜索行业报告和趋势
tavily_search(query='[行业名称] market size 2024 growth rate')
tavily_search(query='[行业名称] industry trends 2024')
```

### 步骤3: 竞争分析
```python
# 搜索主要竞品
tavily_search(query='[公司名称] competitors comparison')
tavily_search(query='[行业名称] market share leaders')

# 如果竞品上市，获取其市值
yahoo_finance(action='price', symbol='COMPETITOR_TICKER')
```

## 输出要求:
1. **市场规模**:
   - TAM: $XXB (数据来源)
   - SAM: $XXB (数据来源)
   - SOM: $XXB (假设与计算逻辑)

2. **行业趋势**:
   - 增长率: XX% CAGR
   - 驱动因素: [列出3-5个]
   - 风险因素: [列出3-5个]

3. **竞争格局**:
   - 主要竞品: [名称、市场份额、市值]
   - 公司定位: [差异化优势]
   - 竞争壁垒: [技术/品牌/网络效应等]

4. **市场评分**: 1-10分 (市场吸引力)

**示例输出格式**:
```markdown
## 市场规模分析

### TAM/SAM/SOM
- **TAM**: $500B (根据IDC 2024全球云计算市场报告)
- **SAM**: $150B (聚焦中国市场，根据Gartner预测)
- **SOM**: $5B (假设3年内获得3%市场份额)

### 增长趋势
- CAGR: 25% (2024-2028)
- 驱动因素:
  1. 数字化转型加速
  2. AI应用普及
  3. 政策支持

## 竞争格局

### 主要竞品
1. **阿里云** - 市场份额30%, 市值 $XXB
2. **腾讯云** - 市场份额20%, 市值 $XXB
3. **华为云** - 市场份额15%

### 公司差异化
- 垂直行业深耕 (金融/医疗)
- AI原生架构
- 成本优势20%

## 市场评分: 8/10
- ✅ 市场规模大
- ✅ 高增长率
- ⚠️ 竞争激烈
```
"""

    agent = Agent(
        name="MarketAnalyst",
        role_prompt=role_prompt,
        model="gpt-4",
        temperature=0.6
    )

    # 注册MCP工具
    mcp_tools = create_mcp_tools_for_agent("MarketAnalyst")
    for tool in mcp_tools:
        agent.register_tool(tool)

    return agent
```

#### 3.2 其他Agent Prompt优化清单

**Team Evaluator**:
- 增加团队背景调查框架 (LinkedIn, Crunchbase)
- 强调创始人previous exits、行业经验
- 要求量化评分 (技术能力/行业经验/执行力)

**Risk Assessor**:
- 引入PEST分析框架 (Political, Economic, Social, Technological)
- 系统化风险分类 (市场风险/技术风险/团队风险/财务风险/法律风险)
- 风险量化评分和缓解建议

**Tech Specialist**:
- 技术架构评估框架
- 技术护城河识别 (专利/算法/数据)
- 技术债务评估

**Legal Advisor**:
- 法律结构审查checklist
- 合规状态评估 (营业执照/资质/许可)
- 知识产权保护评估

#### 3.3 DD Flow Agents优化

**优化 `market_analysis_agent.py`**:

```python
# 当前问题: Prompt过于简单
# 解决方案: 复用Roundtable MarketAnalyst的Prompt，并添加工具

async def analyze_market(company_info: Dict[str, Any]) -> Dict[str, Any]:
    """市场分析Agent"""

    # 创建临时Agent (复用优化后的Prompt)
    agent = create_market_analyst()

    query = f"分析 {company_info['name']} 的市场规模、行业趋势和竞争格局"
    context = company_info

    result = await agent.analyze(query, context)

    return {
        "market_analysis": result,
        "timestamp": datetime.now().isoformat()
    }
```

**类似优化**:
- `team_analysis_agent.py` → 复用TeamEvaluator Prompt
- `risk_agent.py` → 复用RiskAssessor Prompt
- `valuation_agent.py` → 添加Yahoo Finance工具，复用FinancialExpert的估值逻辑

#### 3.4 交付物

- ✅ 7个Roundtable Agent Prompt优化
- ✅ 4个DD Agent Prompt和工具集成
- ✅ Prompt模板文档化
- ✅ A/B测试: 优化前后质量对比

**预计时间**: 1.5天

---

### 阶段 4: 端到端测试 (P1)

**目标**: 全面测试Agent改进效果，确保生产可用

#### 4.1 测试场景设计

**场景1: 上市公司分析 (美股)**
```python
test_case_1 = {
    "company_name": "Tesla",
    "ticker": "TSLA",
    "industry": "Electric Vehicles",
    "stage": "Public",
    "market": "US"
}
```

**预期**:
- ✅ MarketAnalyst能获取股价和市值
- ✅ FinancialExpert能获取10-K财报
- ✅ 所有Agent输出结构化分析
- ✅ Roundtable讨论生成完整报告

**场景2: 上市公司分析 (港股/A股)**
```python
test_case_2 = {
    "company_name": "腾讯",
    "ticker": "0700.HK",
    "industry": "Internet Services",
    "stage": "Public",
    "market": "HK"
}
```

**预期**:
- ✅ Yahoo Finance支持港股数据
- ⚠️ SEC EDGAR不支持 (降级策略)
- ✅ 使用web search补充信息

**场景3: 非上市公司分析**
```python
test_case_3 = {
    "company_name": "某AI创业公司",
    "industry": "Artificial Intelligence",
    "stage": "Series B",
    "bp_uploaded": True
}
```

**预期**:
- ✅ 使用知识库查询BP
- ✅ 使用web search查询行业数据
- ✅ 财务分析基于BP中的数据
- ✅ 所有Agent正常工作

#### 4.2 测试脚本

**创建文件**: `/backend/tests/test_agent_enhancement.py`

```python
"""
Phase 3 Agent Enhancement测试
"""
import asyncio
import json
from datetime import datetime
from app.core.roundtable.investment_agents import create_all_agents


async def test_market_analyst_with_yahoo_finance():
    """测试MarketAnalyst使用Yahoo Finance"""
    print("\n=== Test 1: Market Analyst + Yahoo Finance ===")

    from app.core.roundtable.investment_agents import create_market_analyst

    agent = create_market_analyst()

    query = "分析Tesla (TSLA)的市场地位和竞争格局"
    context = {
        "company_name": "Tesla",
        "ticker": "TSLA",
        "industry": "Electric Vehicles"
    }

    result = await agent.analyze(query, context)

    print(f"Result length: {len(result)} characters")
    print(f"Contains market cap: {'market cap' in result.lower() or '市值' in result}")
    print(f"Contains competitors: {'competitor' in result.lower() or '竞品' in result}")

    assert len(result) > 500, "Result too short"

    print("✅ Test passed")
    return result


async def test_financial_expert_rewoo():
    """测试FinancialExpert ReWOO架构"""
    print("\n=== Test 2: Financial Expert ReWOO ===")

    from app.core.roundtable.investment_agents import create_financial_expert

    agent = create_financial_expert()

    # 验证是否为ReWOO Agent
    from app.core.roundtable.rewoo_agent import ReWOOAgent
    assert isinstance(agent, ReWOOAgent), "Should be ReWOO Agent"

    query = "分析Apple (AAPL)的财务健康度"
    context = {
        "company_name": "Apple",
        "ticker": "AAPL",
        "industry": "Consumer Electronics"
    }

    result = await agent.analyze(query, context)

    print(f"Result length: {len(result)} characters")
    print(f"Contains financial ratios: {'ROE' in result or 'roe' in result or '净资产收益率' in result}")

    assert len(result) > 500, "Result too short"

    print("✅ Test passed")
    return result


async def test_sec_edgar_tool():
    """测试SEC EDGAR工具"""
    print("\n=== Test 3: SEC EDGAR Tool ===")

    from app.core.roundtable.sec_edgar_tool import SECEdgarTool

    tool = SECEdgarTool()

    # 测试获取10-K
    result1 = await tool.execute(
        action="search_filings",
        ticker="MSFT",
        form_type="10-K",
        limit=2
    )

    assert result1["success"], "Search filings failed"
    assert len(result1["filings"]) > 0, "No filings found"

    print(f"Found {len(result1['filings'])} filings for MSFT")

    # 测试获取财务数据
    result2 = await tool.execute(
        action="get_company_facts",
        ticker="MSFT"
    )

    assert result2["success"], "Get company facts failed"
    assert "metrics" in result2, "No metrics returned"

    print(f"Extracted {len(result2['metrics'])} financial metrics")

    print("✅ Test passed")
    return result1, result2


async def test_roundtable_discussion_flow():
    """测试完整Roundtable讨论流程"""
    print("\n=== Test 4: Full Roundtable Discussion ===")

    from app.core.roundtable.roundtable_discussion import RoundtableDiscussion

    discussion = RoundtableDiscussion()

    # 模拟公司数据
    company_data = {
        "name": "NVIDIA",
        "ticker": "NVDA",
        "industry": "Semiconductors",
        "stage": "Public",
        "description": "Leading AI chip manufacturer"
    }

    # 启动讨论
    result = await discussion.start_discussion(
        topic="评估NVIDIA的投资价值",
        context=company_data,
        rounds=2
    )

    print(f"Discussion completed in {result.get('duration', 'N/A')} seconds")
    print(f"Total messages: {len(result.get('messages', []))}")
    print(f"Final report length: {len(result.get('final_report', ''))} characters")

    assert result.get("status") == "completed", "Discussion failed"

    print("✅ Test passed")
    return result


async def test_dd_flow_with_tools():
    """测试DD流程与工具集成"""
    print("\n=== Test 5: DD Flow with MCP Tools ===")

    from app.agents.market_analysis_agent import analyze_market
    from app.agents.team_analysis_agent import analyze_team

    company_info = {
        "name": "Alphabet",
        "ticker": "GOOGL",
        "industry": "Internet Services",
        "founders": ["Larry Page", "Sergey Brin"]
    }

    # 测试市场分析
    market_result = await analyze_market(company_info)
    assert "market_analysis" in market_result, "Market analysis failed"
    print(f"Market analysis: {len(market_result['market_analysis'])} chars")

    # 测试团队分析
    team_result = await analyze_team(company_info)
    assert "team_analysis" in team_result, "Team analysis failed"
    print(f"Team analysis: {len(team_result['team_analysis'])} chars")

    print("✅ Test passed")
    return market_result, team_result


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 3 Agent Enhancement - Test Suite")
    print("=" * 60)

    results = {}

    try:
        results["test1"] = await test_market_analyst_with_yahoo_finance()
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        results["test1"] = None

    try:
        results["test2"] = await test_financial_expert_rewoo()
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        results["test2"] = None

    try:
        results["test3"] = await test_sec_edgar_tool()
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        results["test3"] = None

    try:
        results["test4"] = await test_roundtable_discussion_flow()
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        results["test4"] = None

    try:
        results["test5"] = await test_dd_flow_with_tools()
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        results["test5"] = None

    # 生成测试报告
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r is not None)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")

    # 保存详细报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"/tmp/phase3_test_report_{timestamp}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "success_rate": f"{passed/total*100:.1f}%"
            },
            "results": {k: str(v)[:500] if v else "FAILED" for k, v in results.items()}
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed report saved to: {report_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
```

#### 4.3 性能基准测试

**测试指标**:
1. **数据获取成功率**:
   - Yahoo Finance: >95%
   - SEC EDGAR: >90% (仅美股)
   - Web Search: >98%

2. **响应时间**:
   - 单个Agent分析: <30秒
   - Roundtable讨论(2轮): <3分钟
   - 完整DD流程: <5分钟

3. **输出质量**:
   - 结构化程度: 100%
   - 数据引用率: >80%
   - 平均字数: >1000字/Agent

#### 4.4 交付物

- ✅ 测试套件完成
- ✅ 5个测试场景全部通过
- ✅ 测试报告生成
- ✅ 性能基准达标

**预计时间**: 0.5天

---

### 阶段 5: 文档和部署 (P2)

**目标**: 完善文档，准备生产部署

#### 5.1 更新技术文档

**更新文件**: `/docs/V4/AGENT_ARCHITECTURE.md`

内容包括:
- ReWOO架构说明
- MCP工具集成指南
- Agent Prompt最佳实践
- 工具使用示例

#### 5.2 更新用户文档

**更新文件**: `/docs/V4/USER_GUIDE.md`

内容包括:
- 上市公司vs非上市公司分析差异
- 数据来源说明 (SEC官方、Yahoo Finance等)
- 如何解读Agent分析报告
- 常见问题FAQ

#### 5.3 部署清单

**Docker镜像更新**:
```bash
# 确保所有依赖已安装
cd /Users/dengjianbo/Documents/Magellan
docker-compose build --no-cache report_orchestrator

# 重启服务
docker-compose restart report_orchestrator

# 验证服务
docker-compose logs -f report_orchestrator
```

**环境变量配置**:
```bash
# .env 文件添加 (如果需要)
SEC_EDGAR_USER_AGENT="Magellan AI Investment Platform (your-email@example.com)"
```

#### 5.4 更新进度文档

**更新文件**: `/PHASE3_PROGRESS_SUMMARY.md`

标记所有任务为完成状态。

#### 5.5 交付物

- ✅ 技术文档完善
- ✅ 用户文档更新
- ✅ Docker部署成功
- ✅ Phase 3 完成报告

**预计时间**: 0.5天

---

## 📊 总体时间表

| 阶段 | 任务 | 预计时间 | 优先级 | 依赖 |
|------|------|----------|--------|------|
| 0 | 当前状态盘点 | ✅ DONE | - | - |
| 1 | SEC EDGAR集成 | 0.5天 | P0 | 无 |
| 2 | ReWOO架构升级 | 1天 | P0 | 阶段1 |
| 3 | Prompt优化 | 1.5天 | P0-P1 | 阶段2 |
| 4 | 端到端测试 | 0.5天 | P1 | 阶段3 |
| 5 | 文档和部署 | 0.5天 | P2 | 阶段4 |
| **总计** | - | **4天** | - | - |

---

## 🎯 成功标准

### 阶段1完成标准:
- ✅ SEC EDGAR工具创建并测试通过
- ✅ 能成功获取至少3家美股公司的10-K
- ✅ Financial Expert和Market Analyst能调用工具

### 阶段2完成标准:
- ✅ ReWOO基类创建
- ✅ Financial Expert成功升级
- ✅ 性能提升>30% (对比ReAct)

### 阶段3完成标准:
- ✅ 7个Roundtable Agent Prompt优化
- ✅ 4个DD Agent优化
- ✅ 工具使用成功率>90%

### 阶段4完成标准:
- ✅ 5个测试场景全部通过
- ✅ 性能基准达标
- ✅ 无critical bug

### 阶段5完成标准:
- ✅ 文档更新完成
- ✅ Docker部署成功
- ✅ Phase 3完成报告发布

### Phase 3整体完成标准:
1. ✅ Yahoo Finance工具集成 (已完成)
2. ✅ SEC EDGAR工具集成
3. ✅ 至少1个Agent升级为ReWOO
4. ✅ 所有Agent Prompt结构化
5. ✅ 上市公司数据获取成功率>90%
6. ✅ 端到端测试通过
7. ✅ 文档完善

---

## 💰 成本预估

### MVP阶段 (当前):
- Yahoo Finance: $0/月 ✅
- SEC EDGAR: $0/月 ✅
- Tavily Search: $0/月 (免费额度) ✅
- OpenAI GPT-4: 按使用量付费 ✅
- **总计**: $0/月 (不含LLM API)

### 未来扩展 (可选):
- Alpha Vantage Premium: $49.99/月
- Google Patents (SerpAPI): ~$50/月
- Crunchbase API: ~$99/月
- **扩展总计**: ~$200/月

---

## 🚀 下一步行动

**立即开始**:
1. 创建 `sec_edgar_tool.py`
2. 更新 `mcp_tools.py`
3. 测试SEC EDGAR工具

**完成阶段1后**:
4. 创建 `rewoo_agent.py`
5. 升级Financial Expert
6. 性能对比测试

**完成阶段2后**:
7. 优化所有Agent Prompt
8. 更新DD Agent
9. 工具使用测试

**完成阶段3后**:
10. 运行完整测试套件
11. 生成测试报告
12. 修复发现的问题

**完成阶段4后**:
13. 更新所有文档
14. 部署到生产环境
15. 发布Phase 3完成报告

---

## 📝 风险和缓解措施

### 风险1: SEC EDGAR API限流
**概率**: 中
**影响**: 中
**缓解**:
- 实现请求缓存
- 添加重试逻辑
- 降级到Yahoo Finance

### 风险2: ReWOO架构复杂度
**概率**: 中
**影响**: 高
**缓解**:
- 先实现MVP版本
- 充分测试Plan/Execute/Solve流程
- 保留ReAct作为fallback

### 风险3: Prompt优化效果不明显
**概率**: 低
**影响**: 中
**缓解**:
- A/B测试对比效果
- 收集用户反馈
- 迭代优化

### 风险4: 测试发现critical bug
**概率**: 中
**影响**: 高
**缓解**:
- 每个阶段都进行测试
- 及时修复问题
- 保留回滚能力

---

## 📚 参考资料

### MCP工具文档:
- SEC EDGAR API: https://www.sec.gov/edgar/sec-api-documentation
- Yahoo Finance: https://github.com/ranaroussi/yfinance
- Tavily Search: https://tavily.com/docs

### Agent架构论文:
- ReAct: https://arxiv.org/abs/2210.03629
- ReWOO: https://arxiv.org/abs/2305.18323
- Plan-and-Solve: https://arxiv.org/abs/2305.04091

### 财务分析框架:
- 财务比率指南: https://www.investopedia.com/financial-ratios
- SEC 10-K解读: https://www.sec.gov/files/reada10k.pdf

---

**最后更新**: 2025-11-16 20:00
**下一个里程碑**: 完成SEC EDGAR工具集成 (阶段1)
**预计Phase 3完成日期**: 2025-11-20

---

## ✅ 执行检查清单

### 阶段1检查项:
- [ ] `sec_edgar_tool.py` 文件创建
- [ ] `mcp_tools.py` 更新
- [ ] SEC EDGAR工具单元测试
- [ ] 至少3家公司测试通过

### 阶段2检查项:
- [ ] `rewoo_agent.py` 基类创建
- [ ] Financial Expert升级
- [ ] ReWOO工作流测试
- [ ] 性能对比报告

### 阶段3检查项:
- [ ] Market Analyst Prompt优化
- [ ] Financial Expert Prompt优化
- [ ] Team Evaluator Prompt优化
- [ ] Risk Assessor Prompt优化
- [ ] Tech Specialist Prompt优化
- [ ] Legal Advisor Prompt优化
- [ ] Leader Prompt优化
- [ ] DD Agents优化

### 阶段4检查项:
- [ ] 测试场景1: 美股上市公司
- [ ] 测试场景2: 港股/A股公司
- [ ] 测试场景3: 非上市公司
- [ ] 测试场景4: Roundtable讨论
- [ ] 测试场景5: DD流程
- [ ] 性能基准测试
- [ ] 测试报告生成

### 阶段5检查项:
- [ ] 技术文档更新
- [ ] 用户文档更新
- [ ] Docker镜像构建
- [ ] 服务部署验证
- [ ] Phase 3完成报告

---

**状态**: 📋 Ready to Execute
**责任人**: Claude Code
**审核**: User
