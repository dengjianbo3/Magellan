<template>
  <div class="public-market-config">
    <!-- Header -->
    <div class="header">
      <div class="header-left">
        <h1>{{ t('publicMarket.allocationAnalysis') }}</h1>
        <p class="subtitle">{{ t('publicMarket.configureParameters') }}</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-secondary" @click="handleSaveTemplate">
          <span class="material-symbols-outlined">bookmark</span>
          <span>{{ t('common.saveAsTemplate') }}</span>
        </button>
        <button type="button" class="btn-primary" @click="handleStartAnalysis">
          <span class="material-symbols-outlined">play_arrow</span>
          <span>{{ t('publicMarket.generateReport') }}</span>
        </button>
      </div>
    </div>

    <!-- Configuration Form -->
    <div class="config-form">
      <!-- Configure Data Sources -->
      <div class="config-section">
        <div class="section-header">
          <h3 class="section-title">
            <span class="material-symbols-outlined">cloud</span>
            <span>{{ t('publicMarket.configureDataSources') }}</span>
          </h3>
        </div>

        <div class="section-content">
          <div class="data-sources-grid">
            <label v-for="source in dataSources" :key="source.value" class="source-item">
              <div class="source-checkbox">
                <input
                  type="checkbox"
                  :value="source.value"
                  v-model="config.data_sources"
                />
                <span class="checkmark"></span>
              </div>
              <div class="source-info">
                <span class="source-name">{{ t(source.labelKey) }}</span>
                <span v-if="source.timePeriod" class="source-period">{{ t(source.timePeriod) }}</span>
              </div>
            </label>
          </div>
        </div>
      </div>

      <!-- Define AI Agent Focus -->
      <div class="config-section">
        <div class="section-header">
          <h3 class="section-title">
            <span class="material-symbols-outlined">psychology</span>
            <span>{{ t('publicMarket.defineAgentFocus') }}</span>
          </h3>
        </div>

        <div class="section-content">
          <div class="agent-focus-list">
            <div v-for="agent in agentFocus" :key="agent.value" class="agent-item">
              <div class="agent-info">
                <div class="agent-name">{{ t(agent.labelKey) }}</div>
                <div class="agent-weight">
                  <span>{{ t('publicMarket.weight') }}:</span>
                  <span class="weight-value">{{ config.agent_weights[agent.value] }}%</span>
                </div>
              </div>
              <div class="agent-slider">
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  v-model.number="config.agent_weights[agent.value]"
                  class="slider"
                  :style="getSliderStyle(agent.color)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Set Risk Parameters -->
      <div class="config-section">
        <div class="section-header">
          <h3 class="section-title">
            <span class="material-symbols-outlined">shield</span>
            <span>{{ t('publicMarket.setRiskParameters') }}</span>
          </h3>
        </div>

        <div class="section-content">
          <div class="risk-parameters">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">{{ t('publicMarket.riskAppetite') }}</label>
                <select v-model="config.risk_appetite" class="form-select">
                  <option value="">{{ t('common.pleaseSelect') }}</option>
                  <option value="conservative">{{ t('publicMarket.conservative') }}</option>
                  <option value="moderate">{{ t('publicMarket.moderate') }}</option>
                  <option value="aggressive">{{ t('publicMarket.aggressive') }}</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">{{ t('publicMarket.maxDrawdown') }}</label>
                <div class="input-with-unit">
                  <input
                    type="number"
                    v-model.number="config.max_drawdown"
                    min="0"
                    max="100"
                    step="1"
                    class="form-input"
                    placeholder="20"
                  />
                  <span class="unit">%</span>
                </div>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">{{ t('publicMarket.targetReturn') }}</label>
                <div class="input-with-unit">
                  <input
                    type="number"
                    v-model.number="config.target_return"
                    min="0"
                    max="100"
                    step="0.5"
                    class="form-input"
                    placeholder="15"
                  />
                  <span class="unit">%</span>
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">{{ t('publicMarket.timeHorizon') }}</label>
                <select v-model="config.time_horizon" class="form-select">
                  <option value="">{{ t('common.pleaseSelect') }}</option>
                  <option value="short">{{ t('publicMarket.shortTerm') }} (< 1{{ t('common.year') }})</option>
                  <option value="medium">{{ t('publicMarket.mediumTerm') }} (1-3{{ t('common.year') }})</option>
                  <option value="long">{{ t('publicMarket.longTerm') }} (> 3{{ t('common.year') }})</option>
                </select>
              </div>
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
        <span>{{ t('publicMarket.generateReport') }}</span>
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
const config = ref({
  data_sources: ['real_time_quotes', 'financial_filings'],
  agent_weights: {
    sentiment_analysis: 70,
    quantitative_strategy: 75,
    fundamental_analysis: 90,
    technical_indicators: 60
  },
  risk_appetite: 'moderate',
  max_drawdown: 20,
  target_return: 15,
  time_horizon: 'medium'
});

