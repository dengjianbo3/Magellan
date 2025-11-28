# V2 vs V3 架构对比速查表

**用途**: 快速理解 Sprint 3 重构的核心变化

---

## 📊 一图看懂核心变化

```
V2 (二级市场)                      V3 (一级市场)
┌──────────────┐                  ┌──────────────┐
│   输入: AAPL │                  │ 输入: BP.pdf │
└──────┬───────┘                  └──────┬───────┘
       │                                 │
       ↓                                 ↓
┌──────────────────┐             ┌─────────────────┐
│ yfinance API     │             │ LLM 解析 BP     │
│ (股票数据)       │             │ (提取结构化信息)│
└──────┬───────────┘             └──────┬──────────┘
       │                                 │
       ↓                                 ↓
┌──────────────────┐             ┌─────────────────┐
│ AnalysisAgent    │             │ TeamAnalysisAgent│
│ (生成公司简介)   │             │ + External Data │
└──────┬───────────┘             │ + Web Search    │
       │                         └──────┬──────────┘
       ↓                                │
┌──────────────────┐                   ↓
│ RiskAgent        │             ┌─────────────────┐
│ (追问问题)       │             │MarketAnalysisAgent│
└──────┬───────────┘             │ + Web Search    │
       │                         │ + Internal KB   │
       ↓                         └──────┬──────────┘
┌──────────────────┐                   │
│ 股票投资报告     │                   ↓
└──────────────────┘             ┌─────────────────┐
                                 │ RiskAgent       │
                                 │ (DD问题清单)    │
                                 └──────┬──────────┘
                                        │
                                        ↓
                                 ┌─────────────────┐
                                 │ 投资备忘录(IM)  │
                                 └─────────────────┘
```

---

## 🔄 API 接口对比

### V2: `/ws/start_analysis`

**输入**:
```json
{
  "ticker": "AAPL",
  "user_id": "investor_001"
}
```

**输出 (简化)**:
```json
{
  "session_id": "session_AAPL_xxx",
  "status": "completed",
  "preliminary_report": {
    "company_ticker": "AAPL",
    "report_sections": [
      {"section_title": "初步分析", "content": "苹果公司是..."}
    ]
  },
  "key_questions": [
    "公司如何应对中国市场的竞争？"
  ]
}
```

---

### V3: `/ws/start_dd_analysis`

**输入**:
```json
{
  "company_name": "智算科技",
  "bp_file_base64": "JVBERi0xLjQKJeLjz9...",  // Base64 编码的 PDF
  "user_id": "investor_001"
}
```

**输出 (简化)**:
```json
{
  "session_id": "dd_session_xxx",
  "status": "completed",
  "preliminary_im": {
    "company_name": "智算科技",
    "team_section": {
      "summary": "团队在 AI 领域有深厚背景...",
      "strengths": ["技术实力强", "有大厂经验"],
      "concerns": ["缺乏销售经验"],
      "experience_match_score": 7.5
    },
    "market_section": {
      "summary": "企业 SaaS 市场规模验证...",
      "market_validation": "BP 声称的 1000 亿市场基本合理...",
      "competitive_landscape": "面临飞书、钉钉等巨头竞争..."
    }
  },
  "dd_questions": [
    {
      "category": "Team",
      "question": "请提供 CTO 李四的博士论文和发表论文列表。",
      "reasoning": "验证其 AI 技术能力",
      "bp_reference": "第 5 页"
    }
  ]
}
```

---

## 📦 数据模型对比

### V2 核心模型

```python
class AnalysisRequest(BaseModel):
    ticker: str

class ReportSection(BaseModel):
    section_title: str
    content: str

class FullReportResponse(BaseModel):
    company_ticker: str
    report_sections: List[ReportSection]
    financial_chart_data: Optional[FinancialChartData]
```

---

### V3 核心模型

