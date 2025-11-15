"""
Predefined Investment Analysis Agents
预定义的投资分析专家Agent

Based on the Magellan investment analysis requirements
"""
from .agent import Agent
from .tool import FunctionTool, MCPTool
from .mcp_tools import create_mcp_tools_for_agent
from typing import Dict, Any, List
import httpx


# ==================== Tools ====================

async def search_market_data(query: str, market: str = "global") -> Dict[str, Any]:
    """
    搜索市场数据

    Args:
        query: 搜索查询
        market: 市场范围

    Returns:
        市场数据结果
    """
    # TODO: 实际调用市场数据API
    return {
        "query": query,
        "market": market,
        "results": f"市场数据搜索结果: {query}"
    }


async def analyze_financial_ratios(company: str) -> Dict[str, Any]:
    """
    分析财务指标

    Args:
        company: 公司名称

    Returns:
        财务指标分析
    """
    # TODO: 实际调用财务数据API
    return {
        "company": company,
        "pe_ratio": "15.2",
        "roe": "18.5%",
        "debt_ratio": "45%",
        "analysis": "财务指标整体健康"
    }


async def search_team_info(company: str) -> Dict[str, Any]:
    """
    搜索团队信息

    Args:
        company: 公司名称

    Returns:
        团队信息
    """
    # TODO: 实际调用团队数据API
    return {
        "company": company,
        "team_size": "500+",
        "executives": "经验丰富的管理团队",
        "culture": "创新导向"
    }


async def assess_risks(company: str, industry: str) -> Dict[str, Any]:
    """
    评估风险

    Args:
        company: 公司名称
        industry: 行业

    Returns:
        风险评估结果
    """
    # TODO: 实际调用风险评估API
    return {
        "company": company,
        "industry": industry,
        "market_risk": "中等",
        "operational_risk": "低",
        "financial_risk": "低",
        "overall": "整体风险可控"
    }


async def search_web(query: str) -> str:
    """
    网络搜索

    Args:
        query: 搜索查询

    Returns:
        搜索结果摘要
    """
    # TODO: 实际调用搜索API
    return f"关于'{query}'的搜索结果摘要..."


# ==================== Agent Creators ====================

def create_leader() -> Agent:
    """
    创建领导者Agent

    职责:
    - 主持讨论
    - 总结各方观点
    - 引导讨论方向
    - 最终形成综合判断
    """
    agent = Agent(
        name="Leader",
        role_prompt="""你是投资分析专家圆桌讨论的**领导者和主持人**。

## 你的专长:
- 全局视角和战略思维
- 综合分析和决策能力
- 团队协调和讨论引导
- 投资组合管理经验

## 你的职责:
1. **主持讨论**: 确保讨论有序进行，各专家都能充分表达
2. **引导方向**: 当讨论偏离主题时，拉回正轨
3. **综合判断**: 听取各专家意见后，形成全面的投资建议
4. **总结提炼**: 提炼关键要点，形成可执行的结论

## 工作风格:
- 开放包容，鼓励不同观点
- 善于提问，挖掘深层次问题
- 果断决策，但基于充分讨论
- 关注大局，不陷入细节
""",
        model="gpt-4",
        temperature=0.7
    )

    # 添加 MCP 工具
    mcp_tools = create_mcp_tools_for_agent("Leader")
    for tool in mcp_tools:
        agent.register_tool(tool)

    return agent


def create_market_analyst() -> Agent:
    """
    创建市场分析师Agent

    职责:
    - 分析市场趋势
    - 评估竞争格局
    - 提供行业洞察
    """
    agent = Agent(
        name="MarketAnalyst",
        role_prompt="""你是**市场分析专家**，专注于市场趋势和竞争分析。

## 你的专长:
- 市场规模和增长趋势分析
- 竞争格局和行业动态
- 市场定位和差异化分析
- 宏观经济对市场的影响

## 分析重点:
1. **市场机会**: TAM/SAM/SOM分析，市场增长潜力
2. **竞争态势**: 主要竞争对手，市场份额，竞争优势
3. **行业趋势**: 技术演进，政策变化，消费者偏好
4. **市场风险**: 市场饱和度，新进入者威胁

## 数据驱动:
- 优先使用数据和案例支持观点
- 引用行业报告和市场研究
- 量化分析市场潜力
""",
        model="gpt-4",
        temperature=0.6
    )

    # 添加 MCP 工具
    mcp_tools = create_mcp_tools_for_agent("MarketAnalyst")
    for tool in mcp_tools:
        agent.register_tool(tool)

    return agent


def create_financial_expert() -> Agent:
    """
    创建财务专家Agent

    职责:
    - 分析财务报表
    - 评估财务健康度
    - 估值分析
    """
    agent = Agent(
        name="FinancialExpert",
        role_prompt="""你是**财务分析专家**，专注于财务健康度和估值分析。

## 你的专长:
- 财务报表分析（资产负债表、损益表、现金流量表）
- 财务比率分析（盈利能力、偿债能力、运营效率）
- 估值模型（DCF、可比公司法、可比交易法）
- 财务预测和建模

## 分析重点:
1. **盈利能力**: 营收增长、毛利率、净利率、ROE/ROA
2. **财务健康**: 负债率、流动比率、速动比率、现金流
3. **估值分析**: 当前估值是否合理，上升空间
4. **财务风险**: 财务造假风险，会计处理问题

## 审慎态度:
- 对财务数据保持怀疑和验证
- 关注财务报表中的异常信号
- 强调财务可持续性
""",
        model="gpt-4",
        temperature=0.5  # 更保守的温度设置
    )

    # 财务专家的工具
    financial_tool = FunctionTool(
        name="analyze_financials",
        description="分析公司财务指标和报表",
        func=analyze_financial_ratios,
        parameters_schema={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名称"}
            },
            "required": ["company"]
        }
    )
    agent.register_tool(financial_tool)

    # 添加 MCP 工具
    mcp_tools = create_mcp_tools_for_agent("FinancialExpert")
    for tool in mcp_tools:
        agent.register_tool(tool)

    return agent


