<template>
  <div class="early-stage-config">
    <!-- Header -->
    <div class="header">
      <h1>{{ t('earlyStage.configTitle') }}</h1>
      <p class="subtitle">{{ t('earlyStage.configSubtitle') }}</p>
    </div>

    <!-- Form -->
    <form @submit.prevent="handleGenerate" class="config-form">
      <!-- Project/Analysis Name -->
      <div class="form-section">
        <label class="section-label">
          {{ t('earlyStage.projectName') }}
        </label>
        <input
          v-model="config.project_name"
          type="text"
          class="form-input"
          :placeholder="t('earlyStage.projectNamePlaceholder')"
        />
      </div>

      <!-- Select Data Sources -->
      <div class="form-section">
        <label class="section-label">
          {{ t('earlyStage.selectDataSources') }}
        </label>
        <div class="checkbox-grid">
          <label
            v-for="source in dataSources"
            :key="source.value"
            class="checkbox-item"
          >
            <input
              v-model="config.data_sources"
              type="checkbox"
              :value="source.value"
            />
            <span class="checkbox-label">{{ t(source.labelKey) }}</span>
          </label>
        </div>
      </div>

      <!-- Define Analysis Priorities -->
      <div class="form-section">
        <label class="section-label">
          {{ t('earlyStage.definePriorities') }}
        </label>
        <div class="priorities-grid">
          <div
            v-for="priority in analysisPriorities"
            :key="priority.value"
            :class="['priority-card', { 'selected': config.priority === priority.value }]"
            @click="config.priority = priority.value"
          >
            <span class="priority-icon material-symbols-outlined">
              {{ priority.icon }}
            </span>
            <div class="priority-label">{{ t(priority.labelKey) }}</div>
          </div>
        </div>
      </div>

      <!-- Set Risk Appetite -->
      <div class="form-section">
        <label class="section-label">
          {{ t('earlyStage.setRiskAppetite') }}
        </label>
        <div class="risk-selector">
          <div
            v-for="risk in riskLevels"
            :key="risk.value"
            :class="['risk-option', risk.value, { 'selected': config.risk_appetite === risk.value }]"
            @click="config.risk_appetite = risk.value"
          >
            <div class="risk-label">{{ t(risk.labelKey) }}</div>
            <div class="risk-desc">{{ t(risk.descKey) }}</div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button type="button" class="btn-reset" @click="resetConfig">
          {{ t('earlyStage.reset') }}
        </button>
        <button type="submit" class="btn-generate">
          <span>{{ t('earlyStage.generateReport') }}</span>
          <span class="material-symbols-outlined">play_arrow</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';

const { t } = useLanguage();

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

const emit = defineEmits(['config-complete', 'back']);

const dataSources = computed(() => [
  { value: 'public_market_data', labelKey: 'earlyStage.publicMarketData' },
  { value: 'paid_industry_reports', labelKey: 'earlyStage.paidIndustryReports' },
  { value: 'internal_knowledge', labelKey: 'earlyStage.internalKnowledge' },
  { value: 'news_social', labelKey: 'earlyStage.newsSocial' }
]);

const analysisPriorities = computed(() => [
  { value: 'team_founder', labelKey: 'earlyStage.teamFounder', icon: 'groups' },
  { value: 'technology_product', labelKey: 'earlyStage.technologyProduct', icon: 'psychology' },
  { value: 'market_size', labelKey: 'earlyStage.marketSizeTAM', icon: 'trending_up' },
  { value: 'competitive_landscape', labelKey: 'earlyStage.competitiveLandscape', icon: 'verified' }
]);

const riskLevels = computed(() => [
  {
    value: 'aggressive',
    labelKey: 'earlyStage.aggressive',
    descKey: 'earlyStage.aggressiveDesc'
  },
  {
    value: 'balanced',
    labelKey: 'earlyStage.balanced',
    descKey: 'earlyStage.balancedDesc'
  },
  {
    value: 'conservative',
    labelKey: 'earlyStage.conservative',
    descKey: 'earlyStage.conservativeDesc'
  }
]);

