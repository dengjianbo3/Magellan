/**
 * 场景ID映射配置
 * 将前端场景ID映射到后端API枚举值
 */

export const SCENARIO_MAPPING = {
  // 前端ID -> 后端枚举值
  'early_stage_dd': 'early-stage-investment',
  'growth_stage_dd': 'growth-investment',
  'public_market_dd': 'public-market-investment',
  'alternative_investment_dd': 'alternative-investment',
  'industry_research': 'industry-research'
};

export const REVERSE_SCENARIO_MAPPING = {
  // 后端枚举值 -> 前端ID
  'early-stage-investment': 'early_stage_dd',
  'growth-investment': 'growth_stage_dd',
  'public-market-investment': 'public_market_dd',
  'alternative-investment': 'alternative_investment_dd',
  'industry-research': 'industry_research'
};

/**
 * 将前端场景ID转换为后端枚举值
 * @param {string} frontendId - 前端场景ID
 * @returns {string} 后端枚举值
 */
export function toBackendScenario(frontendId) {
  const backendScenario = SCENARIO_MAPPING[frontendId];
  if (!backendScenario) {
    console.warn(`[ScenarioMapping] Unknown frontend scenario ID: ${frontendId}`);
    return frontendId;
  }
  return backendScenario;
}

/**
 * 将后端枚举值转换为前端场景ID
 * @param {string} backendScenario - 后端枚举值
 * @returns {string} 前端场景ID
 */
export function toFrontendScenario(backendScenario) {
  const frontendId = REVERSE_SCENARIO_MAPPING[backendScenario];
  if (!frontendId) {
    console.warn(`[ScenarioMapping] Unknown backend scenario: ${backendScenario}`);
    return backendScenario;
  }
  return frontendId;
}

/**
 * 生成项目名称
 * @param {Object} target - 目标对象
 * @param {string} scenarioId - 场景ID
 * @returns {string} 项目名称
 */
export function generateProjectName(target, scenarioId) {
  if (!target) return 'Unknown Project';

  switch (scenarioId) {
    case 'early_stage_dd':
    case 'growth_stage_dd':
      return target.company_name || 'Unnamed Company';

    case 'public_market_dd':
      return `${target.ticker || 'Unknown'} 投资分析`;

    case 'alternative_investment_dd':
      return `${target.project_name || target.symbol || 'Unknown'} 分析`;

    case 'industry_research':
      return target.industry_name || target.research_topic || 'Industry Research';

    default:
      return 'Investment Analysis';
  }
}