```python
class DDAnalysisRequest(BaseModel):
    company_name: str
    bp_file: UploadFile
    user_id: str

class BPStructuredData(BaseModel):
    company_name: str
    team: List[TeamMember]
    product_description: str
    market_size_tam: str
    # ... 更多字段

class TeamAnalysisOutput(BaseModel):
    summary: str
    strengths: List[str]
    concerns: List[str]
    experience_match_score: float  # 0-10
    data_sources: List[str]

class MarketAnalysisOutput(BaseModel):
    summary: str
    market_validation: str
    competitive_landscape: str
    red_flags: List[str]

class DDQuestion(BaseModel):
    category: str  # Team/Market/Product/Financial/Risk
    question: str
    reasoning: str
    bp_reference: Optional[str]

class PreliminaryIM(BaseModel):
    company_name: str
    team_section: TeamAnalysisOutput
    market_section: MarketAnalysisOutput
    dd_questions: List[DDQuestion]
```

---

## 🔀 工作流对比

### V2 工作流 (5 步)

```
Step 0: 获取用户画像 (UserService)
Step 1: 获取公司数据 (ExternalData - yfinance)
Step 2: LLM 生成初步分析
Step 3: 获取财务数据（可选）
Step 4: 生成追问问题
Step 5: HITL 审核
```

---

### V3 工作流 (7 步)

```
Step 0: 获取机构偏好 (UserService - 预留)
Step 1: 解析 BP (LLM Gateway 文件理解)
        ↓
        提取结构化数据: 团队/市场/产品/财务
        
Step 2: 团队尽调 (TDD)
        ├─ ExternalData: 查询工商/LinkedIn
        ├─ WebSearch: 搜索团队背景
        └─ TeamAnalysisAgent: 综合分析
        
Step 3: 市场尽调 (MDD) [可与 Step 2 并行]
        ├─ WebSearch: 验证市场规模
        ├─ InternalKnowledge: 查询历史项目
        └─ MarketAnalysisAgent: 市场分析
        
Step 4: 交叉验证
        └─ 对比 BP 数据与外部数据，识别不一致
        
Step 5: 生成 DD 问题清单
        └─ RiskAgent: 基于分析结果生成专业问题
        
Step 6: HITL 审核
        └─ 投资负责人审核并补充访谈纪要
```

---

## 🧠 Agent 对比

### V2 Agents

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **AnalysisAgent** | 生成公司简介 | 公开数据 | 文本描述 |
| **RiskAgent** | 生成追问问题 | 公司简介 | 问题列表 |

---

### V3 Agents

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **BPParser** | 解析 BP | PDF 文件 | `BPStructuredData` |
| **TeamAnalysisAgent** | 团队尽调 | BP团队信息 + 外部数据 + 搜索结果 | `TeamAnalysisOutput` |
| **MarketAnalysisAgent** | 市场尽调 | BP市场信息 + 搜索结果 + 内部洞察 | `MarketAnalysisOutput` |
| **RiskAgent** (升级) | 生成DD清单 | 团队分析 + 市场分析 + BP数据 | `List[DDQuestion]` |

---

## 🔌 外部服务依赖对比

### V2 依赖

```
report_orchestrator
├─ llm_gateway (Gemini)
├─ external_data_service (yfinance - 二级市场)
└─ user_service (个人投资风格)
```

---

### V3 依赖

```
report_orchestrator
├─ llm_gateway (Gemini + File API)
├─ external_data_service (天眼查/LinkedIn - 一级市场)
├─ web_search_service (Tavily)
├─ internal_knowledge_service (ChromaDB + Embeddings)
└─ user_service (机构投资偏好)
```

---

## 🎯 输出质量对比

### V2 输出示例

```
【初步分析】
苹果公司是一家全球领先的科技公司，主要业务包括iPhone、Mac、iPad等硬件产品。
公司在2023年Q4实现营收xxx亿美元，同比增长x%。

【关键问题】
1. 公司如何应对中国市场的竞争？
2. iPhone 销量下滑是否影响长期增长？
3. 服务业务的增长可持续吗？
```

