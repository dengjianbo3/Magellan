<template>
  <div class="industry-research-config">
    <!-- Header -->
    <div class="config-header">
      <h1 class="config-title">{{ t('industryResearch.configureAnalysis') }}</h1>
      <p class="config-subtitle">{{ t('industryResearch.configureAnalysisDesc') }}</p>
    </div>

    <!-- Main Content -->
    <div class="config-content">
      <!-- Define Research Scope -->
      <div class="config-section">
        <h2 class="section-title">{{ t('industryResearch.defineResearchScope') }}</h2>
        <div class="section-content">
          <label class="form-label">{{ t('industryResearch.industryTopicAnalyze') }}</label>
          <input
            v-model="config.research_scope"
            type="text"
            class="form-input"
            :placeholder="t('industryResearch.researchScopePlaceholder')"
          />
        </div>
      </div>

      <!-- Select Research Methodologies -->
      <div class="config-section collapsible" :class="{ expanded: sectionsExpanded.methodologies }">
        <div class="section-header" @click="toggleSection('methodologies')">
          <h2 class="section-title">{{ t('industryResearch.selectMethodologies') }}</h2>
          <span class="material-symbols-outlined expand-icon">
            {{ sectionsExpanded.methodologies ? 'expand_less' : 'expand_more' }}
          </span>
        </div>
        <div v-show="sectionsExpanded.methodologies" class="section-content">
          <div class="methodology-grid">
            <label
              v-for="method in methodologies"
              :key="method.value"
              class="methodology-item"
              :class="{ checked: config.methodologies.includes(method.value) }"
            >
              <input
                type="checkbox"
                :value="method.value"
                v-model="config.methodologies"
                class="checkbox-input"
              />
              <div class="checkbox-custom">
                <span v-if="config.methodologies.includes(method.value)" class="material-symbols-outlined">
                  check
                </span>
              </div>
              <span class="methodology-label">{{ t(method.labelKey) }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Set Data Source Preferences -->
      <div class="config-section collapsible" :class="{ expanded: sectionsExpanded.dataSources }">
        <div class="section-header" @click="toggleSection('dataSources')">
          <h2 class="section-title">{{ t('industryResearch.setDataSources') }}</h2>
          <span class="material-symbols-outlined expand-icon">
            {{ sectionsExpanded.dataSources ? 'expand_less' : 'expand_more' }}
          </span>
        </div>
        <div v-show="sectionsExpanded.dataSources" class="section-content">
          <div class="data-sources-grid">
            <label
              v-for="source in dataSources"
              :key="source.value"
              class="data-source-item"
              :class="{ checked: config.data_sources.includes(source.value) }"
            >
              <input
                type="checkbox"
                :value="source.value"
                v-model="config.data_sources"
                class="checkbox-input"
              />
              <div class="checkbox-custom">
                <span v-if="config.data_sources.includes(source.value)" class="material-symbols-outlined">
                  check
                </span>
              </div>
              <span class="source-label">{{ t(source.labelKey) }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Choose Predictive Models -->
      <div class="config-section collapsible" :class="{ expanded: sectionsExpanded.models }">
        <div class="section-header" @click="toggleSection('models')">
          <h2 class="section-title">{{ t('industryResearch.choosePredictiveModels') }}</h2>
          <span class="material-symbols-outlined expand-icon">
            {{ sectionsExpanded.models ? 'expand_less' : 'expand_more' }}
          </span>
        </div>
        <div v-show="sectionsExpanded.models" class="section-content">
          <div class="models-list">
            <div
              v-for="model in predictiveModels"
              :key="model.value"
              class="model-item"
              :class="{ selected: config.predictive_model === model.value }"
              @click="config.predictive_model = model.value"
            >
              <div class="radio-outer">
                <div v-if="config.predictive_model === model.value" class="radio-inner"></div>
              </div>
              <div class="model-info">
                <span class="model-name">{{ t(model.labelKey) }}</span>
                <span class="model-desc">{{ t(model.descKey) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Define Competitive Analysis Focus -->
      <div class="config-section collapsible" :class="{ expanded: sectionsExpanded.competitive }">
        <div class="section-header" @click="toggleSection('competitive')">
          <h2 class="section-title">{{ t('industryResearch.defineCompetitiveFocus') }}</h2>
          <span class="material-symbols-outlined expand-icon">
            {{ sectionsExpanded.competitive ? 'expand_less' : 'expand_more' }}
          </span>
        </div>
        <div v-show="sectionsExpanded.competitive" class="section-content">
          <div class="competitive-focus-grid">
            <label
              v-for="focus in competitiveFocus"
              :key="focus.value"
              class="focus-item"
              :class="{ checked: config.competitive_focus.includes(focus.value) }"
            >
              <input
                type="checkbox"
                :value="focus.value"
                v-model="config.competitive_focus"
                class="checkbox-input"
              />
              <div class="checkbox-custom">
                <span v-if="config.competitive_focus.includes(focus.value)" class="material-symbols-outlined">
                  check
                </span>
              </div>
              <span class="focus-label">{{ t(focus.labelKey) }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="config-footer">
      <button type="button" class="btn-back" @click="handleBack">
        <span class="material-symbols-outlined">arrow_back</span>
        {{ t('common.back') }}
      </button>
      <div class="footer-right">
        <button type="button" class="btn-template" @click="handleSaveTemplate">
          <span class="material-symbols-outlined">bookmark</span>
          {{ t('industryResearch.saveAsTemplate') }}
        </button>
        <button type="button" class="btn-generate" @click="handleGenerate">
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ t('industryResearch.generateReport') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
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
  research_scope: '',
  methodologies: ['swot', 'porters'],
  data_sources: ['industry_reports', 'market_research'],
  predictive_model: 'time_series',
  competitive_focus: ['market_share', 'pricing']
});

const sectionsExpanded = ref({
  methodologies: true,
  dataSources: false,
  models: false,
  competitive: false
});

// Methodologies
const methodologies = [
  { value: 'swot', labelKey: 'industryResearch.swotAnalysis' },
  { value: 'porters', labelKey: 'industryResearch.portersFiveForces' },
  { value: 'pestle', labelKey: 'industryResearch.pestleAnalysis' },
  { value: 'value_chain', labelKey: 'industryResearch.valueChainAnalysis' }
];

// Data Sources
const dataSources = [
  { value: 'industry_reports', labelKey: 'industryResearch.industryReports' },
  { value: 'market_research', labelKey: 'industryResearch.marketResearch' },
  { value: 'financial_data', labelKey: 'industryResearch.financialData' },
  { value: 'news_media', labelKey: 'industryResearch.newsMedia' },
  { value: 'expert_interviews', labelKey: 'industryResearch.expertInterviews' },
  { value: 'company_filings', labelKey: 'industryResearch.companyFilings' }
];

// Predictive Models
const predictiveModels = [
  {
    value: 'time_series',
    labelKey: 'industryResearch.timeSeries',
    descKey: 'industryResearch.timeSeriesDesc'
  },
  {
    value: 'regression',
    labelKey: 'industryResearch.regression',
    descKey: 'industryResearch.regressionDesc'
  },
  {
    value: 'scenario',
    labelKey: 'industryResearch.scenarioAnalysis',
    descKey: 'industryResearch.scenarioAnalysisDesc'
  }
];

// Competitive Focus
const competitiveFocus = [
  { value: 'market_share', labelKey: 'industryResearch.marketShare' },
  { value: 'pricing', labelKey: 'industryResearch.pricingStrategy' },
  { value: 'product_diff', labelKey: 'industryResearch.productDifferentiation' },
  { value: 'innovation', labelKey: 'industryResearch.innovationCapacity' },
  { value: 'customer_base', labelKey: 'industryResearch.customerBase' }
];

// Methods
function toggleSection(section) {
  sectionsExpanded.value[section] = !sectionsExpanded.value[section];
}

function handleBack() {
  emit('back');
}

function handleSaveTemplate() {
  console.log('[IndustryResearchConfig] Saving template:', config.value);
  alert(t('industryResearch.templateSaved'));
}

function handleGenerate() {
  // 构建符合后端AnalysisConfig schema的配置对象
  const analysisConfig = {
    depth: 'standard',
    data_sources: config.value.data_sources || [],
    language: 'zh',
    // 场景专属参数放入scenario_params
    scenario_params: {
      research_scope: config.value.research_scope,
      methodologies: config.value.methodologies,
      predictive_model: config.value.predictive_model,
      competitive_focus: config.value.competitive_focus
    }
  };

  console.log('[IndustryResearchConfig] Generating report with config:', analysisConfig);
  emit('config-complete', analysisConfig);
}
</script>

<style scoped>
.industry-research-config {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  color: #e5e5e5;
}

/* Header */
.config-header {
  margin-bottom: 2rem;
}

.config-title {
  font-size: 2rem;
  font-weight: 700;
  color: #e5e5e5;
  margin: 0 0 0.5rem 0;
}

.config-subtitle {
  font-size: 1rem;
  color: #a1a1a1;
  margin: 0;
}

/* Content */
.config-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.config-section {
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s ease;
}

.config-section.collapsible {
  cursor: pointer;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e5e5e5;
  margin: 0;
}

.expand-icon {
  font-size: 24px;
  color: #6b7280;
  transition: transform 0.2s ease;
}

.section-content {
  margin-top: 1.25rem;
}

.config-section:not(.collapsible) .section-content {
  margin-top: 0;
}

/* Form Elements */
.form-label {
  display: block;
  font-size: 0.95rem;
  font-weight: 500;
  color: #a1a1a1;
  margin-bottom: 0.5rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  font-size: 0.95rem;
  color: #e5e5e5;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.form-input::placeholder {
  color: #6b7280;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Methodology Grid */
.methodology-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.methodology-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.methodology-item:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.methodology-item.checked {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.checkbox-input {
  display: none;
}

.checkbox-custom {
  width: 20px;
  height: 20px;
  border: 2px solid #6b7280;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.methodology-item.checked .checkbox-custom,
.data-source-item.checked .checkbox-custom,
.focus-item.checked .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
}

.checkbox-custom .material-symbols-outlined {
  font-size: 16px;
  color: white;
  font-weight: bold;
}

.methodology-label {
  font-size: 0.95rem;
  color: #e5e5e5;
}

/* Data Sources Grid */
.data-sources-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.data-source-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.data-source-item:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.data-source-item.checked {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.source-label {
  font-size: 0.95rem;
  color: #e5e5e5;
}

/* Models List */
.models-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.model-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-item:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.model-item.selected {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.radio-outer {
  width: 20px;
  height: 20px;
  border: 2px solid #6b7280;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.2s ease;
  margin-top: 2px;
}

.model-item.selected .radio-outer {
  border-color: #3b82f6;
}

.radio-inner {
  width: 10px;
  height: 10px;
  background: #3b82f6;
  border-radius: 50%;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.model-name {
  font-size: 0.95rem;
  font-weight: 500;
  color: #e5e5e5;
}

.model-desc {
  font-size: 0.85rem;
  color: #a1a1a1;
  line-height: 1.4;
}

/* Competitive Focus Grid */
.competitive-focus-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.focus-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.focus-item:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.focus-item.checked {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.focus-label {
  font-size: 0.95rem;
  color: #e5e5e5;
}

/* Footer */
.config-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1.5rem;
  border-top: 1px solid #3a3a3a;
}

.footer-right {
  display: flex;
  gap: 0.75rem;
}

.btn-back,
.btn-template,
.btn-generate {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.btn-back {
  background: #4b5563;
  color: white;
}

.btn-back:hover {
  background: #374151;
}

.btn-template {
  background: #2a2a2a;
  color: #e5e5e5;
  border: 1px solid #3a3a3a;
}

.btn-template:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.btn-generate {
  background: #3b82f6;
  color: white;
}

.btn-generate:hover {
  background: #2563eb;
}

.btn-back .material-symbols-outlined,
.btn-template .material-symbols-outlined,
.btn-generate .material-symbols-outlined {
  font-size: 20px;
}

/* Responsive */
@media (max-width: 768px) {
  .industry-research-config {
    padding: 1rem;
  }

  .config-title {
    font-size: 1.5rem;
  }

  .config-section {
    padding: 1rem;
  }

  .methodology-grid,
  .data-sources-grid,
  .competitive-focus-grid {
    grid-template-columns: 1fr;
  }

  .config-footer {
    flex-direction: column;
    gap: 1rem;
  }

  .footer-right {
    width: 100%;
    flex-direction: column;
  }

  .btn-back,
  .btn-template,
  .btn-generate {
    width: 100%;
    justify-content: center;
  }
}
</style>
