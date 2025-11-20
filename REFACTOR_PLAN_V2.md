# Magellan 分析向导重构规划文档 V2

**日期**: 2025-11-19
**版本**: v2.0 (基于用户反馈优化)
**状态**: 规划中

---

## 一、核心设计理念 🎯

### 1.1 三层Agent架构

```
┌─────────────────────────────────────────────────────┐
│                  Workflow 层                         │
│  (组合Agents形成分析流程)                            │
│                                                       │
│  early-stage-workflow: [                            │
│    team_evaluator → market_analyst → risk_assessor  │
│  ]                                                    │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│              复合Agent层 (Agent的Agent)               │
│  (由多个原子Agent组成的高级Agent)                    │
│                                                       │
│  deep_dd_agent = {                                   │
│    orchestrator: team_evaluator                     │
│    sub_agents: [market_analyst, financial_expert]   │
│  }                                                    │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│              ⚛️ 原子Agent层 (6个基础专家)            │
│  (所有分析的基石,长期强化的核心能力)                 │
│                                                       │
│  1. 👥 team_evaluator      - 团队评估师             │
│  2. 📊 market_analyst      - 市场分析师             │
│  3. 💰 financial_expert    - 财务专家               │
│  4. ⚠️  risk_assessor       - 风险评估师             │
│  5. 💻 tech_specialist     - 技术专家               │
│  6. ⚖️  legal_advisor       - 法律顾问               │
│                                                       │
│  + 🎯 leader               - 圆桌主持人 (协调者)     │
└─────────────────────────────────────────────────────┘
```

### 1.2 设计原则

#### ✅ **原则1: 原子Agent是唯一基础**
- 所有分析能力必须基于6个原子Agent
- 任何地方（圆桌会议、分析模块、快速判断）都不能绕过原子Agent
- 产品长期目标: 持续强化这6个原子Agent的能力

#### ✅ **原则2: 组合优于创造**
- 不要创造新的专家Agent
- 通过组合原子Agent实现复杂功能
- 例如: "深度尽调" = team_evaluator + market_analyst + financial_expert + risk_assessor

#### ✅ **原则3: Workflow是编排,不是实现**
- Workflow只定义"谁先谁后"
- 真正的能力在Agents里
- Workflow可以是: 线性、并行、条件分支、循环

#### ✅ **原则4: 场景差异化体现在输入和Workflow**
- 每个场景有不同的输入需求
- 每个场景有不同的Workflow编排
- 但底层Agent是统一的

---

## 二、6个原子Agent详解

### Agent 1: 👥 Team Evaluator (团队评估师)

**核心能力**:
- 团队背景调查 (教育、工作经历、创业经历)
- 创始人能力评估 (领导力、执行力、学习能力)
- 团队互补性分析 (技术+商业+运营)
- 团队稳定性评估 (离职率、期权分配)

**应用场景**:
- 早期投资: 团队占比60%+
- 成长期投资: 团队稳定性评估
- 行业研究: 分析头部公司团队

**输入**:
```json
{
  "company_name": "string",
  "team_members": [
    { "name": "张三", "role": "CEO", "background": "..." }
  ],
  "bp_file_id": "string (optional)"
}
```

**输出**:
```json
{
  "team_score": 0-100,
  "founder_background": "...",
  "team_completeness": "完整/缺技术/缺商业",
  "key_risks": ["风险1", "风险2"],
  "key_strengths": ["优势1", "优势2"]
}
```

---

### Agent 2: 📊 Market Analyst (市场分析师)

**核心能力**:
- 市场规模测算 (TAM/SAM/SOM)
- 竞争格局分析 (五力模型、市场集中度)
- 增长趋势预测 (CAGR、增长驱动力)
- 市场机会识别 (空白市场、细分机会)

**应用场景**:
- 早期投资: 市场规模和增长潜力
- 成长期投资: 市场份额和竞争优势
- 公开市场: 行业地位和peer对比
- 行业研究: 市场全景分析

**输入**:
```json
{
  "industry": "string",
  "geography": "China/Global/...",
  "company_name": "string (optional)",
  "competitors": ["公司1", "公司2"]
}
```

**输出**:
```json
{
  "market_size": {
    "tam": 1000000000,
    "sam": 500000000,
    "som": 50000000
  },
  "growth_rate": 25.5,
  "competition": {
    "intensity": "高/中/低",
    "key_players": ["公司1", "公司2"],
    "market_share": {"公司1": 30, "公司2": 25}
  },
  "opportunities": ["机会1", "机会2"]
}
```

---

### Agent 3: 💰 Financial Expert (财务专家)

**核心能力**:
- 财务报表分析 (资产负债表、利润表、现金流量表)
- 估值建模 (DCF、可比公司法、可比交易法)
- 单位经济模型 (CAC、LTV、回收期)
- 财务健康度评估 (流动性、偿债能力、盈利能力)

**应用场景**:
- 早期投资: 单位经济模型和烧钱速率
- 成长期投资: 财务健康度和估值
- 公开市场: 详细财务分析和估值
- 另类投资: 代币经济学分析

**输入**:
```json
{
  "financial_file_id": "string (optional)",
  "annual_revenue": 10000000,
  "financials": {
    "revenue": [...],
    "profit": [...],
    "cash": [...]
  },
  "valuation_request": true
}
```

