# Phase 3: Agent能力增强计划
## Magellan AI Investment Analysis Platform - Agent Enhancement with MCP Tools

**创建日期**: 2025-11-16
**状态**: 🚧 进行中
**重点**: 强化Agent能力，集成MCP工具，优化Prompt

---

## 🎯 核心目标

Phase 3 聚焦于**提升现有Agent的分析能力**，而非添加新功能。这是MVP版本，暂不考虑用户认证和权限系统。

### 重点任务
1. ✅ **清理过程文档** - 删除Phase 1/2的中间文档
2. ✅ **集成Yahoo Finance MCP** - 为财务和市场Agent添加实时数据获取能力
3. 🚧 **优化Agent Prompt** - 提升分析质量和准确性
4. ⏳ **测试Agent改进效果** - 验证工具集成和Prompt优化的效果

---

## 📋 任务清单

### ✅ 已完成任务

#### 1. 清理多余文档 (100%)
删除的文件:
- ❌ `PHASE1_FINAL_SUMMARY.md`
- ❌ `PHASE1_COMPLETION_REPORT.md`
- ❌ `PHASE1_PROGRESS.md`
- ❌ `PHASE2_PLANNING.md`
- ❌ `PHASE2_MIDPOINT_REPORT.md`
- ❌ `PHASE2_PROGRESS.md`
- ❌ `PHASE2_PROGRESS_REPORT.md`
- ❌ `PHASE2_FINAL_SUMMARY.md`
- ❌ `PHASE2_COMPLETION_REPORT.md`
- ❌ `test_phase1_integration.sh`
- ❌ `test_e2e_services.sh`
- ❌ `test_websocket.js`
- ❌ `PROJECT_STATUS.md`
- ❌ `ROUNDTABLE_*.md` (多个)
- ❌ `frontend/PROJECT_SUMMARY.md`
- ❌ `frontend/LANGUAGE_SWITCH_GUIDE.md`
- ❌ `frontend/I18N_README.md`

**保留的重要文档**:
- ✅ `README.md` - 项目主文档
- ✅ `docs/` - 结构化文档目录

#### 2. 集成Yahoo Finance MCP工具 (100%)

**新增文件**:
- `/backend/services/report_orchestrator/app/core/roundtable/yahoo_finance_tool.py` (~415行)

**功能**:
```python
class YahooFinanceTool(Tool):
    支持的操作:
    - price: 获取实时股价、涨跌、52周高低、市值
    - history: 获取历史价格(1d/5d/1mo/3mo/6mo/1y/2y/5y/10y/ytd/max)
    - financials: 获取财务报表(income/balance/cash)
    - info: 获取公司基本信息(行业、国家、员工数、简介)
    - news: 获取最新公司新闻(前5条)
```

**集成到Agent**:
- ✅ Market Analysis Agent - 获取股票市场数据
- ✅ Financial Expert Agent - 获取财务报表数据

**依赖更新**:
```txt
# requirements.txt 新增
yfinance>=0.2.40  # Yahoo Finance API wrapper
```

**工具分配逻辑** (`mcp_tools.py:create_mcp_tools_for_agent`):
```python
MarketAnalyst: TavilySearch + PublicData + YahooFinance + KnowledgeBase
FinancialExpert: TavilySearch + PublicData + YahooFinance + KnowledgeBase
TeamEvaluator: TavilySearch + KnowledgeBase
RiskAssessor: TavilySearch + KnowledgeBase
```

---

### 🚧 进行中任务

#### 3. 优化Market Analysis Agent (30%)

**当前问题**:
- ❌ 经常无法获取股票数据
- ❌ Prompt过于简单，缺乏深度分析指引
- ❌ 未充分利用Yahoo Finance工具

**改进计划**:
1. **Prompt优化**:
   - 增加股票代码识别逻辑（如果公司已上市）
   - 引导使用Yahoo Finance获取实时数据
   - 增加行业对比分析指引
   - 强化竞品分析框架

2. **工具使用增强**:
   - 如果公司已上市，使用Yahoo Finance获取:
     - 当前股价和市值
     - 6个月/1年价格趋势
     - 最新新闻
   - 结合web search验证BP中的市场数据

3. **分析深度提升**:
   - TAM/SAM/SOM验证框架
   - 竞品护城河分析
   - 市场进入壁垒评估

**预期文件修改**:
- `market_analysis_agent.py` - 增强Prompt和逻辑

---

#### 4. 优化Financial Analysis Agent (未开始)

**当前问题**:
- ❌ 缺少对上市公司的财报数据获取
- ❌ 财务分析缺乏行业benchmark

**改进计划**:
1. 使用Yahoo Finance获取:
   - 利润表 (Income Statement)
   - 资产负债表 (Balance Sheet)
   - 现金流量表 (Cash Flow)

2. 计算关键财务指标:
   - 毛利率、净利率
   - ROE、ROA
   - 现金流健康度
   - 增长率 (YoY)

3. 行业对比:
   - 与同行业公司对比
   - 识别财务异常

**预期文件修改**:
- 查找并修改 Financial Analysis Agent 文件

---

#### 5-7. 优化其他Agent的Prompt (未开始)