const config = ref({
  project_name: props.target.company_name || '',
  data_sources: ['public_market_data', 'paid_industry_reports'],
  priority: 'team_founder',
  risk_appetite: 'balanced',
  depth: 'quick'
});

function resetConfig() {
  config.value = {
    project_name: props.target.company_name || '',
    data_sources: ['public_market_data', 'paid_industry_reports'],
    priority: 'team_founder',
    risk_appetite: 'balanced',
    depth: 'quick'
  };
}

function handleGenerate() {
  // 构建符合后端AnalysisConfig schema的配置对象
  const analysisConfig = {
    depth: config.value.depth || 'quick',
    data_sources: config.value.data_sources || [],
    language: 'zh',
    // 场景专属参数放入scenario_params
    scenario_params: {
      project_name: config.value.project_name,
      priority: config.value.priority,
      risk_appetite: config.value.risk_appetite
    }
  };

  emit('config-complete', analysisConfig);
}
</script>

<style scoped>
.early-stage-config {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

/* Header */
.header {
  margin-bottom: 2.5rem;
}

.header h1 {
  font-size: 2rem;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 0.95rem;
  color: #9ca3af;
  line-height: 1.5;
}

/* Form */
.config-form {
  background: #1a1d26;
  border: 1px solid #2d3748;
  border-radius: 12px;
  padding: 2.5rem;
}

.form-section {
  margin-bottom: 2.5rem;
}

.form-section:last-of-type {
  margin-bottom: 0;
}

.section-label {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 1rem;
}

.form-input {
  width: 100%;
  padding: 0.875rem 1rem;
  font-size: 15px;
  background: #111827;
  border: 1px solid #374151;
  color: #f3f4f6;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input::placeholder {
  color: #6b7280;
}

/* Checkbox Grid */
.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #111827;
  border: 1px solid #374151;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.checkbox-item:hover {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
}

.checkbox-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #3b82f6;
}

.checkbox-label {
  font-size: 14px;
  color: #d1d5db;
  font-weight: 500;
}

/* Priorities Grid */
.priorities-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.priority-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
  background: #111827;
  border: 2px solid #374151;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.priority-card:hover {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
  transform: translateY(-2px);
}

.priority-card.selected {
  border-color: #3b82f6;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05));
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.priority-icon {
  font-size: 2.5rem;
  color: #3b82f6;
}

.priority-label {
  font-size: 13px;
  font-weight: 500;
  color: #d1d5db;
  line-height: 1.3;
}

/* Risk Selector */
.risk-selector {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.risk-option {
  padding: 1.25rem;
  background: #111827;
  border: 2px solid #374151;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.risk-option:hover {
  transform: translateY(-2px);
}

.risk-option.aggressive {
  border-color: #dc2626;
}

.risk-option.aggressive:hover,
.risk-option.aggressive.selected {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.2);
}

.risk-option.balanced {
  border-color: #3b82f6;
}

.risk-option.balanced:hover,
.risk-option.balanced.selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.risk-option.conservative {
  border-color: #10b981;
}

.risk-option.conservative:hover,
.risk-option.conservative.selected {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
}

.risk-label {
  font-size: 15px;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 0.5rem;
}

.risk-desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.4;
}

/* Actions */
.form-actions {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 2.5rem;
  padding-top: 2rem;
  border-top: 1px solid #2d3748;
}

.btn-reset,
.btn-generate {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 2rem;
  font-size: 15px;
  font-weight: 500;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-reset {
  background: #374151;
  color: #d1d5db;
}

.btn-reset:hover {
  background: #4b5563;
}

.btn-generate {
  background: #3b82f6;
  color: white;
}

.btn-generate:hover {
  background: #2563eb;
  transform: translateX(2px);
}

@media (max-width: 768px) {
  .early-stage-config {
    padding: 1rem;
  }

  .config-form {
    padding: 1.5rem;
  }

  .checkbox-grid {
    grid-template-columns: 1fr;
  }

  .priorities-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .risk-selector {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-reset,
  .btn-generate {
    width: 100%;
    justify-content: center;
  }
}
</style>
