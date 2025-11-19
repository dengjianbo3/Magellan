<template>
  <div class="alternative-config">
    <!-- Header -->
    <div class="config-header">
      <h1 class="config-title">{{ t('alternative.allocationAnalysis') }}</h1>
      <p class="config-subtitle">{{ t('alternative.configSubtitle') }}</p>
    </div>

    <!-- Main Content -->
    <div class="config-content">
      <!-- Valuation Model Section -->
      <div class="config-section">
        <h2 class="section-title">{{ t('alternative.valuationModel') }}</h2>
        <div class="model-options">
          <div
            v-for="model in valuationModels"
            :key="model.value"
            class="model-option"
            :class="{ active: config.valuation_model === model.value }"
            @click="config.valuation_model = model.value"
          >
            <div class="radio-wrapper">
              <div class="radio-outer">
                <div v-if="config.valuation_model === model.value" class="radio-inner"></div>
              </div>
              <span class="model-name">{{ t(model.labelKey) }}</span>
            </div>
            <button
              type="button"
              class="info-btn"
              @click.stop="showModelInfo(model.value)"
              :title="t('alternative.moreInfo')"
            >
              <span class="material-symbols-outlined">info</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Due Diligence Focus Section -->
      <div class="config-section">
        <h2 class="section-title">{{ t('alternative.dueDiligenceFocus') }}</h2>
        <div class="dd-grid">
          <label
            v-for="focus in ddFocusAreas"
            :key="focus.value"
            class="dd-checkbox"
            :class="{ checked: config.dd_focus.includes(focus.value) }"
          >
            <div class="checkbox-wrapper">
              <input
                type="checkbox"
                :value="focus.value"
                v-model="config.dd_focus"
                class="checkbox-input"
              />
              <div class="checkbox-custom">
                <span v-if="config.dd_focus.includes(focus.value)" class="material-symbols-outlined check-icon">
                  check
                </span>
              </div>
              <span class="checkbox-label">{{ t(focus.labelKey) }}</span>
            </div>
          </label>
        </div>
      </div>

      <!-- Exit Strategy Preference Section -->
      <div class="config-section">
        <h2 class="section-title">{{ t('alternative.exitStrategyPreference') }}</h2>
        <div class="slider-container">
          <div class="slider-labels">
            <span class="slider-label-left">{{ t('alternative.ipo') }}</span>
            <span class="slider-label-right">{{ t('alternative.strategicAcquisition') }}</span>
          </div>
          <div class="slider-wrapper">
            <input
              type="range"
              min="0"
              max="100"
              v-model="config.exit_preference"
              class="slider"
              @input="updateSliderBackground"
              ref="sliderRef"
            />
            <div class="slider-value">{{ config.exit_preference }}</div>
          </div>
          <div class="slider-hint">
            {{ getExitStrategyHint() }}
          </div>
        </div>
      </div>

      <!-- Analysis Depth (Optional) -->
      <div class="config-section">
        <h2 class="section-title">{{ t('alternative.analysisDepth') }}</h2>
        <div class="depth-options">
          <button
            v-for="depth in analysisDepths"
            :key="depth.value"
            type="button"
            class="depth-btn"
            :class="{ active: config.analysis_depth === depth.value }"
            @click="config.analysis_depth = depth.value"
          >
            <span class="material-symbols-outlined">{{ depth.icon }}</span>
            <span class="depth-label">{{ t(depth.labelKey) }}</span>
          </button>
        </div>
      </div>

      <!-- Risk Tolerance (Optional) -->
      <div class="config-section">
        <h2 class="section-title">{{ t('alternative.riskTolerance') }}</h2>
        <div class="risk-options">
          <button
            v-for="risk in riskLevels"
            :key="risk.value"
            type="button"
            class="risk-btn"
            :class="{ active: config.risk_tolerance === risk.value }"
            @click="config.risk_tolerance = risk.value"
          >
            <div class="risk-color" :style="{ background: risk.color }"></div>
            <span class="risk-label">{{ t(risk.labelKey) }}</span>
          </button>
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
        <button type="button" class="btn-reset" @click="resetToDefault">
          <span class="material-symbols-outlined">restart_alt</span>
          {{ t('alternative.resetToDefault') }}
        </button>
        <button type="button" class="btn-generate" @click="handleGenerate">
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ t('alternative.generateReport') }}
        </button>
      </div>
    </div>

    <!-- Model Info Modal -->
    <div v-if="showInfoModal" class="modal-overlay" @click="closeInfoModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">{{ t(currentModelInfo.titleKey) }}</h3>
          <button class="modal-close" @click="closeInfoModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <p class="modal-description">{{ t(currentModelInfo.descKey) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
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
  valuation_model: 'dcf',
  dd_focus: ['legal_compliance', 'operational_risk'],
  exit_preference: 50,
  analysis_depth: 'standard',
  risk_tolerance: 'moderate'
});

