/**
 * Scenario ID Mapper - Stage 2
 * 统一前端和后端的场景ID格式
 *
 * 问题: 前端使用 early_stage_dd, 后端使用 early-stage-investment
 * 解决: 提供双向映射工具
 */

/**
 * 前端场景ID到后端场景ID的映射
 */
const FRONTEND_TO_BACKEND = {
  // 早期投资尽调
  'early_stage_dd': 'early-stage-investment',
  'early-stage-dd': 'early-stage-investment',
  'early_stage': 'early-stage-investment',

  // 成长期投资
  'growth_investment': 'growth-investment',
  'growth': 'growth-investment',

  // 二级市场投资
  'public_market': 'public-market-investment',
  'public-market': 'public-market-investment',
  'public': 'public-market-investment',

  // 另类投资
  'alternative': 'alternative-investment',
  'alternative_investment': 'alternative-investment',

  // 行业研究
  'industry_research': 'industry-research',
  'industry': 'industry-research'
};

/**
 * 后端场景ID到前端场景ID的映射
 */
const BACKEND_TO_FRONTEND = {
  'early-stage-investment': 'early_stage_dd',
  'growth-investment': 'growth_investment',
  'public-market-investment': 'public_market',
  'alternative-investment': 'alternative',
  'industry-research': 'industry_research'
};

/**
 * 场景显示名称(中文)
 */
const SCENARIO_DISPLAY_NAMES = {
  'early-stage-investment': '早期投资尽调',
  'growth-investment': '成长期投资',
  'public-market-investment': '二级市场投资',
  'alternative-investment': '另类投资',
  'industry-research': '行业研究'
};

/**
 * 场景显示名称(英文)
 */
const SCENARIO_DISPLAY_NAMES_EN = {
  'early-stage-investment': 'Early Stage Investment DD',
  'growth-investment': 'Growth Investment',
  'public-market-investment': 'Public Market Investment',
  'alternative-investment': 'Alternative Investment',
  'industry-research': 'Industry Research'
};

/**
 * 将前端场景ID转换为后端场景ID
 * @param {string} frontendId - 前端场景ID
 * @returns {string} 后端场景ID
 */
export function toBackendScenario(frontendId) {
  if (!frontendId) {
    console.warn('[ScenarioMapper] Empty frontend scenario ID');
    return null;
  }

  const backendId = FRONTEND_TO_BACKEND[frontendId];

  if (!backendId) {
    // 如果没有映射,检查是否已经是后端格式
    if (Object.values(BACKEND_TO_FRONTEND).includes(frontendId)) {
      console.warn('[ScenarioMapper] ID already in backend format:', frontendId);
      return frontendId;
    }

    console.error('[ScenarioMapper] Unknown frontend scenario ID:', frontendId);
    return frontendId; // 返回原值,让后端处理错误
  }

  console.log(`[ScenarioMapper] ${frontendId} → ${backendId}`);
  return backendId;
}

/**
 * 将后端场景ID转换为前端场景ID
 * @param {string} backendId - 后端场景ID
 * @returns {string} 前端场景ID
 */
export function toFrontendScenario(backendId) {
  if (!backendId) {
    console.warn('[ScenarioMapper] Empty backend scenario ID');
    return null;
  }

  const frontendId = BACKEND_TO_FRONTEND[backendId];

  if (!frontendId) {
    // 如果没有映射,检查是否已经是前端格式
    if (Object.keys(FRONTEND_TO_BACKEND).includes(backendId)) {
      console.warn('[ScenarioMapper] ID already in frontend format:', backendId);
      return backendId;
    }

    console.error('[ScenarioMapper] Unknown backend scenario ID:', backendId);
    return backendId; // 返回原值
  }

  console.log(`[ScenarioMapper] ${backendId} → ${frontendId}`);
  return frontendId;
}

/**
 * 获取场景的显示名称
 * @param {string} scenarioId - 场景ID (前端或后端格式均可)
 * @param {string} locale - 语言 ('zh' 或 'en')
 * @returns {string} 显示名称
 */
export function getScenarioDisplayName(scenarioId, locale = 'zh') {
  if (!scenarioId) {
    return '';
  }

  // 统一转换为后端格式
  const backendId = toBackendScenario(scenarioId) || scenarioId;

  const names = locale === 'en' ? SCENARIO_DISPLAY_NAMES_EN : SCENARIO_DISPLAY_NAMES;
  return names[backendId] || scenarioId;
}

/**
 * 验证场景ID是否有效
 * @param {string} scenarioId - 场景ID
 * @returns {boolean} 是否有效
 */
export function isValidScenario(scenarioId) {
  if (!scenarioId) {
    return false;
  }

  // 检查是否在前端或后端映射中
  return (
    Object.keys(FRONTEND_TO_BACKEND).includes(scenarioId) ||
    Object.keys(BACKEND_TO_FRONTEND).includes(scenarioId)
  );
}

/**
 * 获取所有支持的场景列表
 * @param {string} format - 返回格式 ('frontend' 或 'backend')
 * @returns {Array} 场景ID列表
 */
export function getAllScenarios(format = 'backend') {
  if (format === 'frontend') {
    return Object.values(BACKEND_TO_FRONTEND);
  }
  return Object.keys(BACKEND_TO_FRONTEND);
}

/**
 * 获取场景信息对象
 * @param {string} scenarioId - 场景ID (前端或后端格式均可)
 * @returns {Object} 场景信息
 */
export function getScenarioInfo(scenarioId) {
  const backendId = toBackendScenario(scenarioId) || scenarioId;
  const frontendId = toFrontendScenario(backendId) || scenarioId;

  return {
    backendId,
    frontendId,
    displayNameZh: SCENARIO_DISPLAY_NAMES[backendId] || backendId,
    displayNameEn: SCENARIO_DISPLAY_NAMES_EN[backendId] || backendId,
    isValid: isValidScenario(scenarioId)
  };
}

// 导出常量供外部使用
export {
  FRONTEND_TO_BACKEND,
  BACKEND_TO_FRONTEND,
  SCENARIO_DISPLAY_NAMES,
  SCENARIO_DISPLAY_NAMES_EN
};