**输出**:
```json
{
  "financial_health_score": 0-100,
  "unit_economics": {
    "cac": 500,
    "ltv": 2000,
    "ltv_cac_ratio": 4.0
  },
  "valuation": {
    "method": "DCF",
    "range": [50000000, 80000000],
    "fair_value": 65000000
  },
  "key_metrics": {
    "gross_margin": 60,
    "operating_margin": 15,
    "cash_runway_months": 18
  }
}
```

---

### Agent 4: ⚠️ Risk Assessor (风险评估师)

**核心能力**:
- 红旗识别 (法律纠纷、股权问题、造假嫌疑)
- 风险分类 (市场风险、技术风险、团队风险、合规风险)
- 风险量化 (发生概率、影响程度)
- 缓解建议 (风险对冲、保护条款)

**应用场景**:
- 所有场景: 风险评估是必须步骤
- 早期投资: 创始人背景调查、股权结构
- 另类投资: 技术风险、合规风险
- 公开市场: 财务风险、行业风险

**输入**:
```json
{
  "company_name": "string",
  "analysis_context": {
    "team_analysis": {...},
    "market_analysis": {...},
    "financial_analysis": {...}
  }
}
```

**输出**:
```json
{
  "overall_risk_level": "高/中/低",
  "risk_score": 0-100,
  "red_flags": [
    {
      "category": "法律",
      "description": "存在未决诉讼",
      "severity": "高",
      "impact": "可能影响融资和上市"
    }
  ],
  "risk_categories": {
    "market_risk": 60,
    "technical_risk": 40,
    "team_risk": 30,
    "compliance_risk": 70
  },
  "mitigation_suggestions": ["建议1", "建议2"]
}
```

---

### Agent 5: 💻 Tech Specialist (技术专家)

**核心能力**:
- 技术架构评估 (可扩展性、稳定性、安全性)
- 代码质量分析 (GitHub活跃度、代码规范)
- 技术团队能力评估 (技术栈、开发效率)
- 技术壁垒判断 (专利、核心技术、护城河)

**应用场景**:
- 早期投资: 技术团队能力、技术可行性
- 另类投资: 智能合约审计、链上数据分析
- 行业研究: 技术趋势和创新方向

**输入**:
```json
{
  "company_name": "string",
  "github_repo": "string (optional)",
  "tech_stack": ["Python", "React", "AWS"],
  "contract_address": "string (for crypto)"
}
```

**输出**:
```json
{
  "tech_score": 0-100,
  "architecture_quality": "优秀/良好/一般/较差",
  "code_quality": {
    "github_stars": 1500,
    "contributors": 25,
    "commit_frequency": "高",
    "code_review_process": "严格"
  },
  "technical_moat": "强/中/弱",
  "security_audit": {
    "vulnerabilities": ["问题1"],
    "overall": "通过/有风险"
  }
}
```

---

### Agent 6: ⚖️ Legal Advisor (法律顾问)

**核心能力**:
- 股权结构分析 (股东构成、期权池、投票权)
- 合规性审查 (行业资质、许可证、监管要求)
- 法律风险识别 (诉讼、知识产权纠纷)
- 投资条款设计 (优先清算权、反稀释条款)

**应用场景**:
- 早期投资: 股权结构清晰性
- 成长期投资: 合规性审查
- 另类投资: 监管风险评估
- 公开市场: 合规披露审查

**输入**:
```json
{
  "company_name": "string",
  "jurisdiction": "China/US/...",
  "industry": "string",
  "equity_structure": {
    "shareholders": [...]
  }
}
```

**输出**:
```json
{
  "legal_risk_score": 0-100,
  "compliance_status": "合规/存在风险/不合规",
  "equity_structure_assessment": {
    "clarity": "清晰/复杂/混乱",
    "founder_control": "强/中/弱",
    "option_pool": 15
  },
  "legal_issues": [
    {
      "type": "诉讼",
      "description": "...",
      "status": "进行中/已解决"
    }
  ],
  "recommendations": ["建议1", "建议2"]
}
```

---

## 三、现状问题分析

### 3.1 当前4步向导流程

```
Step 1: 场景选择 (ScenarioSelection)
   ↓
Step 2: 目标输入 (5个不同的Input组件) ⚠️ 场景差异化
   ↓
Step 3: 分析配置 (AnalysisConfig) ⚠️ **冗余问题**
   ↓
Step 4: 分析进度 (AnalysisProgress)
```

### 3.2 核心问题

#### **问题1: Step 2和Step 3内容重复** ⚠️ 最严重
**现象**:
- Step 2 (目标输入): 用户填写公司名称、行业、融资阶段、地理位置、竞争对手等
- Step 3 (分析配置): 用户再次填写行业、地理位置、产品、市场规模、竞争对手等

**示例** (IndustryResearch场景):
```javascript
// Step 2: IndustryResearchInput.vue
{
  research_topic: "新能源汽车",
  scope: "China",
  time_horizon: "5years",
  focus_areas: ["market-size", "competition"]
}

// Step 3: AnalysisConfig.vue  ← 重复!
{
  industry: "新能源汽车",        // ← 重复
  geography: "china",             // ← 重复
  competitors: ["比亚迪", "特斯拉"] // ← 重复
}
```

**根本原因**:
- Step 2和Step 3的职责边界不清晰
- 两者都在收集业务信息

#### **问题2: Agents硬编码在Workflow中**
**现象**:
```python
# scenario_workflows.py
WorkflowStepTemplate(
    id="team_quick_check",
    agent="team_evaluator",  # ← 硬编码字符串
    quick_mode=True
)
```

**问题**:
- agent名称是字符串,容易拼写错误
- 没有利用6个原子Agent的标准定义
- quick_agents/目录下有很多临时的quick版Agent,与原子Agent重复