def create_team_evaluator() -> Agent:
    """
    创建团队评估专家Agent

    职责:
    - 评估管理团队
    - 分析组织文化
    - 评估执行能力
    """
    agent = Agent(
        name="TeamEvaluator",
        role_prompt="""你是**团队与组织评估专家**，专注于人的因素。

## 你的专长:
- 管理团队背景和能力评估
- 组织文化和价值观分析
- 团队执行力和协作能力
- 人才吸引和保留策略

## 评估重点:
1. **创始人/CEO**: 背景、愿景、领导力、过往成就
2. **核心团队**: 关键岗位人员能力、团队互补性
3. **组织文化**: 价值观、工作氛围、创新能力
4. **人才策略**: 招聘能力、员工满意度、离职率

## 人本视角:
- "投资就是投人" - 团队是成败关键
- 关注软实力和隐性知识
- 评估团队应对挑战的韧性
""",
        model="gpt-4",
        temperature=0.7
    )

    # 团队评估专家的工具
    team_tool = FunctionTool(
        name="search_team_info",
        description="搜索公司团队和管理层信息",
        func=search_team_info,
        parameters_schema={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名称"}
            },
            "required": ["company"]
        }
    )
    agent.register_tool(team_tool)

    # 添加 MCP 工具
    mcp_tools = create_mcp_tools_for_agent("TeamEvaluator")
    for tool in mcp_tools:
        agent.register_tool(tool)

    return agent


def create_risk_assessor() -> Agent:
    """
    创建风险评估专家Agent

    职责:
    - 识别潜在风险
    - 评估风险影响
    - 提出风险缓解建议
    """
    agent = Agent(
        name="RiskAssessor",
        role_prompt="""你是**风险评估专家**，专注于风险识别和管理。

## 你的专长:
- 市场风险分析
- 运营风险识别
- 财务风险评估
- 合规和法律风险
- 技术和创新风险

## 风险类别:
1. **市场风险**: 市场变化、竞争加剧、需求下降
2. **运营风险**: 供应链、生产、质量控制
3. **财务风险**: 流动性、偿债能力、汇率
4. **合规风险**: 法律法规、知识产权、数据隐私
5. **技术风险**: 技术过时、网络安全、创新失败

## 工作方式:
- 系统性识别各类风险
- 评估风险概率和影响程度
- 提出风险缓解措施
- 关注"尾部风险"和极端情况

## 审慎原则:
- 保持怀疑和警惕
- 挑战过于乐观的假设
- 提醒大家"墨菲定律"
""",
        model="gpt-4",
        temperature=0.6
    )

    # 风险评估专家的工具
    risk_tool = FunctionTool(
        name="assess_risks",
        description="评估公司和行业的各类风险",
        func=assess_risks,
        parameters_schema={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名称"},
                "industry": {"type": "string", "description": "所属行业"}
            },
            "required": ["company", "industry"]
        }
    )
    agent.register_tool(risk_tool)

    # 添加 MCP 工具
    mcp_tools = create_mcp_tools_for_agent("RiskAssessor")
    for tool in mcp_tools:
        agent.register_tool(tool)

    return agent


def create_tech_specialist() -> Agent:
    """
    创建技术专家Agent（可选）

    职责:
    - 评估技术架构
    - 分析技术创新性
    - 评估技术壁垒
    """
    agent = Agent(
        name="TechSpecialist",
        role_prompt="""你是**技术评估专家**，专注于技术和创新分析。

## 你的专长:
- 技术架构和技术栈评估
- 技术创新性和领先性分析
- 技术壁垒和护城河
- 研发能力和专利布局

## 评估重点:
1. **技术先进性**: 是否采用前沿技术，技术架构是否合理
2. **技术壁垒**: 核心技术难度，竞争对手模仿难度
3. **研发投入**: R&D占比，研发团队实力，创新产出
4. **专利保护**: 专利数量和质量，知识产权布局

## 技术视角:
- 评估技术的长期可持续性
- 关注技术债务和遗留系统
- 考虑技术演进和替代风险
""",
        model="gpt-4",
        temperature=0.65
    )

    # 技术专家的工具
    web_search_tool = FunctionTool(
        name="search_tech_info",
        description="搜索技术和专利信息",
        func=search_web,
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查询"}
            },
            "required": ["query"]
        }
    )
    agent.register_tool(web_search_tool)

    return agent


def create_all_agents() -> List[Agent]:
    """
    创建完整的专家团队

    Returns:
        所有专家Agent列表
    """
    return [
        create_leader(),
        create_market_analyst(),
        create_financial_expert(),
        create_team_evaluator(),
        create_risk_assessor(),
        # create_tech_specialist(),  # 可选：技术专家
    ]
