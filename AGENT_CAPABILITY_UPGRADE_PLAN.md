# Agent 能力升级方案

## 一、现状分析

### 当前Agent工具配置

| Agent | 现有工具 | 能力局限 |
|-------|---------|---------|
| **Leader** | tavily_search, KB, end_meeting | 缺乏数据汇总能力，无法生成可视化 |
| **MarketAnalyst** | tavily, YF, SEC, KB | 缺乏中国市场数据，无行业数据库 |
| **FinancialExpert** | tavily, YF, SEC, KB | 缺乏估值模型计算，无财务建模工具 |
| **TeamEvaluator** | tavily, KB | 缺乏LinkedIn/企查查数据，背景调查能力弱 |
| **RiskAssessor** | tavily, SEC, KB | 缺乏舆情监控，无实时风险警报 |
| **TechSpecialist** | tavily, KB | 缺乏GitHub/专利数据库，无代码分析能力 |
| **LegalAdvisor** | tavily, KB | 缺乏法规数据库，无判例检索能力 |
| **TechnicalAnalyst** | technical_analysis, tavily | 已较完善，可增加更多交易所数据 |

---

## 二、升级方案总览

### 新增工具/MCP分类

```
1. 数据源类工具 (Data Source Tools)
   - 中国市场数据
   - 全球行业数据库
   - 专利/知识产权数据库
   - 企业工商信息

2. 分析计算类工具 (Analysis Tools)
   - 财务建模工具
   - 估值计算器
   - 风险量化工具

3. 背景调查类工具 (Investigation Tools)
   - 人员背景调查
   - 企业关联图谱
   - 舆情监控

4. 专业数据库类工具 (Database Tools)
   - 法规判例库
   - 专利检索
   - GitHub/开源项目分析

5. 可视化输出工具 (Visualization Tools)
   - 图表生成
   - 报告模板
```

---

## 三、各Agent详细升级方案

### 1. Leader（主持人）

**升级目标**: 增强综合能力，支持动态议程调整和报告生成

#### 新增工具

| 工具名称 | 功能 | 优先级 |
|---------|------|-------|
| `generate_summary_chart` | 生成汇总图表（雷达图、对比表） | P1 |
| `export_meeting_report` | 导出会议纪要为结构化报告 | P1 |
| `check_discussion_coverage` | 检查讨论覆盖度（哪些领域未充分讨论） | P2 |

#### 实现方式
```python
# 新增工具定义
class SummaryChartTool(Tool):
    """生成投资分析汇总图表"""
    name = "generate_summary_chart"

    async def execute(self, chart_type: str, data: dict) -> dict:
        """
        chart_type: radar/comparison/timeline
        data: 各维度评分数据
        返回: 图表URL或Base64
        """
```

---

### 2. MarketAnalyst（市场分析师）

**升级目标**: 增强中国/全球市场数据获取能力，支持行业深度研究

#### 新增工具

| 工具名称 | 功能 | 数据源 | 优先级 |
|---------|------|-------|-------|
| `china_market_data` | 中国A股/港股数据 | 东方财富/同花顺API | P1 |
| `industry_report` | 行业研究报告 | 艾瑞/36Kr/CB Insights | P1 |
| `company_competitors` | 竞争对手分析 | Crunchbase/企查查 | P1 |
| `market_size_calculator` | TAM/SAM/SOM计算器 | 自研 | P2 |
| `trend_analyzer` | 行业趋势分析 | Google Trends + 社交媒体 | P2 |

#### MCP集成建议
```yaml
# 推荐MCP服务
mcp_servers:
  - name: "financial-data"
    source: "yfinance + eastmoney"
    capabilities: ["stock_quote", "financial_statement", "market_cap"]

  - name: "industry-research"
    source: "crunchbase API"
    capabilities: ["company_profile", "funding_rounds", "competitors"]
```