#### **问题3: 场景差异化不明确**
- 5个场景的Input组件功能重复度高
- 没有清晰定义每个场景的"独特输入"是什么
- 配置项（深度、方法论）应该属于哪个场景?

---

## 四、重构方案

### 4.1 简化为3步向导 (合并Step 2和Step 3)

#### 新流程

```
Step 1: 场景选择 + 基础输入
   ↓
   用户选择场景后,立即展示该场景的统一表单
   表单包含: 目标信息 + 分析配置
   ↓
Step 2: 分析进度
   ↓
   实时显示workflow执行进度
   原子Agent的输出
   ↓
Step 3: 报告查看
```

### 4.2 每个场景的统一表单设计

#### **场景1: 早期投资 (Early-Stage Investment)**

**核心输入** (必填):
```javascript
{
  // === 目标公司信息 ===
  company_name: "ABC科技",
  stage: "Seed",  // Angel/Seed/Pre-A/Series A
  industry: "企业服务",

  // === 团队信息 ===
  team_members: [
    { name: "张三", role: "CEO", background: "阿里P8,10年经验" }
  ],

  // === 可选文件 ===
  bp_file_id: "uuid-xxx" (optional),

  // === 分析配置 ===
  depth: "standard",  // quick/standard/comprehensive
  focus_areas: ["team", "market"],  // 重点分析领域
  language: "zh"
}
```

**对应Workflow** (standard模式):
```
1. team_evaluator (团队深度调查)
2. market_analyst (市场验证)
3. financial_expert (商业模式评估)
4. risk_assessor (交叉验证)
5. leader (综合判断)
```

---

#### **场景2: 成长期投资 (Growth Investment)**

**核心输入**:
```javascript
{
  // === 目标公司信息 ===
  company_name: "DEF公司",
  stage: "Series C",  // Series B/C/D/E/Pre-IPO
  industry: "金融科技",
  headquarters: "上海",

  // === 财务数据 ===
  annual_revenue: 50000000,
  financial_file_id: "uuid-yyy" (optional),

  // === 竞争信息 ===
  competitors: [
    { name: "竞品A", market_share: "25%" }
  ],

  // === 分析配置 ===
  depth: "comprehensive",
  valuation_required: true,
  language: "zh"
}
```

**对应Workflow** (comprehensive模式):
```
1. financial_expert (财务深度分析)
2. market_analyst (增长质量评估 + 竞争分析)
3. financial_expert (估值建模)
4. risk_assessor (风险评估)
5. leader (ROI预测)
```

---

#### **场景3: 公开市场投资 (Public Market)**

**核心输入**:
```javascript
{
  // === 标的信息 ===
  ticker: "AAPL",
  research_period: "quarterly",  // quarterly/annually/custom
  custom_start_date: "2024-01-01" (if custom),
  custom_end_date: "2024-12-31" (if custom),

  // === 分析偏好 ===
  key_metrics: ["pe_ratio", "price_to_sales", "roe"],
  include_technical_analysis: true,

  // === 可选文件 ===
  filings_file_ids: ["uuid-zzz"] (optional),

  // === 分析配置 ===
  depth: "standard",
  language: "zh"
}
```

**对应Workflow**:
```
1. financial_expert (数据获取 + 基本面分析)
2. market_analyst (行业对比)
3. tech_specialist (技术面分析, if requested)
4. risk_assessor (风险评估)
5. leader (投资建议)
```

---

#### **场景4: 另类投资 (Alternative Investment)**

**核心输入**:
```javascript
{
  // === 资产信息 ===
  asset_type: "crypto",  // crypto/defi/nft/web3
  project_name: "Uniswap",
  symbol: "UNI",
  contract_address: "0x..." (optional),

  // === 投资规模 ===
  investment_size: 5000000,

  // === 可选文件 ===
  dd_file_ids: ["uuid-aaa"] (optional),

  // === 团队信息 ===
  team_members: [
    { name: "Hayden Adams", role: "Founder" }
  ],

  // === 分析配置 ===
  depth: "comprehensive",
  focus_areas: ["tech", "tokenomics", "community"],
  language: "zh"
}
```

**对应Workflow**:
```
1. tech_specialist (链上数据分析 + 技术评估)
2. financial_expert (代币经济学分析)
3. market_analyst (社区评估)
4. risk_assessor (风险评估: 技术/监管/市场)
5. legal_advisor (合规性审查)
6. leader (投资建议)
```

---

#### **场景5: 行业研究 (Industry Research)**

**核心输入**:
```javascript
{
  // === 研究范围 ===
  research_topic: "新能源汽车产业链",
  industry: "汽车制造",
  geography: "China",
  time_horizon: "5years",

  // === 研究重点 ===
  focus_areas: ["market-size", "competition", "trends", "opportunities"],

  // === 竞争格局 ===
  key_players: ["比亚迪", "特斯拉", "蔚来"],
  products: "纯电动汽车、混动汽车、动力电池",

  // === 市场信息 (optional) ===
  market_size: 500000000000,
  max_size: 1000000000000,

  // === 分析配置 ===
  depth: "comprehensive",
  methodologies: ["swot", "porter", "pestle"],
  include_roundtable: true,  // 是否启用圆桌讨论
  language: "zh"
}
```

**对应Workflow** (comprehensive + roundtable):
```
1. market_analyst (市场定义 + 市场规模测算)
2. market_analyst (增长驱动力分析)
3. market_analyst (竞争格局分析)
4. tech_specialist (技术趋势分析)
5. financial_expert (投资机会地图)
6. roundtable (专家圆桌讨论) ← 6个原子Agent圆桌
7. leader (综合结论)
```