**待优化Agent**:
- Team Analysis Agent
- Risk Agent
- Valuation Agent
- Exit Agent
- Preference Match Agent

**通用优化方向**:
1. **结构化Prompt**:
   - 明确任务目标
   - 提供分析框架
   - 规范输出格式

2. **增加思考链**:
   - Chain-of-Thought prompting
   - 要求先列出分析步骤
   - 再进行逐步分析

3. **质量控制**:
   - 要求引用数据来源
   - 明确不确定性
   - 避免过度自信

---

### ⏳ 待开始任务

#### 8. 重新构建Docker容器 (未开始)

安装yfinance依赖:
```bash
cd /Users/dengjianbo/Documents/Magellan
docker-compose build --no-cache report_orchestrator
docker-compose restart report_orchestrator
```

#### 9. 测试Agent改进效果 (未开始)

**测试场景**:
1. 上市公司分析 (如 Tesla, Apple)
   - 验证能否获取股价数据
   - 验证能否获取财报数据
   - 验证市场分析质量

2. 未上市公司分析
   - 验证降级策略 (使用web search代替)
   - 验证分析逻辑的健壮性

3. 完整DD流程测试
   - 所有Agent协同工作
   - 最终报告质量评估

---

## 🏗️ 技术架构更新

### MCP工具架构

```
Tool (抽象基类)
├── TavilySearchTool - 网络搜索
├── PublicDataTool - 公开数据API
├── KnowledgeBaseTool - 内部知识库
└── YahooFinanceTool - 金融数据 (NEW)
    ├── get_current_price()
    ├── get_price_history()
    ├── get_financials()
    ├── get_company_info()
    └── get_news()
```

### Agent工具配置

```python
# mcp_tools.py:create_mcp_tools_for_agent()

def get_tools_for_agent(agent_role):
    if agent_role == "MarketAnalyst":
        return [
            TavilySearchTool(),
            PublicDataTool(),
            YahooFinanceTool(),  # 新增
            KnowledgeBaseTool()
        ]
    elif agent_role == "FinancialExpert":
        return [
            TavilySearchTool(),
            PublicDataTool(),
            YahooFinanceTool(),  # 新增
            KnowledgeBaseTool()
        ]
    # ... 其他Agent
```

---

## 📈 进度追踪

| 任务 | 状态 | 进度 | 预计完成 |
|------|------|------|---------|
| 1. 清理过程文档 | ✅ 完成 | 100% | - |
| 2. 集成Yahoo Finance | ✅ 完成 | 100% | - |
| 3. 优化Market Agent | 🚧 进行中 | 30% | 今天 |
| 4. 优化Financial Agent | ⏳ 待开始 | 0% | 今天 |
| 5. 优化Team Agent | ⏳ 待开始 | 0% | 今天 |
| 6. 优化Risk Agent | ⏳ 待开始 | 0% | 今天 |
| 7. 优化Valuation Agent | ⏳ 待开始 | 0% | 今天 |
| 8. 重建Docker容器 | ⏳ 待开始 | 0% | 今天 |
| 9. 测试改进效果 | ⏳ 待开始 | 0% | 今天 |

**总体进度**: 2/9 (22%)

---

## 💡 关键决策

### 为什么选择Yahoo Finance?

1. **免费且无需API Key** - 适合MVP阶段
2. **覆盖全球市场** - 支持美股、港股、A股等
3. **数据全面** - 价格、财报、新闻一应俱全
4. **Python生态成熟** - yfinance库稳定可靠
5. **MCP兼容性好** - 多个现成的MCP实现

### Agent优化策略

**优先级排序**:
1. **P0 - Market & Financial Agent** - 数据获取能力最关键
2. **P1 - Team & Risk Agent** - 分析框架优化
3. **P2 - Valuation & Exit Agent** - 逻辑细化

**Prompt优化原则**:
- ✅ 结构化输出 (JSON格式)
- ✅ 明确分析框架 (如SWOT、PEST、Porter五力)
- ✅ 要求数据来源引用
- ✅ 区分事实与推断
- ✅ 量化评分(1-10分)

---

## 🎯 成功标准

### Phase 3 完成标准:
1. ✅ Yahoo Finance工具集成并可用
2. ✅ Market Agent能够获取上市公司实时数据
3. ✅ Financial Agent能够分析财务报表
4. ✅ 所有Agent Prompt结构化且高质量
5. ✅ 端到端测试通过(上市公司 + 非上市公司)
6. ✅ Docker容器重建成功

### 质量指标:
- 上市公司数据获取成功率 > 90%
- Prompt结构化程度 100%
- Agent输出JSON解析成功率 > 95%
- 完整DD流程无崩溃

---

## 📝 后续计划 (Phase 4方向)

基于MVP原则，后续可能的方向:

1. **更多MCP工具**:
   - CrunchBase API (创业公司数据)
   - PitchBook API (投资数据)
   - News API (新闻聚合)

2. **Agent能力扩展**:
   - 多Agent协作优化
   - Agent记忆机制
   - 自我反思和纠错

3. **用户体验**:
   - 实时进度展示优化
   - Agent思考过程可视化
   - 中间结果保存和复用

---

**最后更新**: 2025-11-16 18:30
**下一步行动**: 优化Market Analysis Agent的Prompt和工具使用逻辑
