/**
 * Investment Scenarios Configuration
 * 投资场景配置
 *
 * 与后端workflows.yaml保持同步
 * 定义所有可用的投资分析场景
 */

export const ANALYSIS_MODES = {
  QUICK: 'quick',
  STANDARD: 'standard'
}

export const SCENARIOS = {
  // ============================================
  // 早期投资分析 (Early Stage Investment)
  // ============================================
  EARLY_STAGE: {
    id: 'early-stage-investment',
    name: {
      zh: '早期项目投资分析',
      en: 'Early Stage Investment Analysis'
    },
    description: {
      zh: '适用于种子轮、天使轮、Pre-A轮项目的尽职调查',
      en: 'Due diligence for seed, angel, and pre-A stage projects'
    },
    icon: '🌱',
    category: 'venture',

    // 适用的投资阶段
    stages: ['seed', 'angel', 'pre-a', 'series-a'],

    // 分析重点
    focus: {
      zh: ['团队能力 (40%)', '市场机会 (35%)', '产品创新 (25%)'],
      en: ['Team (40%)', 'Market (35%)', 'Product (25%)']
    },

    // 表单字段配置
    formFields: [
      {
        name: 'company_name',
        type: 'text',
        label: { zh: '公司名称', en: 'Company Name' },
        placeholder: { zh: '请输入公司名称', en: 'Enter company name' },
        required: true,
        validation: { minLength: 2, maxLength: 100 }
      },
      {
        name: 'stage',
        type: 'select',
        label: { zh: '融资阶段', en: 'Funding Stage' },
        required: true,
        options: [
          { value: 'seed', label: { zh: '种子轮', en: 'Seed' } },
          { value: 'angel', label: { zh: '天使轮', en: 'Angel' } },
          { value: 'pre-a', label: { zh: 'Pre-A轮', en: 'Pre-A' } },
          { value: 'series-a', label: { zh: 'A轮', en: 'Series A' } }
        ]
      },
      {
        name: 'industry',
        type: 'select',
        label: { zh: '所属行业', en: 'Industry' },
        required: true,
        options: [
          { value: 'ai', label: { zh: '人工智能', en: 'AI' } },
          { value: 'enterprise', label: { zh: '企业服务', en: 'Enterprise' } },
          { value: 'consumer', label: { zh: '消费品', en: 'Consumer' } },
          { value: 'fintech', label: { zh: '金融科技', en: 'Fintech' } },
          { value: 'healthcare', label: { zh: '医疗健康', en: 'Healthcare' } },
          { value: 'education', label: { zh: '教育', en: 'Education' } },
          { value: 'other', label: { zh: '其他', en: 'Other' } }
        ]
      },
      {
        name: 'bp_file',
        type: 'file',
        label: { zh: '商业计划书 (可选)', en: 'Business Plan (Optional)' },
        required: false,
        accept: '.pdf,.doc,.docx,.ppt,.pptx'
      },
      {
        name: 'team_size',
        type: 'number',
        label: { zh: '团队规模', en: 'Team Size' },
        placeholder: { zh: '核心团队人数', en: 'Core team members' },
        required: false,
        validation: { min: 1, max: 200 }
      }
    ],

    // 模式配置
    modes: {
      quick: {
        duration: 240, // 秒 (4分钟)
        label: { zh: '快速分析', en: 'Quick Analysis' },
        description: { zh: '3-5分钟快速评估，适合初筛', en: '3-5 min rapid assessment' }
      },
      standard: {
        duration: 720, // 秒 (12分钟)
        label: { zh: '标准分析', en: 'Standard Analysis' },
        description: { zh: '10-15分钟全面尽调，包含详细分析', en: '10-15 min comprehensive analysis' }
      }
    }
  },

  // ============================================
  // 成长期投资分析 (Growth Investment)
  // ============================================
  GROWTH: {
    id: 'growth-investment',
    name: {
      zh: '成长期项目投资分析',
      en: 'Growth Stage Investment Analysis'
    },
    description: {
      zh: '适用于A轮、B轮、C轮成长期项目的投资分析',
      en: 'Investment analysis for Series A, B, C growth stage projects'
    },
    icon: '📈',
    category: 'venture',

    stages: ['series-a', 'series-b', 'series-c', 'series-d+'],

    focus: {
      zh: ['市场地位 (40%)', '财务数据 (35%)', '增长潜力 (25%)'],
      en: ['Market Position (40%)', 'Financials (35%)', 'Growth (25%)']
    },

    formFields: [
      {
        name: 'company_name',
        type: 'text',
        label: { zh: '公司名称', en: 'Company Name' },
        placeholder: { zh: '请输入公司名称', en: 'Enter company name' },
        required: true,
        validation: { minLength: 2, maxLength: 100 }
      },
      {
        name: 'stage',
        type: 'select',
        label: { zh: '融资阶段', en: 'Funding Stage' },
        required: true,
        options: [
          { value: 'series-a', label: { zh: 'A轮', en: 'Series A' } },
          { value: 'series-b', label: { zh: 'B轮', en: 'Series B' } },
          { value: 'series-c', label: { zh: 'C轮', en: 'Series C' } },
          { value: 'series-d+', label: { zh: 'D轮及以后', en: 'Series D+' } }
        ]
      },
      {
        name: 'revenue',
        type: 'number',
        label: { zh: '年营收（万元）', en: 'Annual Revenue (10k CNY)' },
        placeholder: { zh: '最近一年营收', en: 'Latest annual revenue' },
        required: false,
        validation: { min: 0 }
      },
      {
        name: 'growth_rate',
        type: 'number',
        label: { zh: '增长率 (%)', en: 'Growth Rate (%)' },
        placeholder: { zh: '年复合增长率', en: 'YoY growth rate' },
        required: false,
        validation: { min: -100, max: 1000 }
      },
      {
        name: 'bp_file',
        type: 'file',
        label: { zh: '商业计划书 (可选)', en: 'Business Plan (Optional)' },
        required: false,
        accept: '.pdf,.doc,.docx,.ppt,.pptx'
      }
    ],

    modes: {
      quick: {
        duration: 255,
        label: { zh: '快速分析', en: 'Quick Analysis' },
        description: { zh: '4-5分钟快速评估', en: '4-5 min assessment' }
      },
      standard: {
        duration: 810,
        label: { zh: '标准分析', en: 'Standard Analysis' },
        description: { zh: '13-15分钟全面分析', en: '13-15 min analysis' }
      }
    }
  },

  // ============================================
  // 公开市场投资分析 (Public Market)
  // ============================================
  PUBLIC_MARKET: {
    id: 'public-market-investment',
    name: {
      zh: '公开市场投资分析',
      en: 'Public Market Investment Analysis'
    },
    description: {
      zh: '适用于二级市场上市公司的投资分析',
      en: 'Investment analysis for publicly traded companies'
    },
    icon: '📊',
    category: 'public',

    stages: ['ipo', 'listed'],

    focus: {
      zh: ['财务表现 (50%)', '市场估值 (30%)', '风险控制 (20%)'],
      en: ['Financials (50%)', 'Valuation (30%)', 'Risk (20%)']
    },

    formFields: [
      {
        name: 'company_name',
        type: 'text',
        label: { zh: '公司名称', en: 'Company Name' },
        placeholder: { zh: '请输入公司名称', en: 'Enter company name' },
        required: true,
        validation: { minLength: 2, maxLength: 100 }
      },
      {
        name: 'stock_code',
        type: 'text',
        label: { zh: '股票代码', en: 'Stock Code' },
        placeholder: { zh: '例如: 600000', en: 'e.g., 600000' },
        required: false,
        validation: { pattern: '^[A-Z0-9]{4,10}$' }
      },
      {
        name: 'market',
        type: 'select',
        label: { zh: '交易市场', en: 'Market' },
        required: true,
        options: [
          { value: 'sse', label: { zh: '上海证券交易所', en: 'Shanghai Stock Exchange' } },
          { value: 'szse', label: { zh: '深圳证券交易所', en: 'Shenzhen Stock Exchange' } },
          { value: 'hkex', label: { zh: '香港交易所', en: 'Hong Kong Exchange' } },
          { value: 'nasdaq', label: { zh: '纳斯达克', en: 'NASDAQ' } },
          { value: 'nyse', label: { zh: '纽交所', en: 'NYSE' } },
          { value: 'other', label: { zh: '其他', en: 'Other' } }
        ]
      }
    ],

    modes: {
      quick: {
        duration: 180,
        label: { zh: '快速分析', en: 'Quick Analysis' },
        description: { zh: '3分钟快速评估', en: '3 min assessment' }
      },
      standard: {
        duration: 510,
        label: { zh: '标准分析', en: 'Standard Analysis' },
        description: { zh: '8-10分钟详细分析', en: '8-10 min analysis' }
      }
    }
  },

  // ============================================
  // 另类投资分析 (Alternative Investment)
  // ============================================
  ALTERNATIVE: {
    id: 'alternative-investment',
    name: {
      zh: '另类投资分析',
      en: 'Alternative Investment Analysis'
    },
    description: {
      zh: '适用于PE/VC基金、房地产、大宗商品等另类投资标的',
      en: 'Analysis for alternative investments like PE/VC funds, real estate, commodities'
    },
    icon: '💎',
    category: 'alternative',

    stages: ['fund', 'real-estate', 'commodity'],

    focus: {
      zh: ['市场趋势 (40%)', '法律合规 (35%)', '风险评估 (25%)'],
      en: ['Market Trends (40%)', 'Legal (35%)', 'Risk (25%)']
    },

    formFields: [
      {
        name: 'target_name',
        type: 'text',
        label: { zh: '投资标的名称', en: 'Target Name' },
        placeholder: { zh: '基金/项目名称', en: 'Fund/Project name' },
        required: true,
        validation: { minLength: 2, maxLength: 100 }
      },
      {
        name: 'investment_type',
        type: 'select',
        label: { zh: '投资类型', en: 'Investment Type' },
        required: true,
        options: [
          { value: 'pe-fund', label: { zh: 'PE基金', en: 'PE Fund' } },
          { value: 'vc-fund', label: { zh: 'VC基金', en: 'VC Fund' } },
          { value: 'real-estate', label: { zh: '房地产', en: 'Real Estate' } },
          { value: 'commodity', label: { zh: '大宗商品', en: 'Commodity' } },
          { value: 'other', label: { zh: '其他', en: 'Other' } }
        ]
      },
      {
        name: 'bp_file',
        type: 'file',
        label: { zh: '投资文档 (可选)', en: 'Investment Document (Optional)' },
        required: false,
        accept: '.pdf,.doc,.docx'
      }
    ],

    modes: {
      quick: {
        duration: 215,
        label: { zh: '快速分析', en: 'Quick Analysis' },
        description: { zh: '3-4分钟快速评估', en: '3-4 min assessment' }
      },
      standard: {
        duration: 640,
        label: { zh: '标准分析', en: 'Standard Analysis' },
        description: { zh: '10-12分钟详细分析', en: '10-12 min analysis' }
      }
    }
  },

  // ============================================
  // 行业研究分析 (Industry Research)
  // ============================================
  INDUSTRY_RESEARCH: {
    id: 'industry-research',
    name: {
      zh: '行业研究分析',
      en: 'Industry Research Analysis'
    },
    description: {
      zh: '适用于行业趋势研究、赛道分析等宏观研究',
      en: 'Analysis for industry trends, sector research, and macro studies'
    },
    icon: '🔍',
    category: 'research',

    stages: ['research'],

    focus: {
      zh: ['市场规模 (40%)', '技术趋势 (35%)', '竞争格局 (25%)'],
      en: ['Market Size (40%)', 'Tech Trends (35%)', 'Competition (25%)']
    },

    formFields: [
      {
        name: 'industry_name',
        type: 'text',
        label: { zh: '行业名称', en: 'Industry Name' },
        placeholder: { zh: '例如: 人工智能', en: 'e.g., Artificial Intelligence' },
        required: true,
        validation: { minLength: 2, maxLength: 50 }
      },
      {
        name: 'sub_sector',
        type: 'text',
        label: { zh: '细分赛道 (可选)', en: 'Sub-sector (Optional)' },
        placeholder: { zh: '例如: 大模型', en: 'e.g., LLM' },
        required: false,
        validation: { maxLength: 50 }
      },
      {
        name: 'region',
        type: 'select',
        label: { zh: '研究区域', en: 'Region' },
        required: true,
        options: [
          { value: 'china', label: { zh: '中国', en: 'China' } },
          { value: 'us', label: { zh: '美国', en: 'United States' } },
          { value: 'global', label: { zh: '全球', en: 'Global' } },
          { value: 'asia', label: { zh: '亚洲', en: 'Asia' } },
          { value: 'europe', label: { zh: '欧洲', en: 'Europe' } }
        ]
      }
    ],

    modes: {
      quick: {
        duration: 195,
        label: { zh: '快速分析', en: 'Quick Analysis' },
        description: { zh: '3分钟快速概览', en: '3 min overview' }
      },
      standard: {
        duration: 570,
        label: { zh: '标准分析', en: 'Standard Analysis' },
        description: { zh: '9-10分钟深度研究', en: '9-10 min deep dive' }
      }
    }
  }
}

/**
 * 获取所有场景列表
 */
export function getAllScenarios() {
  return Object.values(SCENARIOS)
}

/**
 * 根据ID获取场景配置
 */
export function getScenarioById(id) {
  return Object.values(SCENARIOS).find(s => s.id === id)
}

/**
 * 根据分类获取场景列表
 */
export function getScenariosByCategory(category) {
  return Object.values(SCENARIOS).filter(s => s.category === category)
}

/**
 * 获取场景的表单字段（支持国际化）
 */
export function getScenarioFormFields(scenarioId, language = 'zh') {
  const scenario = getScenarioById(scenarioId)
  if (!scenario) return []

  return scenario.formFields.map(field => ({
    ...field,
    label: field.label[language] || field.label.zh,
    placeholder: field.placeholder?.[language] || field.placeholder?.zh,
    options: field.options?.map(opt => ({
      ...opt,
      label: opt.label[language] || opt.label.zh
    }))
  }))
}

export default SCENARIOS