#### 实现示例
```python
class ChinaMarketDataTool(Tool):
    """获取中国市场数据（A股/港股）"""
    name = "china_market_data"

    async def execute(
        self,
        symbol: str,           # 股票代码 如 "600519" 或 "00700"
        market: str = "A",     # A股/港股/美股
        data_type: str = "quote"  # quote/history/financial/news
    ) -> dict:
        """
        返回:
        - 实时行情
        - 历史K线
        - 财务报表
        - 相关新闻
        """
```

---

### 3. FinancialExpert（财务专家）

**升级目标**: 增强估值建模能力，支持自动化财务分析

#### 新增工具

| 工具名称 | 功能 | 优先级 |
|---------|------|-------|
| `dcf_calculator` | DCF现金流折现估值 | P1 |
| `comparable_analysis` | 可比公司法估值 | P1 |
| `financial_ratio_analyzer` | 财务比率自动计算和对标 | P1 |
| `earnings_quality_check` | 盈余质量检测（是否有财务造假迹象） | P2 |
| `cash_flow_forecast` | 现金流预测模型 | P2 |

#### 实现示例
```python
class DCFCalculatorTool(Tool):
    """DCF现金流折现估值工具"""
    name = "dcf_calculator"

    async def execute(
        self,
        revenue_growth: list,      # 未来5年营收增长率
        operating_margin: float,   # 营业利润率
        tax_rate: float,           # 税率
        capex_ratio: float,        # 资本支出占比
        wacc: float,               # 加权平均资本成本
        terminal_growth: float     # 永续增长率
    ) -> dict:
        """
        返回:
        - 企业价值 (EV)
        - 股权价值
        - 每股估值
        - 敏感性分析表
        """
```

```python
class ComparableAnalysisTool(Tool):
    """可比公司法估值"""
    name = "comparable_analysis"

    async def execute(
        self,
        target_company: str,
        comparable_companies: list,  # 可比公司列表
        metrics: list = ["P/E", "P/S", "EV/EBITDA", "P/B"]
    ) -> dict:
        """
        返回:
        - 可比公司估值倍数
        - 行业中位数/平均数
        - 目标公司隐含估值区间
        """
```

---

### 4. TeamEvaluator（团队评估师）

**升级目标**: 增强背景调查能力，支持深度人员分析

#### 新增工具

| 工具名称 | 功能 | 数据源 | 优先级 |
|---------|------|-------|-------|
| `linkedin_profile` | LinkedIn人员档案 | LinkedIn API/爬虫 | P1 |
| `qichacha_search` | 企查查/天眼查企业信息 | 企查查API | P1 |
| `founder_track_record` | 创始人历史项目追踪 | Crunchbase + 新闻 | P1 |
| `team_stability_analyzer` | 团队稳定性分析（离职率等） | 脉脉/Boss直聘数据 | P2 |
| `key_person_risk` | 关键人风险评估 | 综合数据 | P2 |

#### MCP集成建议
```yaml
mcp_servers:
  - name: "people-intelligence"
    capabilities:
      - linkedin_search
      - employment_history
      - education_verification
      - social_presence

  - name: "company-registry"
    source: "qichacha/tianyancha"
    capabilities:
      - company_info
      - shareholders
      - legal_representatives
      - related_companies
```

#### 实现示例
```python
class QichaChaTool(Tool):
    """企查查/天眼查企业信息查询"""
    name = "qichacha_search"

    async def execute(
        self,
        company_name: str,
        query_type: str = "basic"  # basic/shareholders/history/legal
    ) -> dict:
        """
        返回:
        - 企业基本信息（注册资本、成立日期、法人）
        - 股权结构
        - 变更历史
        - 法律诉讼
        - 关联企业图谱
        """
```

---

### 5. RiskAssessor（风险评估师）

**升级目标**: 增强实时风险监控和量化分析能力

#### 新增工具

| 工具名称 | 功能 | 优先级 |
|---------|------|-------|
| `sentiment_monitor` | 舆情监控（负面新闻实时追踪） | P1 |
| `risk_scoring_model` | 风险量化评分模型 | P1 |
| `regulatory_alert` | 监管政策变化预警 | P1 |
| `black_swan_scanner` | 黑天鹅事件扫描 | P2 |
| `supply_chain_risk` | 供应链风险分析 | P2 |
| `geopolitical_risk` | 地缘政治风险评估 | P2 |

