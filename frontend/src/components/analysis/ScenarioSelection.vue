<template>
  <div class="scenario-selection">
    <!-- Header -->
    <div class="header">
      <h1>{{ t('analysisWizard.selectScenario') }}</h1>
      <p class="subtitle">{{ t('analysisWizard.selectScenarioHint') }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>{{ t('analysisWizard.loadingScenarios') }}</p>
    </div>

    <!-- Scenarios Grid -->
    <div v-else class="scenarios-grid">
      <div
        v-for="scenario in scenarios"
        :key="scenario.id"
        :class="['scenario-card', {
          'selected': selectedScenario === scenario.id,
          'coming-soon': scenario.status === 'coming_soon'
        }]"
        @click="selectScenario(scenario)"
      >
        <!-- Icon -->
        <div class="scenario-icon" :style="{ color: scenario.iconColor }">
          {{ scenario.icon }}
        </div>

        <!-- Title and Description -->
        <h3 class="scenario-title">{{ scenario.name }}</h3>
        <p class="scenario-description">{{ scenario.description }}</p>

        <!-- Duration Info -->
        <div class="scenario-meta">
          <div class="meta-row">
            <span class="meta-label">{{ t('analysisWizard.quickJudgment') }}:</span>
            <span class="meta-value">{{ scenario.quick_mode_duration }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">{{ t('analysisWizard.standardAnalysis') }}:</span>
            <span class="meta-value">{{ scenario.standard_mode_duration || t('analysisWizard.na') }}</span>
          </div>
        </div>

        <!-- Coming Soon Badge -->
        <div v-if="scenario.status === 'coming_soon'" class="coming-soon-badge">
          {{ t('analysisWizard.comingSoon') }}
        </div>

        <!-- Selected Indicator -->
        <div v-if="selectedScenario === scenario.id" class="selected-indicator">
          <span class="material-symbols-outlined">check_circle</span>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="actions">
      <button
        class="btn-next"
        :disabled="!selectedScenario"
        @click="handleNext"
      >
        <span>{{ t('analysisWizard.nextStep') }}</span>
        <span class="material-symbols-outlined">arrow_forward</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import analysisServiceV2 from '@/services/analysisServiceV2.js';

const { t } = useLanguage();

const emit = defineEmits(['scenario-selected']);

const loading = ref(true);
const scenarios = ref([]);
const selectedScenario = ref(null);

onMounted(async () => {
  try {
    scenarios.value = await analysisServiceV2.getScenarios();
    loading.value = false;
  } catch (error) {
    console.error('Failed to load scenarios:', error);
    loading.value = false;
  }
});

function selectScenario(scenario) {
  if (scenario.status === 'coming_soon') {
    return; // 暂不支持的场景,不能选择
  }
  selectedScenario.value = scenario.id;
}

function handleNext() {
  if (selectedScenario.value) {
    const scenario = scenarios.value.find(s => s.id === selectedScenario.value);
    emit('scenario-selected', scenario);
  }
}
</script>

<style scoped>
.scenario-selection {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

/* Header */
.header {
  text-align: center;
  margin-bottom: 3rem;
}

.header h1 {
  font-size: 2.5rem;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 0.75rem;
}

.subtitle {
  font-size: 1rem;
  color: #9ca3af;
}

/* Loading */
.loading {
  text-align: center;
  padding: 3rem;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #374151;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Scenarios Grid */
.scenarios-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  margin-bottom: 3rem;
}

@media (max-width: 1200px) {
  .scenarios-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .scenarios-grid {
    grid-template-columns: 1fr;
  }
}

/* Scenario Card */
.scenario-card {
  position: relative;
  background: #1a1d26;
  border: 2px solid #2d3748;
  border-radius: 16px;
  padding: 2.5rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.scenario-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.scenario-card:hover::before {
  opacity: 1;
}

.scenario-card:hover {
  transform: translateY(-8px);
  border-color: #3b82f6;
  box-shadow: 0 12px 32px rgba(59, 130, 246, 0.25);
}

.scenario-card.selected {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #1e3a5f 0%, #1a1d26 100%);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
}

.scenario-card.coming-soon {
  opacity: 0.5;
  cursor: not-allowed;
}

.scenario-card.coming-soon:hover {
  transform: none;
  border-color: #2d3748;
  box-shadow: none;
}

.scenario-card.coming-soon::before {
  opacity: 0;
}

/* Icon */
.scenario-icon {
  font-size: 4rem;
  text-align: center;
  margin-bottom: 1.5rem;
  position: relative;
  z-index: 1;
}

/* Title and Description */
.scenario-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 0.75rem;
  text-align: center;
  position: relative;
  z-index: 1;
}

.scenario-description {
  font-size: 0.95rem;
  color: #9ca3af;
  text-align: center;
  margin-bottom: 2rem;
  min-height: 2.5rem;
  line-height: 1.5;
  position: relative;
  z-index: 1;
}

/* Meta Info */
.scenario-meta {
  border-top: 1px solid #374151;
  padding-top: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  position: relative;
  z-index: 1;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-label {
  font-size: 0.85rem;
  color: #9ca3af;
}

.meta-value {
  font-size: 0.9rem;
  color: #d1d5db;
  font-weight: 600;
}

/* Badges */
.coming-soon-badge {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  background: #f59e0b;
  color: white;
  padding: 0.4rem 1rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  z-index: 2;
}

.selected-indicator {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  color: #3b82f6;
  z-index: 2;
}

.selected-indicator .material-symbols-outlined {
  font-size: 2rem;
  filter: drop-shadow(0 2px 8px rgba(59, 130, 246, 0.5));
}

/* Actions */
.actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 2rem;
  border-top: 1px solid #2d3748;
}

.btn-next {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 2.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-next:hover:not(:disabled) {
  background: #2563eb;
  transform: translateX(4px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
}

.btn-next:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.btn-next .material-symbols-outlined {
  font-size: 1.25rem;
  transition: transform 0.3s ease;
}

.btn-next:hover:not(:disabled) .material-symbols-outlined {
  transform: translateX(4px);
}
</style>