const showInfoModal = ref(false);
const currentModelInfo = ref({});
const sliderRef = ref(null);

// Valuation Models
const valuationModels = computed(() => [
  {
    value: 'dcf',
    labelKey: 'alternative.dcf',
    titleKey: 'alternative.dcfTitle',
    descKey: 'alternative.dcfDesc'
  },
  {
    value: 'comparable',
    labelKey: 'alternative.comparableCompany',
    titleKey: 'alternative.comparableTitle',
    descKey: 'alternative.comparableDesc'
  },
  {
    value: 'precedent',
    labelKey: 'alternative.precedentTransactions',
    titleKey: 'alternative.precedentTitle',
    descKey: 'alternative.precedentDesc'
  }
]);

// Due Diligence Focus Areas
const ddFocusAreas = computed(() => [
  { value: 'legal_compliance', labelKey: 'alternative.legalCompliance' },
  { value: 'operational_risk', labelKey: 'alternative.operationalRisk' },
  { value: 'financial_integrity', labelKey: 'alternative.financialIntegrity' },
  { value: 'market_competition', labelKey: 'alternative.marketCompetition' }
]);

// Analysis Depths
const analysisDepths = computed(() => [
  { value: 'quick', labelKey: 'alternative.quickAnalysis', icon: 'bolt' },
  { value: 'standard', labelKey: 'alternative.standardAnalysis', icon: 'analytics' },
  { value: 'deep', labelKey: 'alternative.deepAnalysis', icon: 'psychology' }
]);

// Risk Levels
const riskLevels = computed(() => [
  { value: 'conservative', labelKey: 'alternative.conservative', color: '#10b981' },
  { value: 'moderate', labelKey: 'alternative.moderate', color: '#f59e0b' },
  { value: 'aggressive', labelKey: 'alternative.aggressive', color: '#ef4444' }
]);

// Methods
function showModelInfo(modelValue) {
  const model = valuationModels.value.find(m => m.value === modelValue);
  if (model) {
    currentModelInfo.value = model;
    showInfoModal.value = true;
  }
}

function closeInfoModal() {
  showInfoModal.value = false;
}

function getExitStrategyHint() {
  const value = parseInt(config.value.exit_preference);
  if (value < 33) {
    return t('alternative.ipoPreferred');
  } else if (value > 66) {
    return t('alternative.acquisitionPreferred');
  } else {
    return t('alternative.balancedExit');
  }
}

function updateSliderBackground() {
  if (sliderRef.value) {
    const value = ((config.value.exit_preference - 0) / (100 - 0)) * 100;
    sliderRef.value.style.setProperty('--slider-value', `${value}%`);
  }
}

function resetToDefault() {
  config.value = {
    valuation_model: 'dcf',
    dd_focus: ['legal_compliance', 'operational_risk'],
    exit_preference: 50,
    analysis_depth: 'standard',
    risk_tolerance: 'moderate'
  };
  nextTick(() => {
    updateSliderBackground();
  });
}

function handleBack() {
  emit('back');
}

function handleGenerate() {
  console.log('[AlternativeConfig] Generating report with config:', config.value);
  emit('config-complete', config.value);
}

// Lifecycle
onMounted(() => {
  updateSliderBackground();
});
</script>

<style scoped>
.alternative-config {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  color: #e5e5e5;
}

/* Header */
.config-header {
  margin-bottom: 2.5rem;
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
  gap: 2rem;
}