---

### 4.3 前端统一表单组件设计

#### **方案: 场景配置驱动的动态表单**

**场景配置文件** (`frontend/src/config/scenarios.js`):
```javascript
export const SCENARIO_CONFIGS = {
  'early-stage-investment': {
    name: '早期投资尽调',
    icon: '🌱',

    // 字段定义
    fields: [
      // === 基础信息组 ===
      {
        id: 'company_name',
        type: 'text',
        label: '公司名称',
        required: true,
        group: 'basic',
        placeholder: '例如: ABC科技'
      },
      {
        id: 'stage',
        type: 'select',
        label: '融资阶段',
        required: true,
        group: 'basic',
        options: [
          { value: 'angel', label: 'Angel', icon: '👼' },
          { value: 'seed', label: 'Seed', icon: '🌱' },
          { value: 'pre-a', label: 'Pre-A', icon: '🚀' },
          { value: 'series-a', label: 'Series A', icon: '💎' }
        ]
      },
      {
        id: 'industry',
        type: 'text',
        label: '所属行业',
        required: false,
        group: 'basic',
        placeholder: '例如: 企业服务'
      },

      // === 团队信息组 ===
      {
        id: 'team_members',
        type: 'array',
        label: '团队成员',
        required: false,
        group: 'team',
        item_schema: {
          name: { type: 'text', label: '姓名' },
          role: { type: 'text', label: '职位' },
          background: { type: 'textarea', label: '背景' }
        }
      },

      // === 文件上传组 ===
      {
        id: 'bp_file',
        type: 'file',
        label: '商业计划书',
        required: false,
        group: 'document',
        accept: ['.pdf', '.ppt', '.pptx', '.doc', '.docx']
      },

      // === 分析配置组 (折叠) ===
      {
        id: 'depth',
        type: 'radio-card',
        label: '分析深度',
        required: true,
        group: 'config',
        default: 'standard',
        options: [
          {
            value: 'quick',
            label: '快速判断',
            description: '30分钟出结果',
            duration: '30min'
          },
          {
            value: 'standard',
            label: '标准分析',
            description: '2小时深度分析',
            duration: '2h'
          },
          {
            value: 'comprehensive',
            label: '全面尽调',
            description: '4小时全方位尽调',
            duration: '4h'
          }
        ]
      },
      {
        id: 'focus_areas',
        type: 'checkbox-group',
        label: '重点关注',
        required: false,
        group: 'config',
        options: [
          { value: 'team', label: '团队能力', icon: '👥' },
          { value: 'market', label: '市场空间', icon: '📊' },
          { value: 'business_model', label: '商业模式', icon: '💼' },
          { value: 'tech', label: '技术壁垒', icon: '💻' }
        ]
      }
    ],

    // 字段分组定义
    groups: [
      { id: 'basic', label: '基础信息', icon: '📋', expanded: true },
      { id: 'team', label: '团队信息', icon: '👥', expanded: true },
      { id: 'document', label: '文件上传', icon: '📎', expanded: false },
      { id: 'config', label: '分析配置', icon: '⚙️', expanded: false }
    ],

    // 对应的Workflow
    workflows: {
      quick: ['team_evaluator', 'market_analyst', 'risk_assessor'],
      standard: ['team_evaluator', 'market_analyst', 'financial_expert', 'risk_assessor', 'leader'],
      comprehensive: ['team_evaluator', 'market_analyst', 'financial_expert', 'tech_specialist', 'risk_assessor', 'legal_advisor', 'leader']
    }
  },

  // 其他4个场景...
}
```

**统一表单组件** (`UnifiedScenarioForm.vue`):
```vue
<template>
  <div class="unified-scenario-form">
    <h2>{{ scenarioConfig.name }}</h2>

    <form @submit.prevent="handleSubmit">
      <!-- 动态渲染字段组 -->
      <div
        v-for="group in scenarioConfig.groups"
        :key="group.id"
        class="field-group"
      >
        <div class="group-header" @click="toggleGroup(group.id)">
          <span class="group-icon">{{ group.icon }}</span>
          <span class="group-label">{{ group.label }}</span>
          <span class="toggle-icon">{{ groupStates[group.id] ? '▲' : '▼' }}</span>
        </div>

        <div v-if="groupStates[group.id]" class="group-content">
          <!-- 动态渲染字段 -->
          <component
            v-for="field in getFieldsByGroup(group.id)"
            :key="field.id"
            :is="getFieldComponent(field.type)"
            v-model="formData[field.id]"
            :field="field"
          />
        </div>
      </div>

      <!-- 提交按钮 -->
      <div class="form-actions">
        <button type="button" @click="$emit('back')">返回</button>
        <button type="submit" :disabled="!isValid">开始分析</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { SCENARIO_CONFIGS } from '@/config/scenarios';

// 字段组件映射
import TextField from './fields/TextField.vue';
import SelectField from './fields/SelectField.vue';
import ArrayField from './fields/ArrayField.vue';
import FileField from './fields/FileField.vue';
import RadioCardField from './fields/RadioCardField.vue';
import CheckboxGroupField from './fields/CheckboxGroupField.vue';

const props = defineProps({
  scenario: { type: String, required: true }
});

const emit = defineEmits(['submit', 'back']);

// 获取场景配置
const scenarioConfig = computed(() => SCENARIO_CONFIGS[props.scenario]);

// 表单数据
const formData = ref({});

// 字段组展开状态
const groupStates = ref(
  Object.fromEntries(
    scenarioConfig.value.groups.map(g => [g.id, g.expanded])
  )
);

// 获取字段组件
function getFieldComponent(type) {
  const componentMap = {
    'text': TextField,
    'select': SelectField,
    'array': ArrayField,
    'file': FileField,
    'radio-card': RadioCardField,
    'checkbox-group': CheckboxGroupField
  };
  return componentMap[type];
}

// 按组获取字段
function getFieldsByGroup(groupId) {
  return scenarioConfig.value.fields.filter(f => f.group === groupId);
}

// 表单验证
const isValid = computed(() => {
  return scenarioConfig.value.fields
    .filter(f => f.required)
    .every(f => formData.value[f.id]);
});

// 提交
function handleSubmit() {
  emit('submit', {
    scenario: props.scenario,
    data: formData.value,
    workflow: scenarioConfig.value.workflows[formData.value.depth || 'standard']
  });
}
</script>
```