// Data Sources
const dataSources = computed(() => [
  { value: 'real_time_quotes', labelKey: 'publicMarket.realTimeQuotes', timePeriod: null },
  { value: 'financial_filings', labelKey: 'publicMarket.financialFilings', timePeriod: 'publicMarket.timePeriod' },
  { value: 'news_social_media', labelKey: 'publicMarket.newsSocialMedia', timePeriod: null }
]);

// Agent Focus
const agentFocus = computed(() => [
  { value: 'sentiment_analysis', labelKey: 'publicMarket.sentimentAnalysis', color: '#8b5cf6' },
  { value: 'quantitative_strategy', labelKey: 'publicMarket.quantitativeStrategy', color: '#3b82f6' },
  { value: 'fundamental_analysis', labelKey: 'publicMarket.fundamentalAnalysis', color: '#10b981' },
  { value: 'technical_indicators', labelKey: 'publicMarket.technicalIndicators', color: '#f59e0b' }
]);

// Methods
function getSliderStyle(color) {
  return {
    '--slider-color': color
  };
}

function handleBack() {
  emit('back');
}

function handleSaveTemplate() {
  console.log('[PublicMarketConfig] Save template:', config.value);
  alert(t('common.saveTemplateSuccess'));
}

function handleStartAnalysis() {
  // Validate
  if (config.value.data_sources.length === 0) {
    alert(t('publicMarket.selectAtLeastOneDataSource'));
    return;
  }

  console.log('[PublicMarketConfig] Starting analysis with config:', config.value);
  emit('config-complete', config.value);
}
</script>

<style scoped>
.public-market-config {
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
  padding: 20px 24px;
  background: var(--section-header-bg, #f9fafb);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
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

.section-content {
  padding: 24px;
}

/* Data Sources Grid */
.data-sources-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.source-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: var(--secondary-bg, #f9fafb);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.source-item:hover {
  background: var(--hover-bg, #f3f4f6);
  border-color: var(--primary-color, #2563eb);
}

.source-checkbox {
  position: relative;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.source-checkbox input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
  accent-color: var(--primary-color, #2563eb);
}

.source-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #111827);
  line-height: 1.4;
}

.source-period {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
}

/* Agent Focus List */
.agent-focus-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.agent-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #111827);
}

.agent-weight {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
}

.weight-value {
  font-weight: 600;
  color: var(--text-primary, #111827);
  min-width: 40px;
  text-align: right;
}

/* Slider */
.agent-slider {
  width: 100%;
}

.slider {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  outline: none;
  background: linear-gradient(
    to right,
    var(--slider-color, #3b82f6) 0%,
    var(--slider-color, #3b82f6) var(--value, 50%),
    #e5e7eb var(--value, 50%),
    #e5e7eb 100%
  );
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  border: 3px solid var(--slider-color, #3b82f6);
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  border: 3px solid var(--slider-color, #3b82f6);
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Risk Parameters */
.risk-parameters {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #111827);
}

.form-select,
.form-input {
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
.form-input:focus {
  outline: none;
  border-color: var(--primary-color, #2563eb);
  box-shadow: 0 0 0 3px var(--primary-light, #eff6ff);
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
  .public-market-config {
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

  .data-sources-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
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