#### 实现示例
```python
class SentimentMonitorTool(Tool):
    """舆情监控工具"""
    name = "sentiment_monitor"

    async def execute(
        self,
        company_name: str,
        keywords: list = None,
        time_range: str = "7d",  # 1d/7d/30d/90d
        sources: list = ["news", "social", "forum"]
    ) -> dict:
        """
        返回:
        - 舆情热度趋势
        - 负面事件列表
        - 情感分析得分
        - 风险等级预警
        """
```

```python
class RiskScoringTool(Tool):
    """风险量化评分模型"""
    name = "risk_scoring_model"

    async def execute(
        self,
        risk_factors: dict  # 各类风险因子评分
    ) -> dict:
        """
        输入:
        {
            "market_risk": {"score": 7, "weight": 0.2},
            "tech_risk": {"score": 5, "weight": 0.15},
            "team_risk": {"score": 6, "weight": 0.15},
            "financial_risk": {"score": 8, "weight": 0.2},
            "legal_risk": {"score": 3, "weight": 0.15},
            "operational_risk": {"score": 5, "weight": 0.15}
        }

        返回:
        - 综合风险得分
        - 风险等级 (低/中/高/极高)
        - 风险矩阵可视化数据
        - 关键风险因子排序
        """
```

---

### 6. TechSpecialist（技术专家）

**升级目标**: 增强技术深度分析能力，支持代码和专利评估

#### 新增工具

| 工具名称 | 功能 | 数据源 | 优先级 |
|---------|------|-------|-------|
| `github_analyzer` | GitHub项目分析 | GitHub API | P1 |
| `patent_search` | 专利检索和分析 | Google Patents/WIPO | P1 |
| `tech_stack_detector` | 技术栈检测 | BuiltWith/Wappalyzer | P1 |
| `open_source_scanner` | 开源依赖风险扫描 | Snyk/OSS Index | P2 |
| `tech_talent_market` | 技术人才市场分析 | StackOverflow/GitHub | P2 |

#### MCP集成建议
```yaml
mcp_servers:
  - name: "github-mcp"
    capabilities:
      - repo_analysis       # 仓库分析（Star/Fork/Contributors）
      - code_quality       # 代码质量评估
      - commit_activity    # 提交活跃度
      - contributor_profile # 贡献者背景

  - name: "patent-search"
    source: "Google Patents API"
    capabilities:
      - patent_search      # 专利检索
      - citation_analysis  # 引用分析
      - patent_family      # 专利族分析
```

#### 实现示例
```python
class GitHubAnalyzerTool(Tool):
    """GitHub项目分析工具"""
    name = "github_analyzer"

    async def execute(
        self,
        repo_url: str = None,
        organization: str = None,
        analysis_type: str = "full"  # full/activity/contributors/quality
    ) -> dict:
        """
        返回:
        - 仓库基本信息 (stars, forks, issues)
        - 提交活跃度趋势
        - 代码语言分布
        - 主要贡献者分析
        - 代码质量指标
        - 开源依赖列表
        """
```

```python
class PatentSearchTool(Tool):
    """专利检索分析工具"""
    name = "patent_search"

    async def execute(
        self,
        company_name: str = None,
        inventor: str = None,
        keywords: list = None,
        patent_office: str = "all"  # USPTO/EPO/CNIPA/all
    ) -> dict:
        """
        返回:
        - 专利列表
        - 专利数量趋势
        - 技术领域分布
        - 引用被引分析
        - 竞争对手专利对比
        """
```

---

### 7. LegalAdvisor（法律顾问）

**升级目标**: 增强法规检索和判例分析能力

#### 新增工具

| 工具名称 | 功能 | 数据源 | 优先级 |
|---------|------|-------|-------|
| `regulation_database` | 法规数据库查询 | 北大法宝/威科先行 | P1 |
| `case_law_search` | 判例检索 | 中国裁判文书网/Westlaw | P1 |
| `compliance_checker` | 合规性检查清单 | 自研规则引擎 | P1 |
| `regulatory_news` | 监管动态追踪 | 官方网站+新闻 | P2 |
| `contract_analyzer` | 合同条款分析 | NLP模型 | P2 |

