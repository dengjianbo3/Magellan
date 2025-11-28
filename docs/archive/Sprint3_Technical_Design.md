# Sprint 3 技术设计文档：DD 工作流与核心分析模块

**版本**: 1.0  
**日期**: 2025-10-22  
**状态**: 设计阶段

---

## 1. 概述

### 1.1 目标
将 `report_orchestrator` 从 V2 的二级市场股票分析工作流，重构为 V3 的一级市场尽职调查（Due Diligence, DD）工作流。

### 1.2 核心变化

| 维度 | V2 (当前) | V3 (目标) |
|------|-----------|-----------|
| **输入** | `ticker` (股票代码) | `company_name` + `bp_file` (商业计划书) |
| **数据源** | yfinance (二级市场数据) | 天眼查 API + Tavily 搜索 + 内部知识库 |
| **工作流** | 数据获取 → LLM 生成 → 问题清单 | 文档解析 → TDD → MDD → 交叉验证 → DD清单 |
| **输出** | 股票投资报告 | 投资备忘录 (IM) 草稿 |
| **Agent** | AnalysisAgent (通用分析) | TeamAnalysisAgent + MarketAnalysisAgent |

---

## 2. 架构设计

### 2.1 服务依赖图

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (WebSocket)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              report_orchestrator (DD Workflow)               │
│                                                              │
│  States:                                                     │
│  1. DOC_PARSE    → 解析 BP                                   │
│  2. TDD          → 团队背景调查                               │
│  3. MDD          → 市场分析                                   │
│  4. CROSS_CHECK  → 交叉验证                                   │
│  5. DD_QUESTIONS → 生成 DD 问题清单                           │
│  6. HITL_REVIEW  → 人工审核                                   │
└────┬─────────┬──────────┬──────────┬──────────┬─────────────┘
     │         │          │          │          │
     ↓         ↓          ↓          ↓          ↓
┌─────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌─────────────┐
│   LLM   │ │External│ │  Web     │ │Internal│ │ User        │
│ Gateway │ │  Data  │ │ Search   │ │Knowledge│ │ Service     │
│         │ │Service │ │ Service  │ │ Service │ │             │
└─────────┘ └────────┘ └──────────┘ └────────┘ └─────────────┘
```

### 2.2 新的服务编排逻辑

```python
# 伪代码展示新工作流
async def dd_workflow(company_name: str, bp_file: UploadFile):
    # Step 1: 文档解析 (DOC_PARSE)
    bp_structured_data = await llm_gateway.parse_bp(bp_file)
    
    # Step 2: 团队背景调查 (TDD - Team Due Diligence)
    team_info = bp_structured_data.get("team")
    external_team_data = await external_data_service.search_people(team_info)
    web_team_data = await web_search_service.search(f"{team_info} background")
    team_analysis = await TeamAnalysisAgent.analyze(team_info, external_team_data, web_team_data)
    
    # Step 3: 市场分析 (MDD - Market Due Diligence)
    market_info = bp_structured_data.get("market")
    web_market_data = await web_search_service.search(f"{market_info} market size")
    internal_insights = await internal_knowledge_service.search(f"similar projects in {market_info}")
    market_analysis = await MarketAnalysisAgent.analyze(market_info, web_market_data, internal_insights)
    
    # Step 4: 交叉验证 (CROSS_CHECK)
    discrepancies = await cross_check(bp_structured_data, external_data, web_data)
    
    # Step 5: 生成 DD 问题清单 (DD_QUESTIONS)
    dd_questions = await RiskAgent.generate_dd_questions(team_analysis, market_analysis, discrepancies)
    
    # Step 6: HITL 审核
    return {
        "preliminary_im": {
            "team_section": team_analysis,
            "market_section": market_analysis
        },
        "dd_questions": dd_questions
    }
```

---

## 3. 数据模型设计

### 3.1 输入模型

```python
class DDAnalysisRequest(BaseModel):
    """新的 DD 分析请求"""
    company_name: str = Field(..., description="公司名称")
    bp_file: UploadFile = Field(..., description="商业计划书 PDF 文件")
    user_id: str = Field(default="default_user", description="发起分析的用户 ID")