**好处**:
- ✅ **一个组件适配所有场景** - 通过配置驱动
- ✅ **场景差异化清晰** - 每个场景有独立的字段定义
- ✅ **易于扩展** - 新增场景只需添加配置
- ✅ **消除冗余** - 目标+配置在一个表单里

---

### 4.4 原子Agent标准化与配置文件化

#### **删除冗余的quick_agents**

**现状问题**:
- `backend/services/report_orchestrator/app/core/quick_agents/` 目录下有16个quick版agent
- 这些agent与`agents/`目录下的standard agents功能重复
- 违反了"原子Agent是唯一基础"的原则

**重构方案**:
1. **删除quick_agents目录**
2. **在原子Agent中添加quick_mode参数**

**示例**:
```python
# backend/services/report_orchestrator/app/agents/team_analysis_agent.py

class TeamEvaluatorAgent:
    """团队评估原子Agent - 唯一的团队分析实现"""

    def __init__(self, quick_mode: bool = False):
        self.quick_mode = quick_mode

    async def analyze(self, context: dict) -> dict:
        if self.quick_mode:
            # 快速模式: 30秒分析
            return await self._quick_analysis(context)
        else:
            # 标准模式: 深度分析
            return await self._deep_analysis(context)

    async def _quick_analysis(self, context: dict) -> dict:
        """快速分析: 只看核心信息"""
        return {
            "team_score": self._calculate_quick_score(context),
            "key_members_background": self._extract_key_members(context),
            "confidence": "medium"
        }

    async def _deep_analysis(self, context: dict) -> dict:
        """深度分析: 全面尽调"""
        return {
            "team_score": self._calculate_deep_score(context),
            "founder_background": await self._research_founder(context),
            "team_completeness": self._assess_completeness(context),
            "team_stability": self._assess_stability(context),
            "key_risks": self._identify_risks(context),
            "key_strengths": self._identify_strengths(context),
            "confidence": "high"
        }
```

#### **Agent配置文件化**

**agents配置文件** (`backend/services/report_orchestrator/config/agents.yaml`):
```yaml
# 6个原子Agent配置
agents:
  team_evaluator:
    name: "团队评估师"
    description: "评估团队背景、能力和稳定性"
    class: "app.agents.team_analysis_agent.TeamEvaluatorAgent"
    capabilities:
      - team_background_check
      - founder_assessment
      - team_completeness_analysis
    inputs:
      - company_name
      - team_members
      - bp_file_id (optional)
    outputs:
      - team_score
      - founder_background
      - team_completeness
      - key_risks
      - key_strengths
    quick_mode_supported: true
    estimated_duration:
      quick: 60  # 秒
      standard: 300

  market_analyst:
    name: "市场分析师"
    description: "分析市场规模、竞争格局和增长趋势"
    class: "app.agents.market_analysis_agent.MarketAnalystAgent"
    capabilities:
      - market_sizing
      - competition_analysis
      - trend_forecasting
    inputs:
      - industry
      - geography
      - company_name (optional)
      - competitors (optional)
    outputs:
      - market_size
      - growth_rate
      - competition
      - opportunities
    quick_mode_supported: true
    estimated_duration:
      quick: 90
      standard: 400

  financial_expert:
    name: "财务专家"
    description: "分析财务健康度、单位经济模型和估值"
    class: "app.agents.financial_expert_agent.FinancialExpertAgent"
    capabilities:
      - financial_statement_analysis
      - valuation_modeling
      - unit_economics_analysis
    inputs:
      - financial_file_id (optional)
      - annual_revenue (optional)
      - financials (optional)
      - valuation_request (optional)
    outputs:
      - financial_health_score
      - unit_economics
      - valuation (if requested)
      - key_metrics
    quick_mode_supported: true
    estimated_duration:
      quick: 90
      standard: 600

  risk_assessor:
    name: "风险评估师"
    description: "识别红旗、量化风险和提供缓解建议"
    class: "app.agents.risk_agent.RiskAssessorAgent"
    capabilities:
      - red_flag_detection
      - risk_classification
      - risk_quantification
    inputs:
      - company_name
      - analysis_context (from previous agents)
    outputs:
      - overall_risk_level
      - risk_score
      - red_flags
      - risk_categories
      - mitigation_suggestions
    quick_mode_supported: true
    estimated_duration:
      quick: 60
      standard: 300

  tech_specialist:
    name: "技术专家"
    description: "评估技术架构、代码质量和技术壁垒"
    class: "app.agents.tech_specialist_agent.TechSpecialistAgent"
    capabilities:
      - architecture_assessment
      - code_quality_analysis
      - technical_moat_evaluation
    inputs:
      - company_name
      - github_repo (optional)
      - tech_stack (optional)
      - contract_address (optional, for crypto)
    outputs:
      - tech_score
      - architecture_quality
      - code_quality
      - technical_moat
      - security_audit (for crypto)
    quick_mode_supported: true
    estimated_duration:
      quick: 60
      standard: 400

  legal_advisor:
    name: "法律顾问"
    description: "审查股权结构、合规性和法律风险"
    class: "app.agents.legal_advisor_agent.LegalAdvisorAgent"
    capabilities:
      - equity_structure_analysis
      - compliance_review
      - legal_risk_identification
    inputs:
      - company_name
      - jurisdiction
      - industry
      - equity_structure (optional)
    outputs:
      - legal_risk_score
      - compliance_status
      - equity_structure_assessment
      - legal_issues
      - recommendations
    quick_mode_supported: false
    estimated_duration:
      standard: 500

  leader:
    name: "圆桌主持人"
    description: "主持讨论、综合判断、形成结论"
    class: "app.core.roundtable.investment_agents.LeaderAgent"
    capabilities:
      - discussion_facilitation
      - consensus_building
      - synthesis
    inputs:
      - all_agent_outputs
    outputs:
      - final_recommendation
      - investment_score
      - key_insights
      - next_steps
    quick_mode_supported: false
    estimated_duration:
      standard: 180
```