#### 实现示例
```python
class RegulationDatabaseTool(Tool):
    """法规数据库查询"""
    name = "regulation_database"

    async def execute(
        self,
        keywords: list,
        jurisdiction: str = "CN",  # CN/US/EU/HK
        law_type: str = "all",     # all/law/regulation/judicial
        effective_only: bool = True
    ) -> dict:
        """
        返回:
        - 相关法规列表
        - 法规全文/摘要
        - 最新修订版本
        - 相关司法解释
        """
```

```python
class ComplianceCheckerTool(Tool):
    """合规性检查清单"""
    name = "compliance_checker"

    async def execute(
        self,
        industry: str,          # fintech/healthcare/crypto/ecommerce
        business_model: str,
        operating_regions: list
    ) -> dict:
        """
        返回:
        - 必需资质清单
        - 合规要求列表
        - 常见法律风险
        - 监管重点关注领域
        - 建议行动项
        """
```

---

### 8. TechnicalAnalyst（技术分析师）

**升级目标**: 扩展数据源，增强多市场支持

#### 新增工具

| 工具名称 | 功能 | 数据源 | 优先级 |
|---------|------|-------|-------|
| `multi_exchange_data` | 多交易所数据 | Binance/OKX/Coinbase | P1 |
| `orderbook_analyzer` | 订单簿深度分析 | 交易所API | P2 |
| `whale_tracker` | 大户/鲸鱼追踪 | 链上数据 | P2 |
| `correlation_analyzer` | 相关性分析 | 自研 | P2 |
| `backtester` | 策略回测 | 自研 | P3 |

#### 实现示例
```python
class MultiExchangeDataTool(Tool):
    """多交易所数据聚合"""
    name = "multi_exchange_data"

    async def execute(
        self,
        symbol: str,
        exchanges: list = ["binance", "okx", "coinbase"],
        data_type: str = "price"  # price/volume/funding
    ) -> dict:
        """
        返回:
        - 多交易所价格对比
        - 价差套利机会
        - 成交量分布
        - 资金费率对比
        """
```

---

## 四、MCP服务器架构建议

### 推荐MCP服务器列表

```yaml
# mcp_config.yaml

mcp_servers:
  # 1. 金融数据服务
  - name: financial-data-mcp
    description: "统一金融数据接口"
    tools:
      - china_stock_data      # A股数据
      - hk_stock_data         # 港股数据
      - us_stock_data         # 美股数据 (已有Yahoo Finance)
      - crypto_data           # 加密货币数据
      - forex_data            # 外汇数据
    config:
      eastmoney_api_key: "${EASTMONEY_API_KEY}"

  # 2. 企业信息服务
  - name: company-intelligence-mcp
    description: "企业信息和背景调查"
    tools:
      - qichacha_search       # 企查查
      - tianyancha_search     # 天眼查
      - crunchbase_search     # Crunchbase
      - linkedin_search       # LinkedIn
    config:
      qichacha_api_key: "${QICHACHA_API_KEY}"
      crunchbase_api_key: "${CRUNCHBASE_API_KEY}"

  # 3. 法规和知识产权服务
  - name: legal-ip-mcp
    description: "法规数据库和知识产权"
    tools:
      - regulation_search     # 法规检索
      - case_law_search       # 判例检索
      - patent_search         # 专利检索
      - trademark_search      # 商标检索
    config:
      google_patents_key: "${GOOGLE_PATENTS_KEY}"

  # 4. 技术分析服务
  - name: tech-analysis-mcp
    description: "代码和技术分析"
    tools:
      - github_analyzer       # GitHub分析
      - tech_stack_detector   # 技术栈检测
      - npm_package_analyzer  # NPM包分析
      - docker_image_analyzer # Docker镜像分析
    config:
      github_token: "${GITHUB_TOKEN}"

  # 5. 舆情和风险监控服务
  - name: risk-monitoring-mcp
    description: "舆情监控和风险预警"
    tools:
      - sentiment_monitor     # 舆情监控
      - news_aggregator       # 新闻聚合
      - social_listener       # 社交媒体监听
      - regulatory_alert      # 监管预警
    config:
      newsapi_key: "${NEWSAPI_KEY}"
```

