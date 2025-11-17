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