class InstitutionPreference(BaseModel):
    """机构投资偏好 (Sprint 4 使用，此处预留)"""
    investment_themes: List[str] = Field(default=[], description="投资主题，如 ['SaaS', 'AI']")
    preferred_stages: List[str] = Field(default=[], description="偏好阶段，如 ['Seed', 'Series A']")
    focus_sectors: List[str] = Field(default=[], description="关注赛道")
```

### 3.2 BP 结构化数据模型

```python
class TeamMember(BaseModel):
    name: str
    title: str
    background: str

class BPStructuredData(BaseModel):
    """从 BP 中提取的结构化数据"""
    company_name: str
    founding_date: Optional[str] = None
    team: List[TeamMember] = []
    product_description: str
    market_size_tam: Optional[str] = None
    target_market: str
    competitors: List[str] = []
    funding_request: Optional[str] = None
    current_valuation: Optional[str] = None
    financial_projections: Dict[str, Any] = {}
```

### 3.3 分析模块输出模型

```python
class TeamAnalysisOutput(BaseModel):
    """团队分析模块输出"""
    summary: str = Field(..., description="团队整体评价")
    strengths: List[str] = Field(..., description="团队优势")
    concerns: List[str] = Field(..., description="潜在担忧")
    experience_match_score: float = Field(..., ge=0, le=10, description="经验匹配度评分")
    data_sources: List[str] = Field(..., description="数据来源")

class MarketAnalysisOutput(BaseModel):
    """市场分析模块输出"""
    summary: str
    market_validation: str = Field(..., description="市场规模验证结果")
    growth_potential: str
    competitive_landscape: str
    red_flags: List[str] = []
    data_sources: List[str]

class DDQuestion(BaseModel):
    """DD 问题清单条目"""
    category: str = Field(..., description="分类：Team/Market/Product/Financial/Risk")
    question: str
    reasoning: str = Field(..., description="为什么要问这个问题")
    bp_reference: Optional[str] = Field(None, description="BP 中相关内容的引用")

class PreliminaryIM(BaseModel):
    """初步投资备忘录"""
    company_name: str
    team_section: TeamAnalysisOutput
    market_section: MarketAnalysisOutput
    dd_questions: List[DDQuestion]
    generated_at: str
```

### 3.4 WebSocket 消息模型

```python
class DDStep(BaseModel):
    """DD 工作流步骤"""
    id: int
    title: str
    status: str  # 'running', 'success', 'error', 'paused'
    result: Optional[str] = None
    progress: Optional[float] = None  # 0-100
    sub_steps: Optional[List[str]] = None

class DDWorkflowMessage(BaseModel):
    """WebSocket 推送的消息格式"""
    session_id: str
    status: str  # 'in_progress', 'hitl_required', 'completed', 'error'
    current_step: DDStep
    preliminary_im: Optional[PreliminaryIM] = None
```

---

## 4. API 接口设计

### 4.1 新的 WebSocket 端点

```python
@app.websocket("/ws/start_dd_analysis")
async def websocket_dd_analysis_endpoint(websocket: WebSocket):
    """
    V3 的 DD 工作流 WebSocket 端点
    
    Client 发送:
    {
        "company_name": "TestCo",
        "bp_file_base64": "...",  # Base64 编码的文件内容
        "user_id": "investor_001"
    }
    
    Server 推送:
    {
        "session_id": "dd_session_xxx",
        "status": "in_progress",
        "current_step": {
            "id": 1,
            "title": "正在解析商业计划书",
            "status": "running",
            "progress": 30
        }
    }
    """
```

### 4.2 新的 HTTP 端点（用于测试）

```python
@app.post("/start_dd_analysis", response_model=DDWorkflowMessage)
async def start_dd_analysis_http(
    company_name: str = Form(...),
    bp_file: UploadFile = File(...),
    user_id: str = Form(default="default_user")
):
    """HTTP 版本的 DD 分析入口（用于测试和简单集成）"""