---

## 五、实施路线图

### Phase 1: 核心数据源升级 (2周)

| 任务 | Agent | 工具 | 工作量 |
|-----|-------|------|-------|
| 中国市场数据 | MarketAnalyst, FinancialExpert | china_market_data | 3天 |
| 企查查集成 | TeamEvaluator | qichacha_search | 2天 |
| 专利检索 | TechSpecialist | patent_search | 2天 |
| GitHub分析 | TechSpecialist | github_analyzer | 2天 |
| 舆情监控 | RiskAssessor | sentiment_monitor | 3天 |

### Phase 2: 分析计算工具 (2周)

| 任务 | Agent | 工具 | 工作量 |
|-----|-------|------|-------|
| DCF估值计算器 | FinancialExpert | dcf_calculator | 3天 |
| 可比公司分析 | FinancialExpert | comparable_analysis | 2天 |
| 风险量化模型 | RiskAssessor | risk_scoring_model | 3天 |
| 合规检查器 | LegalAdvisor | compliance_checker | 3天 |
| 汇总图表生成 | Leader | generate_summary_chart | 2天 |

### Phase 3: MCP服务化 (2周)

| 任务 | 描述 | 工作量 |
|-----|------|-------|
| MCP服务器框架 | 搭建MCP服务器基础架构 | 3天 |
| financial-data-mcp | 金融数据MCP服务 | 3天 |
| company-intelligence-mcp | 企业信息MCP服务 | 3天 |
| 集成测试 | 全链路测试 | 3天 |

### Phase 4: 高级功能 (2周)

| 任务 | Agent | 工具 | 工作量 |
|-----|-------|------|-------|
| LinkedIn集成 | TeamEvaluator | linkedin_profile | 3天 |
| 法规数据库 | LegalAdvisor | regulation_database | 3天 |
| 多交易所数据 | TechnicalAnalyst | multi_exchange_data | 2天 |
| 订单簿分析 | TechnicalAnalyst | orderbook_analyzer | 2天 |
| 黑天鹅扫描 | RiskAssessor | black_swan_scanner | 2天 |

---

## 六、技术实现要点

### 6.1 工具注册机制扩展

```python
# mcp_tools.py 扩展

def create_mcp_tools_for_agent(agent_role: str, scenario: str = None) -> List[Tool]:
    """
    根据Agent角色和场景动态创建工具集

    Args:
        agent_role: Agent角色名称
        scenario: 分析场景 (early_stage/growth/public_market/crypto)
    """
    tools = []

    # 基础工具（所有Agent）
    tools.append(TavilySearchTool())
    tools.append(KnowledgeBaseTool())

    # 角色特定工具
    if agent_role == "MarketAnalyst":
        tools.extend([
            YahooFinanceTool(),
            SECEdgarTool(),
            ChinaMarketDataTool(),     # 新增
            IndustryReportTool(),       # 新增
            CompanyCompetitorsTool(),   # 新增
        ])

    elif agent_role == "FinancialExpert":
        tools.extend([
            YahooFinanceTool(),
            SECEdgarTool(),
            DCFCalculatorTool(),        # 新增
            ComparableAnalysisTool(),   # 新增
            FinancialRatioTool(),       # 新增
        ])

    elif agent_role == "TeamEvaluator":
        tools.extend([
            QichaChaTool(),             # 新增
            LinkedInProfileTool(),      # 新增
            FounderTrackRecordTool(),   # 新增
        ])

    elif agent_role == "RiskAssessor":
        tools.extend([
            SECEdgarTool(),
            SentimentMonitorTool(),     # 新增
            RiskScoringTool(),          # 新增
            RegulatoryAlertTool(),      # 新增
        ])

    elif agent_role == "TechSpecialist":
        tools.extend([
            GitHubAnalyzerTool(),       # 新增
            PatentSearchTool(),         # 新增
            TechStackDetectorTool(),    # 新增
        ])

    elif agent_role == "LegalAdvisor":
        tools.extend([
            RegulationDatabaseTool(),   # 新增
            CaseLawSearchTool(),        # 新增
            ComplianceCheckerTool(),    # 新增
        ])

    elif agent_role == "TechnicalAnalyst":
        tools.extend([
            TechnicalAnalysisTool(),
            MultiExchangeDataTool(),    # 新增
        ])

    elif agent_role == "Leader":
        tools.extend([
            SummaryChartTool(),         # 新增
            DiscussionCoverageTool(),   # 新增
        ])

    return tools
```

