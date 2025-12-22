/**
 * AI Agents Configuration
 * 系统中所有可用的AI智能体配置
 */

export const AGENTS_CONFIG = [
  {
    id: 'market-analyst',
    name: 'Market Analyst',
    name_zh: '市场分析师',
    role: 'Market Intelligence',
    role_zh: '市场情报',
    icon: 'show_chart',
    description: 'Analyzes market trends, competition, and industry dynamics with deep market research capabilities.',
    description_zh: '分析市场趋势、竞争和行业动态，具有深度市场研究能力',
    capabilities: ['Market Research', 'Competitor Analysis', 'Trend Forecasting'],
    status: 'active',
    analysisCount: 156,
    avgResponse: '2.3s'
  },
  {
    id: 'financial-expert',
    name: 'Financial Expert',
    name_zh: '财务专家',
    role: 'Financial Analysis',
    role_zh: '财务分析',
    icon: 'account_balance',
    description: 'Reviews financial statements, calculates key ratios, and performs valuation analysis.',
    description_zh: '审查财务报表，计算关键比率，进行估值分析',
    capabilities: ['Financial Modeling', 'Ratio Analysis', 'Valuation'],
    status: 'active',
    analysisCount: 142,
    avgResponse: '3.1s'
  },
  {
    id: 'team-evaluator',
    name: 'Team Evaluator',
    name_zh: '团队评估师',
    role: 'Team Assessment',
    role_zh: '团队评估',
    icon: 'groups',
    description: 'Evaluates management team quality, organizational structure, and company culture.',
    description_zh: '评估管理团队质量、组织结构和公司文化',
    capabilities: ['Leadership Analysis', 'Culture Assessment', 'HR Review'],
    status: 'active',
    analysisCount: 98,
    avgResponse: '2.8s'
  },
  {
    id: 'risk-assessor',
    name: 'Risk Assessor',
    name_zh: '风险评估师',
    role: 'Risk Management',
    role_zh: '风险管理',
    icon: 'shield',
    description: 'Identifies potential risks, evaluates their impact, and suggests mitigation strategies.',
    description_zh: '识别潜在风险，评估其影响，并提出缓解策略',
    capabilities: ['Risk Identification', 'Impact Analysis', 'Mitigation Planning'],
    status: 'active',
    analysisCount: 134,
    avgResponse: '2.5s'
  },
  {
    id: 'tech-specialist',
    name: 'Tech Specialist',
    name_zh: '技术专家',
    role: 'Technology Review',
    role_zh: '技术审查',
    icon: 'computer',
    description: 'Assesses technology stack, innovation capabilities, and technical debt.',
    description_zh: '评估技术栈、创新能力和技术债务',
    capabilities: ['Tech Stack Review', 'Innovation Assessment', 'IP Analysis'],
    status: 'active',
    analysisCount: 67,
    avgResponse: '4.2s'
  },
  {
    id: 'legal-advisor',
    name: 'Legal Advisor',
    name_zh: '法律顾问',
    role: 'Legal Compliance',
    role_zh: '法律合规',
    icon: 'gavel',
    description: 'Reviews legal structure, compliance status, and regulatory requirements.',
    description_zh: '审查法律结构、合规状态和监管要求',
    capabilities: ['Compliance Review', 'Contract Analysis', 'Regulatory Assessment'],
    status: 'active',
    analysisCount: 45,
    avgResponse: '3.8s'
  },
  {
    id: 'technical-analyst',
    name: 'Technical Analyst',
    name_zh: '技术分析师',
    role: 'Technical Analysis',
    role_zh: '技术面分析',
    icon: 'candlestick_chart',
    description: 'Performs K-line pattern analysis, calculates technical indicators (RSI, MACD, Bollinger Bands), identifies support/resistance levels, and provides trading signals.',
    description_zh: '进行K线形态分析，计算技术指标（RSI、MACD、布林带等），识别支撑阻力位，提供交易信号',
    capabilities: ['K-Line Patterns', 'Technical Indicators', 'Support/Resistance', 'Trading Signals'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '2.0s'
  },
  {
    id: 'macro-economist',
    name: 'Macro Economist',
    name_zh: '宏观经济分析师',
    role: 'Macro Analysis',
    role_zh: '宏观分析',
    icon: 'public',
    description: 'Analyzes macroeconomic trends, monetary policies, GDP growth, inflation, and global economic cycles to assess investment environment.',
    description_zh: '分析宏观经济趋势、货币政策、GDP增长、通胀及全球经济周期，评估投资环境',
    capabilities: ['Macro Trends', 'Policy Analysis', 'Economic Cycles', 'Global Markets'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '2.5s'
  },
  {
    id: 'esg-analyst',
    name: 'ESG Analyst',
    name_zh: 'ESG分析师',
    role: 'ESG Assessment',
    role_zh: 'ESG评估',
    icon: 'eco',
    description: 'Evaluates Environmental, Social, and Governance factors, sustainability practices, carbon footprint, and corporate responsibility.',
    description_zh: '评估环境、社会和治理因素，可持续发展实践，碳足迹及企业社会责任',
    capabilities: ['ESG Scoring', 'Sustainability', 'Carbon Analysis', 'Governance Review'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '2.8s'
  },
  {
    id: 'sentiment-analyst',
    name: 'Sentiment Analyst',
    name_zh: '情绪分析师',
    role: 'Sentiment Analysis',
    role_zh: '情绪分析',
    icon: 'psychology',
    description: 'Monitors market sentiment through news, social media, analyst ratings, and investor behavior patterns.',
    description_zh: '通过新闻、社交媒体、分析师评级和投资者行为模式监测市场情绪',
    capabilities: ['News Sentiment', 'Social Media', 'Analyst Ratings', 'Behavior Patterns'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '2.2s'
  },
  {
    id: 'quant-strategist',
    name: 'Quant Strategist',
    name_zh: '量化策略师',
    role: 'Quantitative Analysis',
    role_zh: '量化分析',
    icon: 'analytics',
    description: 'Develops quantitative models, performs statistical analysis, backtesting strategies, and factor-based investing research.',
    description_zh: '开发量化模型，进行统计分析、策略回测及因子投资研究',
    capabilities: ['Quant Models', 'Statistical Analysis', 'Backtesting', 'Factor Investing'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '3.5s'
  },
  {
    id: 'deal-structurer',
    name: 'Deal Structurer',
    name_zh: '交易结构师',
    role: 'Deal Structuring',
    role_zh: '交易结构',
    icon: 'handshake',
    description: 'Designs optimal deal structures, financing arrangements, term sheets, and transaction mechanics.',
    description_zh: '设计最优交易结构、融资安排、条款清单及交易机制',
    capabilities: ['Deal Structure', 'Financing', 'Term Sheets', 'Transaction Design'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '3.0s'
  },
  {
    id: 'ma-advisor',
    name: 'M&A Advisor',
    name_zh: '并购顾问',
    role: 'M&A Advisory',
    role_zh: '并购咨询',
    icon: 'merge_type',
    description: 'Provides M&A strategy, target screening, synergy analysis, and post-merger integration planning.',
    description_zh: '提供并购策略、标的筛选、协同效应分析及并购后整合规划',
    capabilities: ['M&A Strategy', 'Target Screening', 'Synergy Analysis', 'PMI Planning'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '3.2s'
  },
  {
    id: 'onchain-analyst',
    name: 'Onchain Analyst',
    name_zh: '链上分析师',
    role: 'Onchain Analysis',
    role_zh: '链上分析',
    icon: 'link',
    description: 'Analyzes blockchain on-chain data including whale wallet movements, exchange fund flows, DeFi TVL changes, and smart money flows.',
    description_zh: '分析区块链链上数据，包括巨鲸地址动向、交易所资金流向、DeFi协议TVL变化和智能货币流动',
    capabilities: ['Whale Tracking', 'Exchange Flows', 'DeFi TVL', 'Smart Money'],
    status: 'active',
    analysisCount: 0,
    avgResponse: '2.5s'
  },
  {
    id: 'leader',
    name: 'Discussion Leader',
    name_zh: '讨论主持人',
    role: 'Facilitation',
    role_zh: '主持协调',
    icon: 'emoji_events',
    description: 'Leads the roundtable discussion, coordinates between experts, and ensures productive dialogue.',
    description_zh: '主持圆桌讨论，协调各专家之间的对话，确保讨论富有成效',
    capabilities: ['Facilitation', 'Coordination', 'Synthesis'],
    status: 'active',
    analysisCount: 89,
    avgResponse: '1.8s'
  }
];

/**
 * Get agents filtered by status
 * @param {string} status - 'active' or 'inactive'
 * @returns {Array} Filtered agents
 */
export function getAgentsByStatus(status = 'active') {
  return AGENTS_CONFIG.filter(agent => agent.status === status);
}

/**
 * Get agent by ID
 * @param {string} id - Agent ID
 * @returns {Object|null} Agent object or null
 */
export function getAgentById(id) {
  return AGENTS_CONFIG.find(agent => agent.id === id) || null;
}

/**
 * Get agents suitable for roundtable (active agents)
 * @returns {Array} Active agents
 */
export function getRoundtableAgents() {
  return getAgentsByStatus('active');
}