#### **Agent注册表**

```python
# backend/services/report_orchestrator/app/core/agent_registry.py
import yaml
from typing import Dict, Type
import importlib

class AgentRegistry:
    """原子Agent注册表 - 从配置文件加载"""

    def __init__(self, config_path: str = "config/agents.yaml"):
        self.config = self._load_config(config_path)
        self.agents: Dict[str, Type] = {}
        self._register_agents()

    def _load_config(self, path: str) -> dict:
        """加载agents配置"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _register_agents(self):
        """注册所有agents"""
        for agent_id, agent_config in self.config['agents'].items():
            agent_class = self._import_class(agent_config['class'])
            self.agents[agent_id] = {
                'class': agent_class,
                'config': agent_config
            }

    def _import_class(self, class_path: str):
        """动态导入Agent类"""
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def get_agent(self, agent_id: str, quick_mode: bool = False):
        """获取agent实例"""
        if agent_id not in self.agents:
            raise ValueError(f"Unknown agent: {agent_id}")

        agent_info = self.agents[agent_id]
        agent_class = agent_info['class']
        config = agent_info['config']

        # 检查是否支持quick_mode
        if quick_mode and not config.get('quick_mode_supported', False):
            raise ValueError(f"Agent {agent_id} does not support quick_mode")

        return agent_class(quick_mode=quick_mode)

    def get_agent_config(self, agent_id: str) -> dict:
        """获取agent配置"""
        if agent_id not in self.agents:
            raise ValueError(f"Unknown agent: {agent_id}")
        return self.agents[agent_id]['config']

    def list_agents(self) -> list:
        """列出所有原子agents"""
        return [
            {
                'id': agent_id,
                'name': info['config']['name'],
                'description': info['config']['description'],
                'capabilities': info['config']['capabilities']
            }
            for agent_id, info in self.agents.items()
        ]


# 单例模式
agent_registry = AgentRegistry()
```

---

### 4.5 Workflow配置文件化