**特点**: 通用、描述性、适合快速了解

---

### V3 输出示例

```
【团队分析】
摘要: 智算科技的创始团队在云计算和 AI 领域具有深厚的技术背景。CEO 张三...

优势:
✓ 技术实力雄厚，CEO 和 CTO 均来自一线互联网公司
✓ 团队在 AI + 企业服务领域有直接相关经验
✓ 创始人之间有长期合作基础

担忧:
⚠ 缺乏企业级 SaaS 销售和 BD 背景的核心成员
⚠ 团队结构不完整，未提及 CFO

经验匹配度: 7.5/10

数据来源: BP 第 5-6 页、LinkedIn、36氪报道

【市场分析】
市场验证: BP 声称的"中国企业 SaaS 市场 2025 年 1000 亿"基本合理，但需注意...
竞争格局: 面临飞书、钉钉等巨头竞争，差异化策略关键在于...

【DD 问题清单】
[Team] 请提供 CTO 李四的博士论文列表，验证其 AI 技术能力是否匹配产品需求。
       (原因: BP 第 5 页描述模糊，需具体验证)
       
[Market] BP 第 8 页称市场规模 1000 亿，请说明数据来源及可服务市场(SAM)比例。
         (原因: TAM 常被过度乐观估计)
         
[Financial] 财务预测显示第二年收入增长 300%，请详细说明 CAC、LTV、销售周期。
            (原因: SaaS 增长依赖单位经济模型)
```

**特点**: 专业、结构化、可操作、有数据支撑

---

## ⚡ 性能对比

| 指标 | V2 | V3 | 备注 |
|------|----|----|------|
| **平均完成时间** | 30-60 秒 | 3-5 分钟 | V3 更复杂，但并行优化后可控 |
| **LLM 调用次数** | 2-3 次 | 5-7 次 | V3 多个 Agent |
| **外部 API 调用** | 1-2 次 | 4-6 次 | V3 集成更多数据源 |
| **并发能力** | 10+ | 3-5 | V3 每个会话更重 |

---

## 📂 文件结构对比

### V2 结构
```
backend/services/report_orchestrator/
├── app/
│   ├── main.py (390 行，包含所有逻辑)
│   ├── models/
│   ├── core/
│   └── services/
└── tests/
```

---

### V3 结构
```
backend/services/report_orchestrator/
├── app/
│   ├── main.py (WebSocket 端点)
│   ├── models/
│   │   └── dd_models.py (新增)
│   ├── core/
│   │   └── dd_state_machine.py (新增)
│   ├── agents/ (新增)
│   │   ├── team_analysis_agent.py
│   │   ├── market_analysis_agent.py
│   │   └── risk_agent.py
│   ├── parsers/ (新增)
│   │   └── bp_parser.py
│   └── services/
└── tests/
    ├── test_dd_models.py
    ├── test_dd_state_machine.py
    ├── test_team_analysis_agent.py
    ├── test_market_analysis_agent.py
    └── test_dd_workflow_integration.py
```

---

## 🚦 迁移策略

### 保留 V2 端点
```python
# 保持向后兼容
@app.websocket("/ws/start_analysis")  # V2 - 保留
@app.websocket("/ws/start_dd_analysis")  # V3 - 新增
```

### 逐步迁移前端
1. V2 端点继续服务旧的股票分析功能（如有需要）
2. 新的 DD 功能使用 V3 端点
3. 前端路由隔离：`/analysis/stock` vs `/analysis/dd`

---

## 📚 相关文档

- **技术设计**: `docs/Sprint3_Technical_Design.md`
- **任务清单**: `docs/Sprint3_Task_Checklist.md`
- **V3 设计文档**: `docs/AI_Investment_Agent_V3_Design.md`
- **V3 开发计划**: `docs/MVP_V3_Development_Plan.md`

---

**最后更新**: 2025-10-22
