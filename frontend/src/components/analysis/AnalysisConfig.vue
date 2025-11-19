<template>
  <div class="analysis-config">
    <!-- Header -->
    <div class="config-header">
      <h2>{{ t('analysisWizard.configureIndustryAnalysis') }}</h2>
      <p class="subtitle">{{ t('analysisWizard.configureIndustryAnalysisHint') }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="config-form">
      <!-- Define Your Research Scope Section -->
      <div class="config-section expanded">
        <div class="section-header" @click="toggleSection('scope')">
          <h3>{{ t('analysisWizard.defineResearchScope') }}</h3>
          <span class="toggle-icon">{{ sections.scope ? '▲' : '▼' }}</span>
        </div>

        <div v-if="sections.scope" class="section-content">
          <!-- Industry/Topic -->
          <div class="form-group">
            <label>{{ t('analysisWizard.industryTopicLabel') }}</label>
            <input
              v-model="config.industry"
              type="text"
              :placeholder="t('analysisWizard.industryTopicPlaceholder')"
              class="form-input"
            />
          </div>

          <!-- Geography -->
          <div class="form-group">
            <label>{{ t('analysisWizard.geography') }}</label>
            <select v-model="config.geography" class="form-select">
              <option value="">{{ t('analysisWizard.geographyPlaceholder') }}</option>
              <option value="global">{{ t('analysisWizard.geographyGlobal') }}</option>
              <option value="north-america">{{ t('analysisWizard.geographyNorthAmerica') }}</option>
              <option value="europe">{{ t('analysisWizard.geographyEurope') }}</option>
              <option value="asia-pacific">{{ t('analysisWizard.geographyAsiaPacific') }}</option>
              <option value="china">{{ t('analysisWizard.geographyChina') }}</option>
            </select>
          </div>

          <!-- Main Products/Services -->
          <div class="form-group">
            <label>{{ t('analysisWizard.mainProducts') }}</label>
            <textarea
              v-model="config.products"
              rows="3"
              :placeholder="t('analysisWizard.mainProductsPlaceholder')"
              class="form-textarea"
            ></textarea>
          </div>

          <!-- Market Size & Max Size -->
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('analysisWizard.marketSize') }}</label>
              <input
                v-model="config.marketSize"
                type="number"
                :placeholder="t('analysisWizard.marketSizePlaceholder')"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>{{ t('analysisWizard.maxSize') }}</label>
              <input
                v-model="config.maxSize"
                type="number"
                :placeholder="t('analysisWizard.maxSizePlaceholder')"
                class="form-input"
              />
            </div>
          </div>

          <!-- Key Competitors -->
          <div class="form-group">
            <label>{{ t('analysisWizard.keyCompetitors') }}</label>
            <div class="tags-input">
              <span v-for="(tag, index) in config.competitors" :key="index" class="tag">
                {{ tag }}
                <button type="button" @click="removeTag('competitors', index)" class="tag-remove">×</button>
              </span>
              <input
                v-model="newCompetitor"
                type="text"
                :placeholder="t('analysisWizard.keyCompetitorsPlaceholder')"
                class="tag-input"
                @keydown.enter.prevent="addTag('competitors', newCompetitor)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Select Research Methodologies Section -->
      <div class="config-section">
        <div class="section-header" @click="toggleSection('methodologies')">
          <h3>{{ t('analysisWizard.selectResearchMethodologies') }}</h3>
          <span class="toggle-icon">{{ sections.methodologies ? '▲' : '▼' }}</span>
        </div>

        <div v-if="sections.methodologies" class="section-content">
          <div class="methodologies-grid">
            <label class="methodology-checkbox">
              <input type="checkbox" v-model="config.methodologies" value="swot" />
              <span class="checkbox-custom"></span>
              <span class="methodology-label">{{ t('analysisWizard.swotAnalysis') }}</span>
            </label>
            <label class="methodology-checkbox">
              <input type="checkbox" v-model="config.methodologies" value="porter" />
              <span class="checkbox-custom"></span>
              <span class="methodology-label">{{ t('analysisWizard.portersFiveForces') }}</span>
            </label>
            <label class="methodology-checkbox">
              <input type="checkbox" v-model="config.methodologies" value="pestle" />
              <span class="checkbox-custom"></span>
              <span class="methodology-label">{{ t('analysisWizard.pestleAnalysis') }}</span>
            </label>
            <label class="methodology-checkbox">
              <input type="checkbox" v-model="config.methodologies" value="value-chain" />
              <span class="checkbox-custom"></span>
              <span class="methodology-label">{{ t('analysisWizard.valueChainAnalysis') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Set Data Source Preferences Section -->
      <div class="config-section">
        <div class="section-header" @click="toggleSection('dataSources')">
          <h3>{{ t('analysisWizard.setDataSourcePreferences') }}</h3>
          <span class="toggle-icon">{{ sections.dataSources ? '▲' : '▼' }}</span>
        </div>

        <div v-if="sections.dataSources" class="section-content">
          <p class="section-hint">{{ t('analysisWizard.selectDataSources') }}</p>
          <!-- Data source options would go here -->
        </div>
      </div>

      <!-- Choose Predictive Models Section -->
      <div class="config-section">
        <div class="section-header" @click="toggleSection('predictiveModels')">
          <h3>{{ t('analysisWizard.choosePredictiveModels') }}</h3>
          <span class="toggle-icon">{{ sections.predictiveModels ? '▲' : '▼' }}</span>
        </div>

        <div v-if="sections.predictiveModels" class="section-content">
          <p class="section-hint">{{ t('analysisWizard.selectPredictiveModels') }}</p>
          <!-- Predictive model options would go here -->
        </div>
      </div>

      <!-- Define Competitive Analysis Focus Section -->
      <div class="config-section">
        <div class="section-header" @click="toggleSection('competitive')">
          <h3>{{ t('analysisWizard.defineCompetitiveAnalysisFocus') }}</h3>
          <span class="toggle-icon">{{ sections.competitive ? '▲' : '▼' }}</span>
        </div>

        <div v-if="sections.competitive" class="section-content">
          <p class="section-hint">{{ t('analysisWizard.specifyCompetitiveParams') }}</p>
          <!-- Competitive analysis options would go here -->
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="actions">
        <button type="button" class="btn-secondary" @click="saveAsTemplate">
          <span class="material-symbols-outlined">bookmark</span>
          {{ t('analysisWizard.saveAsTemplate') }}
        </button>
        <button type="submit" class="btn-primary">
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ t('analysisWizard.generateReport') }}
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
  }
});