#### **workflow配置文件** (`backend/services/report_orchestrator/config/workflows.yaml`):
```yaml
# 5个场景的Workflow定义
workflows:
  early-stage-investment:
    name: "早期投资尽调"
    orchestrator_class: "app.core.orchestrators.early_stage_orchestrator.EarlyStageInvestmentOrchestrator"

    quick:
      name: "快速判断 (30分钟)"
      estimated_duration: 1800  # 30分钟
      steps:
        - id: "team_quick_check"
          agent: "team_evaluator"
          quick_mode: true
          required: true
          inputs: ["company_name", "team_members"]
          outputs: ["team_score", "key_members_background"]

        - id: "market_opportunity"
          agent: "market_analyst"
          quick_mode: true
          required: true
          inputs: ["industry", "geography"]
          outputs: ["market_size_estimate", "market_attractiveness"]

        - id: "red_flag_scan"
          agent: "risk_assessor"
          quick_mode: true
          required: true
          inputs: ["company_name", "context.team_quick_check", "context.market_opportunity"]
          outputs: ["red_flags", "critical_issues"]

        - id: "quick_judgment"
          agent: "leader"
          required: true
          inputs: ["context.all"]
          outputs: ["recommendation", "confidence", "next_steps"]

    standard:
      name: "标准分析 (2小时)"
      estimated_duration: 7200
      steps:
        - id: "bp_parsing"
          agent: "financial_expert"  # 复用财务专家来解析BP
          required: false
          condition: "target.bp_file_id is not None"
          inputs: ["bp_file_id"]
          outputs: ["structured_bp", "business_model", "financials"]

        - id: "team_deep_investigation"
          agent: "team_evaluator"
          required: true
          inputs: ["company_name", "team_members", "context.bp_parsing"]
          outputs: ["team_analysis", "founder_background", "experience_match"]

        - id: "market_validation"
          agent: "market_analyst"
          required: true
          inputs: ["industry", "geography", "context.bp_parsing"]
          data_sources: ["web_search", "industry_reports"]
          outputs: ["market_size", "competition", "market_trends"]

        - id: "business_model_assessment"
          agent: "financial_expert"
          required: true
          inputs: ["context.bp_parsing", "context.market_validation"]
          outputs: ["unit_economics", "revenue_model", "scalability"]

        - id: "cross_validation"
          agent: "risk_assessor"
          required: true
          inputs: ["context.all"]
          outputs: ["inconsistencies", "red_flags"]

        - id: "investment_recommendation"
          agent: "leader"
          required: true
          inputs: ["context.all"]
          outputs: ["recommendation", "investment_score", "key_risks", "next_steps"]

    comprehensive:
      name: "全面尽调 (4小时)"
      estimated_duration: 14400
      steps:
        # ... 所有standard的步骤
        # ... 额外增加tech_specialist和legal_advisor

  growth-investment:
    # ... 类似结构

  public-market-investment:
    # ... 类似结构

  alternative-investment:
    # ... 类似结构

  industry-research:
    name: "行业/市场研究"
    orchestrator_class: "app.core.orchestrators.industry_research_orchestrator.IndustryResearchOrchestrator"

    comprehensive:
      name: "深度行业研究 + 圆桌讨论"
      estimated_duration: 10800  # 3小时
      steps:
        - id: "market_definition"
          agent: "market_analyst"
          required: true
          inputs: ["research_topic", "industry"]
          outputs: ["market_boundaries", "segments", "value_chain"]

        - id: "market_sizing"
          agent: "market_analyst"
          required: true
          data_sources: ["industry_reports", "government_data", "web_search"]
          outputs: ["tam_sam_som", "historical_growth", "future_projections"]

        - id: "growth_drivers_analysis"
          agent: "market_analyst"
          required: true
          inputs: ["context.market_sizing"]
          outputs: ["key_drivers", "barriers", "catalysts"]

        - id: "competitive_landscape"
          agent: "market_analyst"
          required: true
          data_sources: ["web_search", "company_databases"]
          outputs: ["key_players", "market_structure", "competitive_dynamics"]

        - id: "technology_trends"
          agent: "tech_specialist"
          required: true
          inputs: ["industry", "context.competitive_landscape"]
          outputs: ["tech_trends", "innovations", "disruptors"]

        - id: "investment_opportunity_mapping"
          agent: "financial_expert"
          required: true
          inputs: ["context.all"]
          outputs: ["opportunity_areas", "attractive_segments", "entry_strategies"]

        - id: "roundtable_discussion"
          agent: "roundtable"  # 特殊: 圆桌会议
          required: true
          condition: "config.include_roundtable == True"
          inputs: ["context.all"]
          participants:  # 6个原子Agent参与
            - team_evaluator
            - market_analyst
            - financial_expert
            - risk_assessor
            - tech_specialist
            - legal_advisor
          moderator: "leader"
          outputs: ["expert_insights", "consensus_view", "debate_points", "refined_conclusions"]
```

#### **Workflow引擎**

```python
# backend/services/report_orchestrator/app/core/workflow_engine.py
import yaml
from typing import Dict, Any, List
from .agent_registry import agent_registry

class WorkflowEngine:
    """基于配置的Workflow执行引擎"""

    def __init__(self, config_path: str = "config/workflows.yaml"):
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_workflow(self, scenario: str, depth: str) -> dict:
        """获取workflow定义"""
        if scenario not in self.config['workflows']:
            raise ValueError(f"Unknown scenario: {scenario}")

        scenario_config = self.config['workflows'][scenario]

        if depth not in scenario_config:
            raise ValueError(f"Unknown depth for {scenario}: {depth}")

        return scenario_config[depth]

    async def execute_workflow(
        self,
        scenario: str,
        depth: str,
        target: dict,
        config: dict,
        websocket
    ) -> dict:
        """执行workflow"""

        # 获取workflow定义
        workflow = self.get_workflow(scenario, depth)
        context = {'target': target, 'config': config}

        # 通知开始
        await self._send_workflow_start(websocket, workflow)

        # 执行步骤
        for step in workflow['steps']:
            # 检查条件
            if not self._check_condition(step, context):
                continue

            # 获取agent
            agent = agent_registry.get_agent(
                step['agent'],
                quick_mode=step.get('quick_mode', False)
            )

            # 准备输入
            inputs = self._prepare_inputs(step['inputs'], context)

            # 执行agent
            await self._send_step_start(websocket, step)

            try:
                result = await agent.analyze(inputs)
                context[step['id']] = result

                await self._send_step_complete(websocket, step, result)

            except Exception as e:
                await self._send_step_error(websocket, step, str(e))
                raise

        # 返回最终context
        return context

    def _check_condition(self, step: dict, context: dict) -> bool:
        """检查步骤执行条件"""
        if 'condition' not in step:
            return True

        condition = step['condition']
        # 简单的条件表达式评估
        # 例如: "target.bp_file_id is not None"
        # 实际实现可以用ast.literal_eval或更安全的方式
        return eval(condition, {'target': context['target'], 'config': context['config']})

    def _prepare_inputs(self, input_defs: List[str], context: dict) -> dict:
        """准备agent输入"""
        inputs = {}

        for input_def in input_defs:
            if input_def.startswith('context.'):
                # 从context获取
                key = input_def.replace('context.', '')
                if key == 'all':
                    inputs['context'] = context
                else:
                    inputs[key] = context.get(key)
            else:
                # 从target获取
                inputs[input_def] = context['target'].get(input_def)

        return inputs

    async def _send_workflow_start(self, websocket, workflow: dict):
        """通知workflow开始"""
        await websocket.send_json({
            "type": "workflow_start",
            "data": {
                "name": workflow['name'],
                "estimated_duration": workflow['estimated_duration'],
                "steps": [
                    {
                        "id": step['id'],
                        "name": agent_registry.get_agent_config(step['agent'])['name'],
                        "agent": step['agent']
                    }
                    for step in workflow['steps']
                    if step.get('required', True)
                ]
            }
        })

    async def _send_step_start(self, websocket, step: dict):
        """通知步骤开始"""
        agent_config = agent_registry.get_agent_config(step['agent'])
        await websocket.send_json({
            "type": "step_start",
            "data": {
                "step_id": step['id'],
                "agent_id": step['agent'],
                "agent_name": agent_config['name'],
                "estimated_duration": agent_config['estimated_duration'].get(
                    'quick' if step.get('quick_mode') else 'standard'
                )
            }
        })

    async def _send_step_complete(self, websocket, step: dict, result: dict):
        """通知步骤完成"""
        await websocket.send_json({
            "type": "step_complete",
            "data": {
                "step_id": step['id'],
                "agent_id": step['agent'],
                "result": result
            }
        })

    async def _send_step_error(self, websocket, step: dict, error: str):
        """通知步骤错误"""
        await websocket.send_json({
            "type": "step_error",
            "data": {
                "step_id": step['id'],
                "agent_id": step['agent'],
                "error": error
            }
        })


# 单例
workflow_engine = WorkflowEngine()
```