@app.get("/dd_session/{session_id}", response_model=DDWorkflowMessage)
async def get_dd_session_status(session_id: str):
    """查询 DD 会话状态"""

@app.post("/dd_session/{session_id}/continue")
async def continue_dd_session(session_id: str, user_input: dict):
    """继续被 HITL 暂停的 DD 会话"""
```

---

## 5. Agent 设计

### 5.1 TeamAnalysisAgent

**职责**: 综合多源信息，生成团队分析报告

**输入**:
- BP 中的团队信息
- External Data Service 返回的工商/LinkedIn 数据
- Web Search Service 返回的背景搜索结果

**处理逻辑**:
```python
class TeamAnalysisAgent:
    async def analyze(
        self,
        bp_team_info: List[TeamMember],
        external_data: Dict,
        web_search_results: List[SearchResult]
    ) -> TeamAnalysisOutput:
        # 1. 构建综合上下文
        context = self._build_context(bp_team_info, external_data, web_search_results)
        
        # 2. 调用 LLM 生成分析
        prompt = f"""
        你是一位资深的风险投资分析师，专注于团队尽职调查（TDD）。
        
        **任务**: 分析以下创业团队，评估其执行项目的能力。
        
        **BP 中的团队信息**:
        {json.dumps(bp_team_info, ensure_ascii=False)}
        
        **外部验证数据**:
        {json.dumps(external_data, ensure_ascii=False)}
        
        **网络搜索结果**:
        {self._format_search_results(web_search_results)}
        
        **输出要求**:
        请生成一个 JSON 对象，包含以下字段：
        - summary: 团队整体评价（200-300字）
        - strengths: 团队优势列表（3-5条）
        - concerns: 潜在担忧列表（2-4条）
        - experience_match_score: 经验匹配度评分（0-10分）
        - data_sources: 使用的数据来源列表
        """
        
        response = await call_llm_gateway(prompt)
        return TeamAnalysisOutput(**json.loads(response))
```

### 5.2 MarketAnalysisAgent

**职责**: 验证市场规模，分析竞争格局

**输入**:
- BP 中的市场信息
- Web Search 的市场数据
- Internal Knowledge 的历史项目洞察

**处理逻辑**:
```python
class MarketAnalysisAgent:
    async def analyze(
        self,
        bp_market_info: Dict,
        web_market_data: List[SearchResult],
        internal_insights: List[Dict]
    ) -> MarketAnalysisOutput:
        prompt = f"""
        你是一位资深的行业分析师，专注于市场尽职调查（MDD）。
        
        **任务**: 验证 BP 中的市场假设，分析竞争格局。
        
        **BP 声称的市场信息**:
        - 目标市场: {bp_market_info.get('target_market')}
        - 市场规模 (TAM): {bp_market_info.get('market_size_tam')}
        - 竞品: {bp_market_info.get('competitors')}
        
        **网络搜索到的市场数据**:
        {self._format_search_results(web_market_data)}
        
        **内部历史洞察**:
        {json.dumps(internal_insights, ensure_ascii=False)}
        
        **输出要求**:
        生成 JSON，包含：
        - summary: 市场整体评价
        - market_validation: BP 中市场规模是否合理？有无夸大？
        - growth_potential: 增长潜力评估
        - competitive_landscape: 竞争格局分析
        - red_flags: 发现的市场风险
        """
        # ...
