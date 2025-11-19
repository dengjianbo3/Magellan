<template>
  <div class="growth-config">
    <!-- Header -->
    <div class="header">
      <div class="header-left">
        <h1>{{ t('growthStage.configTitle') }}</h1>
        <p class="subtitle">{{ t('growthStage.configSubtitle') }}</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-secondary" @click="handleSaveTemplate">
          <span class="material-symbols-outlined">bookmark</span>
          <span>{{ t('common.saveAsTemplate') }}</span>
        </button>
        <button type="button" class="btn-primary" @click="handleStartAnalysis">
          <span class="material-symbols-outlined">play_arrow</span>
          <span>{{ t('common.startAnalysis') }}</span>
        </button>
      </div>
    </div>

    <!-- Configuration Form -->
    <div class="config-form">
      <!-- Growth Model Selection -->
      <div class="config-section expanded">
        <div class="section-header" @click="toggleSection('growthModel')">
          <h3 class="section-title">
            <span class="material-symbols-outlined">insights</span>
            <span>{{ t('growthStage.growthModelSelection') }}</span>
          </h3>
          <span class="material-symbols-outlined chevron">
            {{ expandedSections.growthModel ? 'expand_less' : 'expand_more' }}
          </span>
        </div>

        <div v-show="expandedSections.growthModel" class="section-content">
          <div class="growth-model-options">
            <div
              v-for="model in growthModels"
              :key="model.value"
              :class="['model-option', { 'selected': config.growth_model === model.value }]"
              @click="config.growth_model = model.value"
            >
              <div class="model-header">
                <div class="radio-wrapper">
                  <input
                    type="radio"
                    :id="`model-${model.value}`"
                    :value="model.value"
                    v-model="config.growth_model"
                  />
                  <label :for="`model-${model.value}`" class="model-name">
                    {{ t(model.nameKey) }}
                  </label>
                </div>
              </div>
              <p class="model-description">{{ t(model.descKey) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Competition Analysis Focus -->
      <div class="config-section">
        <div class="section-header" @click="toggleSection('competition')">
          <h3 class="section-title">
            <span class="material-symbols-outlined">query_stats</span>
            <span>{{ t('growthStage.competitionAnalysisFocus') }}</span>
          </h3>
          <span class="material-symbols-outlined chevron">
            {{ expandedSections.competition ? 'expand_less' : 'expand_more' }}
          </span>
        </div>

        <div v-show="expandedSections.competition" class="section-content">
          <div class="form-group">
            <label class="form-label">{{ t('growthStage.competitiveAdvantages') }}</label>
            <div class="checkbox-group">
              <label v-for="advantage in competitiveAdvantages" :key="advantage.value" class="checkbox-item">
                <input
                  type="checkbox"
                  :value="advantage.value"
                  v-model="config.competitive_advantages"
                />
                <span>{{ t(advantage.labelKey) }}</span>
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('growthStage.competitionIntensity') }}</label>
            <select v-model="config.competition_intensity" class="form-select">
              <option value="">{{ t('common.pleaseSelect') }}</option>
              <option value="low">{{ t('growthStage.lowCompetition') }}</option>
              <option value="medium">{{ t('growthStage.mediumCompetition') }}</option>
              <option value="high">{{ t('growthStage.highCompetition') }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Market Outlook Assessment -->
      <div class="config-section">
        <div class="section-header" @click="toggleSection('market')">
          <h3 class="section-title">
            <span class="material-symbols-outlined">trending_up</span>
            <span>{{ t('growthStage.marketOutlookAssessment') }}</span>
          </h3>
          <span class="material-symbols-outlined chevron">
            {{ expandedSections.market ? 'expand_less' : 'expand_more' }}
          </span>
        </div>

        <div v-show="expandedSections.market" class="section-content">
          <div class="form-group">
            <label class="form-label">{{ t('growthStage.marketGrowthRate') }}</label>
            <div class="input-with-unit">
              <input
                type="number"
                v-model.number="config.market_growth_rate"
                min="0"
                max="100"
                step="0.1"
                placeholder="15"
              />
              <span class="unit">%</span>
            </div>
            <p class="form-hint">{{ t('growthStage.marketGrowthRateHint') }}</p>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('growthStage.marketMaturity') }}</label>
            <div class="radio-group">
              <label v-for="maturity in marketMaturities" :key="maturity.value" class="radio-item">
                <input
                  type="radio"
                  :value="maturity.value"
                  v-model="config.market_maturity"
                />
                <span>{{ t(maturity.labelKey) }}</span>
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('growthStage.keyMarketDrivers') }}</label>
            <textarea
              v-model="config.key_market_drivers"
              rows="3"
              :placeholder="t('growthStage.keyMarketDriversPlaceholder')"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Financial Projections -->
      <div class="config-section">
        <div class="section-header" @click="toggleSection('financial')">
          <h3 class="section-title">
            <span class="material-symbols-outlined">account_balance</span>
            <span>{{ t('growthStage.financialProjections') }}</span>
          </h3>
          <span class="material-symbols-outlined chevron">
            {{ expandedSections.financial ? 'expand_less' : 'expand_more' }}
          </span>
        </div>

        <div v-show="expandedSections.financial" class="section-content">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">{{ t('growthStage.projectionPeriod') }}</label>
              <select v-model="config.projection_period" class="form-select">
                <option value="">{{ t('common.pleaseSelect') }}</option>
                <option value="3">{{ t('growthStage.threeYears') }}</option>
                <option value="5">{{ t('growthStage.fiveYears') }}</option>
                <option value="10">{{ t('growthStage.tenYears') }}</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">{{ t('growthStage.revenueGrowthAssumption') }}</label>
              <div class="input-with-unit">
                <input
                  type="number"
                  v-model.number="config.revenue_growth_assumption"
                  min="0"
                  max="100"
                  step="0.1"
                  placeholder="25"
                />
                <span class="unit">%</span>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">{{ t('growthStage.profitMarginTarget') }}</label>
              <div class="input-with-unit">
                <input
                  type="number"
                  v-model.number="config.profit_margin_target"
                  min="-100"
                  max="100"
                  step="0.1"
                  placeholder="20"
                />
                <span class="unit">%</span>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">{{ t('growthStage.burnRateAssumption') }}</label>
              <div class="input-with-unit">
                <input
                  type="number"
                  v-model.number="config.burn_rate_assumption"
                  min="0"
                  step="0.1"
                  :placeholder="t('growthStage.monthlyBurnRate')"
                />
                <span class="unit">{{ t('common.millionCurrency') }}</span>
              </div>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('growthStage.keyFinancialMetrics') }}</label>
            <div class="checkbox-group">
              <label v-for="metric in financialMetrics" :key="metric.value" class="checkbox-item">
                <input
                  type="checkbox"
                  :value="metric.value"
                  v-model="config.key_financial_metrics"
                />
                <span>{{ t(metric.labelKey) }}</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="footer-actions">
      <button type="button" class="btn-text" @click="handleBack">
        <span class="material-symbols-outlined">arrow_back</span>
        <span>{{ t('common.back') }}</span>
      </button>
      <button type="button" class="btn-primary" @click="handleStartAnalysis">
        <span class="material-symbols-outlined">play_arrow</span>
        <span>{{ t('common.startAnalysis') }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage';

const { t } = useLanguage();

// Props
const props = defineProps({
  scenario: {
    type: Object,
    required: true
  },
  target: {
    type: Object,
    required: true
  }
});

// Emits
const emit = defineEmits(['config-complete', 'back']);

// State
const expandedSections = ref({
  growthModel: true,
  competition: false,
  market: false,
  financial: false
});

const config = ref({
  growth_model: 's-curve',
  competitive_advantages: [],
  competition_intensity: '',
  market_growth_rate: null,
  market_maturity: '',
  key_market_drivers: '',
  projection_period: '',
  revenue_growth_assumption: null,
  profit_margin_target: null,
  burn_rate_assumption: null,
  key_financial_metrics: []
});

// Growth Models
const growthModels = computed(() => [
  {
    value: 's-curve',
    nameKey: 'growthStage.sCurveGrowth',
    descKey: 'growthStage.sCurveGrowthDesc'
  },
  {
    value: 'linear',
    nameKey: 'growthStage.linearGrowth',
    descKey: 'growthStage.linearGrowthDesc'
  },
  {
    value: 'exponential',
    nameKey: 'growthStage.exponentialGrowth',
    descKey: 'growthStage.exponentialGrowthDesc'
  }
]);

// Competitive Advantages
const competitiveAdvantages = computed(() => [
  { value: 'technology', labelKey: 'growthStage.technologyLeadership' },
  { value: 'brand', labelKey: 'growthStage.brandRecognition' },
  { value: 'network', labelKey: 'growthStage.networkEffects' },
  { value: 'cost', labelKey: 'growthStage.costAdvantage' },
  { value: 'data', labelKey: 'growthStage.dataAdvantage' }
]);

// Market Maturities
const marketMaturities = computed(() => [
  { value: 'emerging', labelKey: 'growthStage.emergingMarket' },
  { value: 'growing', labelKey: 'growthStage.growingMarket' },
  { value: 'mature', labelKey: 'growthStage.matureMarket' }
]);

// Financial Metrics
const financialMetrics = computed(() => [
  { value: 'revenue', labelKey: 'growthStage.revenue' },
  { value: 'gross_margin', labelKey: 'growthStage.grossMargin' },
  { value: 'operating_margin', labelKey: 'growthStage.operatingMargin' },
  { value: 'net_income', labelKey: 'growthStage.netIncome' },
  { value: 'cash_flow', labelKey: 'growthStage.cashFlow' },
  { value: 'customer_acquisition_cost', labelKey: 'growthStage.cac' },
  { value: 'lifetime_value', labelKey: 'growthStage.ltv' },
  { value: 'runway', labelKey: 'growthStage.runway' }
]);

// Methods
function toggleSection(section) {
  expandedSections.value[section] = !expandedSections.value[section];
}

function handleBack() {
  emit('back');
}

function handleSaveTemplate() {
  // TODO: Implement save template functionality
  console.log('[GrowthConfig] Save template:', config.value);
  alert(t('common.saveTemplateSuccess'));
}

function handleStartAnalysis() {
  // Validate required fields
  if (!config.value.growth_model) {
    alert(t('growthStage.pleaseSelectGrowthModel'));
    return;
  }

  // 构建符合后端AnalysisConfig schema的配置对象
  const analysisConfig = {
    depth: 'standard',
    data_sources: [],
    language: 'zh',
    // 场景专属参数放入scenario_params
    scenario_params: {
      growth_model: config.value.growth_model,
      competitive_advantages: config.value.competitive_advantages,
      competition_intensity: config.value.competition_intensity,
      market_growth_rate: config.value.market_growth_rate,
      market_maturity: config.value.market_maturity,
      key_market_drivers: config.value.key_market_drivers,
      projection_period: config.value.projection_period,
      revenue_growth_assumption: config.value.revenue_growth_assumption,
      profit_margin_target: config.value.profit_margin_target,
      burn_rate_assumption: config.value.burn_rate_assumption,
      key_financial_metrics: config.value.key_financial_metrics
    }
  };

  console.log('[GrowthConfig] Starting analysis with config:', analysisConfig);
  emit('config-complete', analysisConfig);
}
</script>

<style scoped>
.growth-config {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}

.header-left h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* Buttons */
.btn-primary,
.btn-secondary,
.btn-text {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  white-space: nowrap;
}

.btn-primary {
  background: var(--primary-color, #2563eb);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover, #1d4ed8);
}

.btn-secondary {
  background: var(--secondary-bg, #f3f4f6);
  color: var(--text-primary, #111827);
  border: 1px solid var(--border-color, #e5e7eb);
}

.btn-secondary:hover {
  background: var(--secondary-hover, #e5e7eb);
}

.btn-text {
  background: transparent;
  color: var(--text-secondary, #6b7280);
  padding: 10px 16px;
}

.btn-text:hover {
  color: var(--text-primary, #111827);
  background: var(--secondary-bg, #f3f4f6);
}

/* Config Form */
.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

/* Config Section */
.config-section {
  background: var(--card-bg, white);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.section-header:hover {
  background: var(--hover-bg, #f9fafb);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin: 0;
}

.section-title .material-symbols-outlined {
  font-size: 24px;
  color: var(--icon-color, #6b7280);
}

.chevron {
  font-size: 24px;
  color: var(--icon-color, #6b7280);
  transition: transform 0.3s ease;
}

.section-content {
  padding: 0 24px 24px 24px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Growth Model Options */
.growth-model-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-option {
  padding: 16px;
  border: 2px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-option:hover {
  border-color: var(--primary-color, #2563eb);
  background: var(--hover-bg, #f9fafb);
}

.model-option.selected {
  border-color: var(--primary-color, #2563eb);
  background: var(--primary-light, #eff6ff);
}

.model-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.radio-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.radio-wrapper input[type="radio"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
  accent-color: var(--primary-color, #2563eb);
}

.model-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  cursor: pointer;
  margin: 0;
}

.model-description {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 0 0 0 32px;
  line-height: 1.5;
}

/* Form Groups */
.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #111827);
  margin-bottom: 8px;
}

.form-hint {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin: 6px 0 0 0;
  line-height: 1.4;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

/* Input Fields */
.form-select,
input[type="text"],
input[type="number"],
textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary, #111827);
  background: var(--input-bg, white);
  transition: all 0.2s ease;
}

.form-select:focus,
input[type="text"]:focus,
input[type="number"]:focus,
textarea:focus {
  outline: none;
  border-color: var(--primary-color, #2563eb);
  box-shadow: 0 0 0 3px var(--primary-light, #eff6ff);
}

textarea {
  resize: vertical;
  font-family: inherit;
  line-height: 1.5;
}

.input-with-unit {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-with-unit input {
  flex: 1;
}

.unit {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary, #6b7280);
  white-space: nowrap;
}

/* Checkbox Group */
.checkbox-group {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary, #111827);
}

.checkbox-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--primary-color, #2563eb);
}

/* Radio Group */
.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary, #111827);
}

.radio-item input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--primary-color, #2563eb);
}

/* Footer Actions */
.footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 24px;
  border-top: 1px solid var(--border-color, #e5e7eb);
}

/* Material Icons */
.material-symbols-outlined {
  font-family: 'Material Symbols Outlined';
  font-weight: normal;
  font-style: normal;
  font-size: 20px;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  display: inline-block;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  -webkit-font-smoothing: antialiased;
  user-select: none;
}

/* Responsive */
@media (max-width: 768px) {
  .growth-config {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .header-actions button {
    width: 100%;
    justify-content: center;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .checkbox-group {
    grid-template-columns: 1fr;
  }

  .footer-actions {
    flex-direction: column-reverse;
    gap: 12px;
  }

  .footer-actions button {
    width: 100%;
    justify-content: center;
  }
}
</style>
