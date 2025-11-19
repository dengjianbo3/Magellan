<template>
  <div class="step-result-card">
    <!-- 市场规模结果 -->
    <div v-if="isMarketSizeResult" class="result-content market-size">
      <div class="metrics-grid">
        <div class="metric-item">
          <span class="metric-label">{{ t('analysisWizard.tam') }}</span>
          <span class="metric-value">{{ result.tam || 'N/A' }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">{{ t('analysisWizard.sam') }}</span>
          <span class="metric-value">{{ result.sam || 'N/A' }}</span>
        </div>
        <div class="metric-item highlight">
          <span class="metric-label">{{ t('analysisWizard.growthRate') }}</span>
          <span class="metric-value">{{ result.growth_rate || 'N/A' }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">{{ t('analysisWizard.marketMaturity') }}</span>
          <span class="metric-value">{{ result.market_maturity || 'N/A' }}</span>
        </div>
      </div>
      <div v-if="result.score" class="score-badge" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 竞争格局结果 -->
    <div v-else-if="isCompetitionResult" class="result-content competition">
      <div v-if="result.top_players && result.top_players.length" class="players-section">
        <div class="section-label">{{ t('analysisWizard.topPlayers') }}</div>
        <div class="players-list">
          <div v-for="(player, idx) in result.top_players" :key="idx" class="player-item">
            <template v-if="typeof player === 'object'">
              <span class="player-name">{{ player.name }}</span>
              <span v-if="player.market_share" class="player-share">{{ player.market_share }}</span>
            </template>
            <template v-else>
              <span class="player-name">{{ player }}</span>
            </template>
          </div>
        </div>
      </div>
      <div class="metrics-grid compact">
        <div class="metric-item">
          <span class="metric-label">{{ t('analysisWizard.marketConcentration') }}</span>
          <span class="metric-value">{{ result.market_concentration || 'N/A' }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">{{ t('analysisWizard.entryBarriers') }}</span>
          <span class="metric-value">{{ result.entry_barriers || 'N/A' }}</span>
        </div>
      </div>
      <div v-if="result.score" class="score-badge" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 趋势分析结果 -->
    <div v-else-if="isTrendResult" class="result-content trend">
      <div v-if="result.key_trends && result.key_trends.length" class="trends-section">
        <div class="section-label">{{ t('analysisWizard.keyTrends') }}</div>
        <div class="trends-list">
          <span v-for="(trend, idx) in result.key_trends" :key="idx" class="trend-tag">
            {{ typeof trend === 'object' ? trend.trend || trend.name : trend }}
          </span>
        </div>
      </div>
      <div class="metrics-grid compact">
        <div class="metric-item">
          <span class="metric-label">{{ t('analysisWizard.techDirection') }}</span>
          <span class="metric-value">{{ result.tech_direction || 'N/A' }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">{{ t('analysisWizard.policySupport') }}</span>
          <span class="metric-value">{{ result.policy_support || 'N/A' }}</span>
        </div>
      </div>
      <div v-if="result.score" class="score-badge" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 机会扫描结果 -->
    <div v-else-if="isOpportunityResult" class="result-content opportunity">
      <div v-if="result.opportunities && result.opportunities.length" class="opportunities-section">
        <div class="section-label">{{ t('analysisWizard.investmentOpportunities') }}</div>
        <ul class="opportunities-list">
          <li v-for="(opp, idx) in result.opportunities" :key="idx">
            <template v-if="typeof opp === 'object'">
              <strong>{{ opp.name }}</strong>
              <span v-if="opp.potential" class="opp-potential">({{ opp.potential }})</span>
              <div v-if="opp.description" class="opp-desc">{{ opp.description }}</div>
            </template>
            <template v-else>{{ opp }}</template>
          </li>
        </ul>
      </div>
      <div v-if="result.sub_sectors && result.sub_sectors.length" class="subsectors-section">
        <div class="section-label">{{ t('analysisWizard.subSectors') }}</div>
        <div class="subsector-tags">
          <span v-for="(sector, idx) in result.sub_sectors" :key="idx" class="subsector-tag">
            {{ sector }}
          </span>
        </div>
      </div>
      <div v-if="result.score" class="score-badge" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 通用结果展示 -->
    <div v-else class="result-content generic">
      <div v-if="result.summary" class="summary-text">
        {{ result.summary }}
      </div>
      <div v-if="hasOtherFields" class="other-fields">
        <div v-for="(value, key) in otherFields" :key="key" class="field-row">
          <span class="field-label">{{ formatLabel(key) }}</span>
          <span class="field-value">{{ formatValue(value) }}</span>
        </div>
      </div>
      <div v-if="result.score" class="score-badge" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';

const { t } = useLanguage();

const props = defineProps({
  result: {
    type: Object,
    required: true
  },
  stepType: {
    type: String,
    default: ''
  }
});

// 判断结果类型
const isMarketSizeResult = computed(() => {
  return props.stepType === 'market_size_check' ||
         (props.result.tam || props.result.sam || props.result.growth_rate);
});

const isCompetitionResult = computed(() => {
  return props.stepType === 'competition_landscape' ||
         (props.result.top_players || props.result.market_concentration);
});

const isTrendResult = computed(() => {
  return props.stepType === 'trend_analysis' ||
         (props.result.key_trends || props.result.tech_direction);
});

const isOpportunityResult = computed(() => {
  return props.stepType === 'opportunity_scan' ||
         (props.result.opportunities || props.result.sub_sectors);
});

// 提取其他字段
const otherFields = computed(() => {
  const excludeKeys = ['score', 'summary', 'tam', 'sam', 'growth_rate', 'market_maturity',
                       'top_players', 'market_concentration', 'entry_barriers',
                       'key_trends', 'tech_direction', 'policy_support',
                       'opportunities', 'sub_sectors', 'innovations'];
  const fields = {};
  for (const [key, value] of Object.entries(props.result)) {
    if (!excludeKeys.includes(key) && value !== null && value !== undefined) {
      fields[key] = value;
    }
  }
  return fields;
});

const hasOtherFields = computed(() => {
  return Object.keys(otherFields.value).length > 0;
});

function getScoreClass(score) {
  if (score >= 0.8) return 'excellent';
  if (score >= 0.6) return 'good';
  if (score >= 0.4) return 'fair';
  return 'poor';
}

function formatLabel(key) {
  const labelMap = {
    'revenue_assessment': t('analysisWizard.revenueAssessment'),
    'cash_flow': t('analysisWizard.cashFlow'),
    'profitability': t('analysisWizard.profitability'),
    'concerns': t('analysisWizard.concernsLabel'),
    'valuation_level': t('analysisWizard.valuationLevel'),
    'pe_ratio': t('analysisWizard.peRatio'),
    'price_target': t('analysisWizard.priceTarget')
  };
  return labelMap[key] || key.replace(/_/g, ' ');
}

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}
</script>

<style scoped>
.step-result-card {
  margin-top: 12px;
}

.result-content {
  position: relative;
  padding: 16px;
  background: var(--result-bg, rgba(59, 130, 246, 0.08));
  border-radius: 8px;
  border-left: 3px solid var(--primary-color, #3b82f6);
}

/* 指标网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.metrics-grid.compact {
  margin-top: 12px;
  margin-bottom: 0;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 11px;
  color: var(--text-secondary, #a1a1a1);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #e5e5e5);
  line-height: 1.3;
}

.metric-item.highlight .metric-value {
  color: var(--success-color, #10b981);
  font-weight: 600;
}

/* 评分徽章 */
.score-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.score-badge.excellent {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.score-badge.good {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.score-badge.fair {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.score-badge.poor {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

/* 区块标签 */
.section-label {
  font-size: 11px;
  color: var(--text-secondary, #a1a1a1);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

/* 玩家列表 */
.players-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.player-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--tag-bg, rgba(255, 255, 255, 0.08));
  border-radius: 4px;
  font-size: 13px;
}

.player-name {
  color: var(--text-primary, #e5e5e5);
  font-weight: 500;
}

.player-share {
  color: var(--text-secondary, #a1a1a1);
  font-size: 11px;
}

/* 趋势标签 */
.trends-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.trend-tag {
  padding: 4px 10px;
  background: var(--tag-bg, rgba(255, 255, 255, 0.08));
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary, #e5e5e5);
}

/* 机会列表 */
.opportunities-list {
  list-style: none;
  padding: 0;
  margin: 0 0 12px 0;
}

.opportunities-list li {
  padding: 6px 0;
  font-size: 13px;
  color: var(--text-primary, #e5e5e5);
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
  line-height: 1.4;
}

.opportunities-list li:last-child {
  border-bottom: none;
}

.opportunities-list li::before {
  content: "•";
  color: var(--primary-color, #3b82f6);
  margin-right: 8px;
}

.opp-potential {
  margin-left: 6px;
  font-size: 11px;
  color: var(--success-color, #10b981);
  font-weight: 500;
}

.opp-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary, #a1a1a1);
  line-height: 1.4;
  padding-left: 0;
}

/* 细分赛道标签 */
.subsector-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.subsector-tag {
  padding: 4px 10px;
  background: var(--primary-color, #3b82f6);
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

/* 通用字段 */
.summary-text {
  font-size: 13px;
  color: var(--text-primary, #e5e5e5);
  line-height: 1.5;
  margin-bottom: 12px;
}

.other-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.field-label {
  color: var(--text-secondary, #a1a1a1);
}

.field-value {
  color: var(--text-primary, #e5e5e5);
  font-weight: 500;
  text-align: right;
}

/* 深色主题变量 */
:root {
  --result-bg: rgba(59, 130, 246, 0.08);
  --tag-bg: rgba(255, 255, 255, 0.08);
}
</style>