```

### 5.3 RiskAgent (升级版)

**V3 进化**: 从生成"追问问题"升级为生成"专业 DD 问题清单"

```python
class RiskAgent:
    async def generate_dd_questions(
        self,
        team_analysis: TeamAnalysisOutput,
        market_analysis: MarketAnalysisOutput,
        bp_data: BPStructuredData
    ) -> List[DDQuestion]:
        prompt = f"""
        你是一位经验丰富的投资负责人，即将与创始人进行深度访谈。
        
        **背景**:
        - 团队分析: {team_analysis.summary}
        - 市场分析: {market_analysis.summary}
        - BP 关键数据: {bp_data}
        
        **任务**: 生成 15-20 个有针对性的 DD 问题，帮助投委会做出决策。
        
        问题应该：
        1. 具体且可验证（避免"请介绍一下你们的团队"这种宽泛问题）
        2. 针对 BP 中的薄弱环节或可疑数据
        3. 涵盖 Team/Market/Product/Financial/Risk 五大类
        
        **输出格式**: 
        [
          {{
            "category": "Team",
            "question": "BP 第5页提到 CTO 有 AI 背景，请提供其在 XX 公司期间主导的具体项目和成果。",
            "reasoning": "CTO 的技术能力是产品壁垒的关键，需要验证。",
            "bp_reference": "第5页，团队介绍"
          }},
          ...
        ]
        """
        # ...
```

---

## 6. 工作流状态机

### 6.1 状态定义

```python
class DDWorkflowState(str, Enum):
    INIT = "init"
    DOC_PARSE = "doc_parse"           # 解析 BP
    TDD = "team_dd"                   # 团队尽调
    MDD = "market_dd"                 # 市场尽调
    CROSS_CHECK = "cross_check"       # 交叉验证
    DD_QUESTIONS = "dd_questions"     # 生成问题清单
    HITL_REVIEW = "hitl_review"       # 人工审核
    COMPLETED = "completed"
    ERROR = "error"
```

### 6.2 状态转换图

```
[INIT]
  ↓
[DOC_PARSE] ─────────────┐
  ↓                      │ (解析失败)
[TDD] ←──┐               │
  ↓      │ (并行)        ↓
[MDD] ←──┘             [ERROR]
  ↓
[CROSS_CHECK]
  ↓
[DD_QUESTIONS]
  ↓
[HITL_REVIEW] ←──────────┐
  ↓                      │ (用户要求修改)
  │                      │
  └─ (用户确认) ─────────┘
  ↓
[COMPLETED]
```

### 6.3 状态机实现

```python
class DDStateMachine:
    def __init__(self, session_id: str, company_name: str, bp_file: UploadFile):
        self.session_id = session_id
        self.state = DDWorkflowState.INIT
        self.context = {
            "company_name": company_name,
            "bp_file": bp_file,
            "bp_data": None,
            "team_analysis": None,
            "market_analysis": None,
            "dd_questions": None
        }
    
    async def run(self, websocket: WebSocket):
        """执行完整的 DD 工作流"""
        try:
            await self.transition_to(DDWorkflowState.DOC_PARSE, websocket)
            await self.transition_to(DDWorkflowState.TDD, websocket)
            await self.transition_to(DDWorkflowState.MDD, websocket)
            await self.transition_to(DDWorkflowState.CROSS_CHECK, websocket)
            await self.transition_to(DDWorkflowState.DD_QUESTIONS, websocket)
            await self.transition_to(DDWorkflowState.HITL_REVIEW, websocket)
            await self.transition_to(DDWorkflowState.COMPLETED, websocket)
        except Exception as e:
            await self.transition_to(DDWorkflowState.ERROR, websocket, error=str(e))
    
    async def transition_to(self, new_state: DDWorkflowState, websocket: WebSocket, **kwargs):
        """状态转换并执行相应操作"""
        self.state = new_state
        
        if new_state == DDWorkflowState.DOC_PARSE:
            await self._execute_doc_parse(websocket)
        elif new_state == DDWorkflowState.TDD:
            await self._execute_tdd(websocket)
        # ... 其他状态的处理
```

---

## 7. 测试计划

### 7.1 单元测试

```python
# tests/test_team_analysis_agent.py
async def test_team_analysis_agent():
    agent = TeamAnalysisAgent()
    mock_bp_team = [TeamMember(name="张三", title="CEO", background="10年 SaaS 经验")]
    mock_external = {"linkedin": "..."}
    mock_web = [SearchResult(...)]
    
    result = await agent.analyze(mock_bp_team, mock_external, mock_web)
    
    assert result.summary is not None
    assert len(result.strengths) >= 3
    assert 0 <= result.experience_match_score <= 10