### 6.2 MCP客户端集成

```python
# mcp_client.py

class MCPClient:
    """MCP服务客户端"""

    def __init__(self, config_path: str = "mcp_config.yaml"):
        self.config = self._load_config(config_path)
        self.servers = {}

    async def connect(self, server_name: str):
        """连接到MCP服务器"""
        if server_name not in self.servers:
            server_config = self.config.get(server_name)
            self.servers[server_name] = await self._create_connection(server_config)
        return self.servers[server_name]

    async def call_tool(self, server_name: str, tool_name: str, **params):
        """调用MCP工具"""
        server = await self.connect(server_name)
        return await server.call_tool(tool_name, params)
```

---

## 七、API密钥和服务依赖

### 需要的API密钥

| 服务 | 用途 | 获取方式 | 估计成本 |
|-----|------|---------|---------|
| Tavily | 网络搜索 | 已有 | $50/月 |
| Yahoo Finance | 股票数据 | 免费 | 免费 |
| SEC EDGAR | 美股财报 | 免费 | 免费 |
| 东方财富/同花顺 | A股数据 | 申请API | ¥500/月 |
| 企查查/天眼查 | 企业信息 | 申请API | ¥2000/月 |
| Crunchbase | 全球公司 | 申请API | $99/月 |
| GitHub | 代码分析 | 免费Token | 免费 |
| Google Patents | 专利检索 | 申请API | 免费 |
| NewsAPI | 新闻聚合 | 申请API | $49/月 |

---

## 八、预期效果

### 升级前后对比

| 维度 | 升级前 | 升级后 |
|-----|-------|-------|
| **数据覆盖** | 主要依赖网络搜索 | 结构化数据源+网络搜索 |
| **中国市场** | 几乎无法获取 | A股/港股完整数据 |
| **背景调查** | 浅层搜索 | 深度企业+人员调查 |
| **财务分析** | 依赖BP文档 | 自动估值+财务建模 |
| **风险评估** | 定性分析 | 量化评分+实时监控 |
| **技术评估** | 依赖描述 | 代码+专利实证分析 |
| **法律合规** | 通用搜索 | 专业法规库+判例库 |
| **分析时间** | 15-20分钟 | 10-15分钟（数据获取更快） |
| **准确性** | 中等 | 显著提升 |

---

## 九、风险和注意事项

1. **API成本控制**: 建议实施调用限流和缓存机制
2. **数据合规**: 企查查/天眼查数据使用需注意合规
3. **服务可用性**: 建议实施降级策略，外部服务不可用时回退到搜索
4. **隐私保护**: LinkedIn等个人数据需注意隐私合规
5. **维护成本**: MCP服务需要持续维护和更新

---

## 十、总结

本升级方案将使Magellan的Agent系统从"通用搜索型"升级为"专业数据驱动型"：

- **Leader**: 增强汇总和报告能力
- **MarketAnalyst**: 全球市场数据覆盖
- **FinancialExpert**: 专业估值建模
- **TeamEvaluator**: 深度背景调查
- **RiskAssessor**: 量化风险监控
- **TechSpecialist**: 代码和专利分析
- **LegalAdvisor**: 专业法规检索
- **TechnicalAnalyst**: 多交易所数据

预计总实施周期: **8周**
预计月度运营成本: **¥5000-8000**