---

## 五、实施路线图

### Phase 1: 基础重构 (3-4天)

#### Day 1: 清理和标准化
- [ ] **删除quick_agents目录** (16个冗余agent)
- [ ] **整合为6个原子Agent** + 1个leader
- [ ] **为每个原子Agent添加quick_mode支持**
- [ ] **创建agents.yaml配置文件**
- [ ] **实现AgentRegistry**

#### Day 2: 配置系统
- [ ] **创建workflows.yaml配置文件**
- [ ] **实现WorkflowEngine**
- [ ] **修改Orchestrator使用WorkflowEngine**
- [ ] **测试workflow加载和执行**

#### Day 3-4: 前端统一表单
- [ ] **创建scenarios.js配置文件** (5个场景)
- [ ] **实现UnifiedScenarioForm组件**
- [ ] **实现字段组件** (TextField, SelectField, etc.)
- [ ] **重构AnalysisWizardView** (4步→3步)

### Phase 2: 测试与优化 (2-3天)

#### Day 5: 单元测试
- [ ] 测试AgentRegistry
- [ ] 测试WorkflowEngine
- [ ] 测试每个原子Agent (quick + standard mode)

#### Day 6: 集成测试
- [ ] 测试5个场景的完整workflow
- [ ] 测试场景切换
- [ ] 测试quick/standard/comprehensive模式

#### Day 7: E2E测试
- [ ] 前端表单提交 → 后端workflow执行 → 结果返回
- [ ] 测试WebSocket实时推送
- [ ] 测试报告生成

### Phase 3: 文档与上线 (1天)

#### Day 8: 文档和部署
- [ ] 更新开发文档
- [ ] 创建Agent开发指南
- [ ] 创建Workflow配置指南
- [ ] 灰度发布
- [ ] 监控和修复问题

---

## 六、关键设计决策总结

### ✅ 决策1: 简化为3步向导
- **Step 1**: 场景选择 + 统一表单 (目标+配置)
- **Step 2**: 分析进度
- **Step 3**: 报告查看

### ✅ 决策2: 场景差异化体现在配置
- 每个场景有独立的字段定义 (scenarios.js)
- 不同场景对应不同的workflow (workflows.yaml)
- 底层Agent统一,组合方式不同

### ✅ 决策3: 原子Agent是唯一基础
- 只有6个原子Agent + 1个leader
- 删除所有quick_agents
- 原子Agent支持quick_mode参数

### ✅ 决策4: Agents配置文件化
- agents.yaml定义原子Agent
- AgentRegistry动态加载
- 不使用数据库,使用YAML文件

### ✅ 决策5: Workflow配置文件化
- workflows.yaml定义场景workflow
- WorkflowEngine执行workflow
- 支持条件执行、动态输入

### ✅ 决策6: 不需要workflow编辑器
- Workflow由产品团队定义
- 用户不可编辑
- 通过YAML文件维护

---

## 七、风险与挑战

### 风险1: 原子Agent能力不足
**风险**: 6个原子Agent可能无法覆盖所有分析需求

**缓解**:
- 原子Agent设计要充分考虑扩展性
- 通过组合实现复杂功能
- 持续迭代增强Agent能力

### 风险2: Workflow复杂度增加
**风险**: 复杂的workflow可能难以维护

**缓解**:
- Workflow配置清晰分层 (quick/standard/comprehensive)
- 添加workflow验证工具
- 提供workflow可视化工具 (未来)

### 风险3: 用户适应新流程
**风险**: 3步流程与现有4步不同

**缓解**:
- 保持核心流程简单
- 提供引导教程
- 灰度发布,收集反馈

---

## 八、下一步行动

**立即开始**:
1. 确认重构方案
2. 开始Phase 1 Day 1: 清理quick_agents
3. 创建agents.yaml和workflows.yaml

**需要您确认**:
- ✅ 3步向导方案
- ✅ 场景差异化通过配置实现
- ✅ 原子Agent统一化
- ✅ 配置文件化 (YAML)

---

**文档版本**: v2.0
**最后更新**: 2025-11-19
**状态**: 等待确认后开始实施