```

### 7.2 集成测试（里程碑测试）

```python
# tests/test_dd_workflow_integration.py
async def test_complete_dd_workflow():
    """
    Sprint 3 里程碑测试：
    通过 API 触发一个新的 DD 工作流，传入一个公司名和一份 BP。
    Orchestrator 应能按顺序调用各服务，并最终生成包含"团队分析"和
    "市场分析"两个章节的结构化文本。
    """
    # 1. 准备测试数据
    company_name = "TestCo AI"
    bp_file = create_test_bp_file()
    
    # 2. 发起 DD 分析
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/start_dd_analysis",
            data={"company_name": company_name, "user_id": "test_user"},
            files={"bp_file": bp_file}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # 3. 验证输出结构
    assert "preliminary_im" in data
    assert "team_section" in data["preliminary_im"]
    assert "market_section" in data["preliminary_im"]
    assert "dd_questions" in data
    
    # 4. 验证内容质量
    team_section = data["preliminary_im"]["team_section"]
    assert len(team_section["strengths"]) >= 3
    assert team_section["experience_match_score"] is not None
    
    market_section = data["preliminary_im"]["market_section"]
    assert market_section["market_validation"] is not None
    
    dd_questions = data["dd_questions"]
    assert len(dd_questions) >= 10
    assert all(q["category"] in ["Team", "Market", "Product", "Financial", "Risk"] for q in dd_questions)