const emit = defineEmits(['config-complete', 'back']);

// Section visibility state
const sections = ref({
  scope: true,
  methodologies: false,
  dataSources: false,
  predictiveModels: false,
  competitive: false
});

// Form configuration
const config = ref({
  industry: '',
  geography: '',
  products: '',
  marketSize: '',
  maxSize: '',
  competitors: ['NVIDIA', 'Intel'],
  methodologies: ['swot', 'porter'],
  dataSources: [],
  predictiveModels: [],
  competitiveFocus: []
});

// Temporary input fields
const newCompetitor = ref('');

function toggleSection(section) {
  sections.value[section] = !sections.value[section];
}

function addTag(field, value) {
  if (value && value.trim()) {
    config.value[field].push(value.trim());
    if (field === 'competitors') {
      newCompetitor.value = '';
    }
  }
}

function removeTag(field, index) {
  config.value[field].splice(index, 1);
}

function saveAsTemplate() {
  console.log('Save as template:', config.value);
  // TODO: Implement template saving
}

function handleSubmit() {
  console.log('Generate report with config:', config.value);
  emit('config-complete', config.value);
}
</script>

<style scoped>
.analysis-config {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

/* Header */
.config-header {
  margin-bottom: 2rem;
}

.config-header h2 {
  font-size: 2rem;
  font-weight: 600;
  color: #e5e7eb;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 0.95rem;
  color: #9ca3af;
}

/* Config Form */
.config-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Config Sections */
.config-section {
  background: #1a1d26;
  border: 1px solid #2d3748;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.config-section.expanded {
  border-color: #3b82f6;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  background: #212530;
  cursor: pointer;
  transition: background 0.2s ease;
}

.section-header:hover {
  background: #252a38;
}

.section-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #e5e7eb;
  margin: 0;
}

.toggle-icon {
  color: #9ca3af;
  font-size: 0.9rem;
  transition: transform 0.3s ease;
}

.section-content {
  padding: 1.5rem;
  background: #1a1d26;
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

.section-hint {
  font-size: 0.9rem;
  color: #9ca3af;
  margin-bottom: 1rem;
}

/* Form Elements */
.form-group {
  margin-bottom: 1.25rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: #d1d5db;
  margin-bottom: 0.5rem;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  background: #0f1117;
  border: 1px solid #374151;
  border-radius: 8px;
  color: #e5e7eb;
  font-size: 0.95rem;
  transition: all 0.2s ease;
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: #6b7280;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  background: #1a1d26;
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
  line-height: 1.5;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

/* Tags Input */
.tags-input {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #0f1117;
  border: 1px solid #374151;
  border-radius: 8px;
  min-height: 44px;
  transition: border-color 0.2s ease;
}

.tags-input:focus-within {
  border-color: #3b82f6;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.75rem;
  background: #3b82f6;
  color: white;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
}

.tag-remove {
  background: none;
  border: none;
  color: white;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  margin-left: 0.25rem;
  opacity: 0.8;
  transition: opacity 0.2s ease;
}

.tag-remove:hover {
  opacity: 1;
}

.tag-input {
  flex: 1;
  min-width: 200px;
  background: transparent;
  border: none;
  color: #e5e7eb;
  font-size: 0.95rem;
  outline: none;
  padding: 0.25rem 0.5rem;
}

.tag-input::placeholder {
  color: #6b7280;
}

/* Methodologies Grid */
.methodologies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
}

.methodology-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: #0f1117;
  border: 1px solid #374151;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.methodology-checkbox:hover {
  background: #1a1d26;
  border-color: #3b82f6;
}

.methodology-checkbox input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  cursor: pointer;
}

.checkbox-custom {
  width: 20px;
  height: 20px;
  border: 2px solid #4b5563;
  border-radius: 4px;
  background: #0f1117;
  transition: all 0.2s ease;
  position: relative;
  flex-shrink: 0;
}

.methodology-checkbox input[type="checkbox"]:checked + .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
}

.methodology-checkbox input[type="checkbox"]:checked + .checkbox-custom::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 0.85rem;
  font-weight: bold;
}

.methodology-label {
  font-size: 0.95rem;
  color: #e5e7eb;
  font-weight: 500;
}

/* Actions */
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #2d3748;
}

.btn-primary,
.btn-secondary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.75rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.btn-secondary {
  background: #1f2937;
  color: #d1d5db;
  border: 1px solid #374151;
}

.btn-secondary:hover {
  background: #374151;
  border-color: #4b5563;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.material-symbols-outlined {
  font-size: 1.25rem;
}

/* Responsive */
@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .methodologies-grid {
    grid-template-columns: 1fr;
  }

  .actions {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
    justify-content: center;
  }
}
</style>