.config-section {
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 12px;
  padding: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e5e5e5;
  margin: 0 0 1.25rem 0;
}

/* Valuation Model */
.model-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-option:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.model-option.active {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.radio-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.radio-outer {
  width: 20px;
  height: 20px;
  border: 2px solid #6b7280;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease;
}

.model-option.active .radio-outer {
  border-color: #3b82f6;
}

.radio-inner {
  width: 10px;
  height: 10px;
  background: #3b82f6;
  border-radius: 50%;
}

.model-name {
  font-size: 0.95rem;
  color: #e5e5e5;
}

.info-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #a1a1a1;
}

.info-btn:hover {
  background: #333333;
  border-color: #3b82f6;
  color: #3b82f6;
}

.info-btn .material-symbols-outlined {
  font-size: 18px;
}

/* Due Diligence Focus */
.dd-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.dd-checkbox {
  display: flex;
  align-items: center;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dd-checkbox:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.dd-checkbox.checked {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
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

.dd-checkbox.checked .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
}

.check-icon {
  font-size: 16px;
  color: white;
  font-weight: bold;
}

.checkbox-label {
  font-size: 0.95rem;
  color: #e5e5e5;
}

/* Exit Strategy Slider */
.slider-container {
  margin-top: 0.5rem;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.slider-label-left,
.slider-label-right {
  font-size: 0.9rem;
  color: #a1a1a1;
  font-weight: 500;
}

.slider-wrapper {
  position: relative;
  padding: 1rem 0;
}

.slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(
    to right,
    #3b82f6 0%,
    #3b82f6 var(--slider-value, 50%),
    #3a3a3a var(--slider-value, 50%),
    #3a3a3a 100%
  );
  outline: none;
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
  background: #3b82f6;
  cursor: pointer;
  border: 3px solid #1a1a1a;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 3px solid #1a1a1a;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.slider-value {
  position: absolute;
  top: -8px;
  left: calc(var(--slider-value, 50%) - 20px);
  background: #3b82f6;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  pointer-events: none;
}

.slider-hint {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  text-align: center;
  font-size: 0.9rem;
  color: #a1a1a1;
}

/* Analysis Depth */
.depth-options {
  display: flex;
  gap: 0.75rem;
}

.depth-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #e5e5e5;
}

.depth-btn:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.depth-btn.active {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.depth-btn .material-symbols-outlined {
  font-size: 28px;
  color: #3b82f6;
}

.depth-label {
  font-size: 0.9rem;
  font-weight: 500;
}

/* Risk Tolerance */
.risk-options {
  display: flex;
  gap: 0.75rem;
}

.risk-btn {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #e5e5e5;
}

.risk-btn:hover {
  background: #333333;
  border-color: #4a4a4a;
}

.risk-btn.active {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.risk-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
}

.risk-label {
  font-size: 0.9rem;
  font-weight: 500;
}

/* Footer */
.config-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #3a3a3a;
}

.footer-right {
  display: flex;
  gap: 0.75rem;
}

.btn-back,
.btn-reset,
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

.btn-reset {
  background: #2a2a2a;
  color: #e5e5e5;
  border: 1px solid #3a3a3a;
}

.btn-reset:hover {
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
.btn-reset .material-symbols-outlined,
.btn-generate .material-symbols-outlined {
  font-size: 20px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 12px;
  max-width: 500px;
  width: 100%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #3a3a3a;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e5e5e5;
  margin: 0;
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #a1a1a1;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: #2a2a2a;
  color: #e5e5e5;
}

.modal-close .material-symbols-outlined {
  font-size: 20px;
}

.modal-body {
  padding: 1.5rem;
}

.modal-description {
  font-size: 0.95rem;
  line-height: 1.6;
  color: #a1a1a1;
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .alternative-config {
    padding: 1rem;
  }

  .config-title {
    font-size: 1.5rem;
  }

  .dd-grid {
    grid-template-columns: 1fr;
  }

  .depth-options,
  .risk-options {
    flex-direction: column;
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
  .btn-reset,
  .btn-generate {
    width: 100%;
    justify-content: center;
  }
}
</style>