```

---

## 8. 实施计划

### Phase 1: 基础重构（2-3天）
- [ ] 定义所有新的 Pydantic 模型
- [ ] 创建 `DDStateMachine` 类
- [ ] 实现新的 WebSocket 端点骨架
- [ ] 编写单元测试

### Phase 2: Agent 实现（3-4天）
- [ ] 实现 `TeamAnalysisAgent`
- [ ] 实现 `MarketAnalysisAgent`
- [ ] 升级 `RiskAgent` 为 DD 问题生成器
- [ ] 编写 Agent 单元测试

### Phase 3: 服务集成（2-3天）
- [ ] 集成 LLM Gateway 的文件解析能力
- [ ] 集成 External Data Service
- [ ] 集成 Web Search Service
- [ ] 集成 Internal Knowledge Service
- [ ] 实现交叉验证逻辑

### Phase 4: 测试与调优（2天）
- [ ] 运行集成测试（里程碑测试）
- [ ] 调试和修复问题
- [ ] 性能优化
- [ ] 文档更新

**总计**: 9-12 天

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 解析 BP 准确率低 | 高 | 1. 使用结构化 Prompt；2. 增加验证步骤；3. 保留人工修正接口 |
| 外部 API（天眼查）限流 | 中 | 1. 实现缓存；2. 降级方案（仅用 Web Search） |
| Tavily 搜索返回不相关结果 | 中 | 1. 优化查询构建；2. 增加相关性过滤 |
| 工作流执行时间过长 | 中 | 1. 异步并行执行 TDD 和 MDD；2. 实现进度条 |
| WebSocket 连接不稳定 | 低 | 1. 实现会话持久化；2. 提供 HTTP 恢复接口 |

---

## 10. 附录

### 10.1 示例 BP 解析输出

```json
{
  "company_name": "智算科技",
  "founding_date": "2023-03",
  "team": [
    {
      "name": "张三",
      "title": "CEO",
      "background": "前阿里巴巴 P9，10年云计算经验"
    },
    {
      "name": "李四",
      "title": "CTO",
      "background": "清华大学博士，AI 领域专家"
    }
  ],
  "product_description": "基于大模型的企业知识管理平台...",
  "market_size_tam": "中国企业 SaaS 市场 2025 年预计达到 1000 亿元",
  "target_market": "中大型企业",
  "competitors": ["飞书", "钉钉", "企业微信"],
  "funding_request": "A 轮融资 3000 万元",
  "current_valuation": "投前估值 2 亿元"
}
```

### 10.2 示例团队分析输出

```json
{
  "summary": "智算科技的创始团队在云计算和 AI 领域具有深厚的技术背景。CEO 张三在阿里巴巴的 P9 级别证明了其在大型互联网公司的管理能力，而 CTO 李四的清华博士背景为产品的技术壁垒提供了保障。然而，团队在企业 SaaS 销售方面的经验相对薄弱，这可能影响早期的市场拓展速度。",
  "strengths": [
    "技术实力雄厚，CEO 和 CTO 均来自一线互联网公司或顶尖高校",
    "团队在目标领域（AI + 企业服务）有直接相关经验",
    "创始人之间有长期合作基础（根据 LinkedIn 显示，两人曾在同一项目组）"
  ],
  "concerns": [
    "缺乏企业级 SaaS 销售和 BD 背景的核心成员",
    "BP 中未提及 CFO 或运营负责人，团队结构不完整",
    "李四博士毕业仅 2 年，实际工程落地经验有待验证"
  ],
  "experience_match_score": 7.5,
  "data_sources": [
    "BP 第 5-6 页团队介绍",
    "LinkedIn 公开信息",
    "36氪报道：《阿里 P9 张三创业，瞄准企业知识管理》"
  ]
}
```

### 10.3 示例 DD 问题清单

```json
[
  {
    "category": "Team",
    "question": "BP 提到 CTO 李四是'AI 领域专家'，请提供其博士期间的具体研究方向、发表论文列表，以及在工业界落地的项目案例。",
    "reasoning": "'AI 专家'是一个宽泛的描述，需要验证其技术能力是否与产品需求匹配（知识图谱、NLP 等）。",
    "bp_reference": "第 5 页，CTO 介绍"
  },
  {
    "category": "Market",
    "question": "BP 声称'中国企业 SaaS 市场 2025 年达到 1000 亿'，请说明该数据来源，以及你们定义的 TAM 中，有多少比例是你们的可服务市场（SAM）？",
    "reasoning": "市场规模数据需要可靠来源，且 TAM 通常被过度乐观估计。",
    "bp_reference": "第 8 页，市场规模"
  },
  {
    "category": "Product",
    "question": "产品 Demo 中展示的'智能问答'功能，其背后使用的是自研模型还是调用第三方 API（如 OpenAI、文心一言）？如果是自研，请提供模型参数量、训练数据规模和准确率基准测试结果。",
    "reasoning": "技术壁垒的真实性直接影响估值。如果仅是 API 封装，护城河较弱。",
    "bp_reference": "第 12 页，核心技术"
  },
  {
    "category": "Financial",
    "question": "财务预测显示第二年收入增长 300%，请详细说明假设的客户获取成本（CAC）、客户生命周期价值（LTV）、销售周期长度，以及支撑这一增长的具体销售策略和团队配置。",
    "reasoning": "SaaS 的增长严重依赖单位经济模型，需要验证假设的合理性。",
    "bp_reference": "第 15 页，财务预测"
  },
  {
    "category": "Risk",
    "question": "你们将飞书、钉钉列为竞品，但这些产品已有庞大的用户基础。请说明你们的差异化优势，以及为什么大企业会愿意切换到一个新平台（考虑迁移成本）？",
    "reasoning": "与巨头的正面竞争是最大风险，需要清晰的差异化策略。",
    "bp_reference": "第 10 页，竞品分析"
  }
]
```

---

## 11. 总结

本技术设计文档为 Sprint 3 的开发提供了完整的蓝图。核心要点：

1. **清晰的状态机**: DD 工作流被拆解为 7 个明确的状态
2. **模块化 Agent**: TeamAnalysisAgent 和 MarketAnalysisAgent 各司其职
3. **强类型系统**: 所有数据流都有 Pydantic 模型定义
4. **可测试性**: 每个模块都有对应的单元测试和集成测试
5. **用户可见性**: 通过 WebSocket 实时推送工作流进度

**下一步**: 根据本设计文档，开始 Phase 1 的开发工作。
