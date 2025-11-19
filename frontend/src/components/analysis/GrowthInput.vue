<template>
  <div class="growth-input">
    <!-- Header -->
    <div class="header">
      <h1>{{ t('growthStage.title') }}</h1>
      <p class="subtitle">{{ t('growthStage.subtitle') }}</p>
    </div>

    <!-- Form -->
    <form @submit.prevent="handleSubmit" class="input-form">
      <!-- Basic Company Information -->
      <div class="form-section">
        <h3 class="section-title">{{ t('growthStage.basicInfo') }}</h3>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label required">{{ t('growthStage.companyName') }}</label>
            <input
              v-model="formData.company_name"
              type="text"
              class="form-input"
              :placeholder="t('growthStage.companyNamePlaceholder')"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('growthStage.tickerSymbol') }}</label>
            <input
              v-model="formData.ticker_symbol"
              type="text"
              class="form-input"
              :placeholder="t('growthStage.tickerPlaceholder')"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">{{ t('growthStage.industrySector') }}</label>
            <input
              v-model="formData.industry"
              type="text"
              class="form-input"
              :placeholder="t('growthStage.industryPlaceholder')"
            />
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('growthStage.headquarters') }}</label>
            <input
              v-model="formData.headquarters"
              type="text"
              class="form-input"
              :placeholder="t('growthStage.headquartersPlaceholder')"
            />
          </div>
        </div>

        <!-- Stage Selection -->
        <div class="form-group">
          <label class="form-label required">{{ t('growthStage.fundingStage') }}</label>
          <div class="stage-selector">
            <div
              v-for="stage in fundingStages"
              :key="stage.value"
              :class="['stage-option', { 'selected': formData.stage === stage.value }]"
              @click="formData.stage = stage.value"
            >
              <div class="stage-icon">{{ stage.icon }}</div>
              <div class="stage-name">{{ stage.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Financial Data -->
      <div class="form-section">
        <h3 class="section-title">{{ t('growthStage.financialData') }}</h3>
        <p class="section-hint">{{ t('growthStage.financialDataHint') }}</p>

        <div class="file-upload-area">
          <input
            ref="fileInput"
            type="file"
            @change="handleFileChange"
            accept=".csv,.xlsx,.xls,.pdf"
            style="display: none"
          />
          <div v-if="!uploadedFile" class="upload-prompt" @click="$refs.fileInput.click()">
            <span class="material-symbols-outlined upload-icon">cloud_upload</span>
            <div class="upload-text">
              <div class="upload-title">{{ t('growthStage.clickToUpload') }}</div>
              <div class="upload-hint">{{ t('growthStage.financialFormats') }}</div>
            </div>
          </div>
          <div v-else class="file-uploaded">
            <span class="material-symbols-outlined file-icon">description</span>
            <div class="file-info">
              <div class="file-name">{{ uploadedFile.name }}</div>
              <div class="file-size">{{ formatFileSize(uploadedFile.size) }}</div>
            </div>
            <button type="button" class="btn-remove" @click="removeFile">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div v-if="uploading" class="upload-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: '60%' }"></div>
            </div>
            <div class="progress-text">{{ t('growthStage.uploading') }}...</div>
          </div>
        </div>
      </div>

      <!-- Market Positioning & Strategy -->
      <div class="form-section">
        <h3 class="section-title">{{ t('growthStage.marketPositioning') }}</h3>

        <div class="form-group">
          <label class="form-label">{{ t('growthStage.coreProducts') }}</label>
          <textarea
            v-model="formData.core_products"
            class="form-textarea"
            :placeholder="t('growthStage.coreProductsPlaceholder')"
            rows="3"
          ></textarea>
        </div>
      </div>

      <!-- Competitive Landscape -->
      <div class="form-section">
        <h3 class="section-title">{{ t('growthStage.competitiveLandscape') }}</h3>

        <div
          v-for="(competitor, index) in formData.competitors"
          :key="index"
          class="competitor-row"
        >
          <input
            v-model="competitor.name"
            type="text"
            class="form-input"
            :placeholder="t('growthStage.competitorName')"
          />
          <input
            v-model="competitor.market_share"
            type="text"
            class="form-input small"
            :placeholder="t('growthStage.marketShare')"
          />
          <button
            v-if="formData.competitors.length > 1"
            type="button"
            class="btn-remove-row"
            @click="removeCompetitor(index)"
          >
            <span class="material-symbols-outlined">delete</span>
          </button>
        </div>

        <button type="button" class="btn-add" @click="addCompetitor">
          <span class="material-symbols-outlined">add_circle</span>
          <span>{{ t('growthStage.addCompetitor') }}</span>
        </button>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button type="button" class="btn-back" @click="$emit('back')">
          <span class="material-symbols-outlined">arrow_back</span>
          <span>{{ t('growthStage.back') }}</span>
        </button>
        <button type="submit" class="btn-next" :disabled="!isValid">
          <span>{{ t('growthStage.startAnalysis') }}</span>
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

defineProps({
  scenario: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['target-configured', 'back']);

const fundingStages = computed(() => [
  { value: 'series-b', label: 'Series B', icon: '🚀' },
  { value: 'series-c', label: 'Series C', icon: '📈' },
  { value: 'series-d', label: 'Series D', icon: '💫' },
  { value: 'series-e', label: 'Series E', icon: '⭐' },
  { value: 'pre-ipo', label: 'Pre-IPO', icon: '🏆' }
]);

const formData = ref({
  company_name: '',
  ticker_symbol: '',
  industry: '',
  headquarters: '',
  stage: '',
  financial_file_id: null,
  core_products: '',
  competitors: [
    { name: '', market_share: '' }
  ]
});

const uploadedFile = ref(null);
const uploading = ref(false);

const isValid = computed(() => {
  return formData.value.company_name.trim() && formData.value.stage;
});

async function handleFileChange(event) {
  const file = event.target.files[0];
  if (!file) return;

  uploading.value = true;

  try {
    const formDataUpload = new FormData();
    formDataUpload.append('file', file);

    const response = await fetch('http://localhost:8000/api/upload_financial', {
      method: 'POST',
      body: formDataUpload
    });

    if (!response.ok) {
      throw new Error('Upload failed');
    }

    const result = await response.json();
    formData.value.financial_file_id = result.file_id;
    uploadedFile.value = file;

    console.log('[GrowthInput] File uploaded:', result);

  } catch (error) {
    console.error('[GrowthInput] Upload error:', error);
    alert(t('growthStage.uploadError'));
  } finally {
    uploading.value = false;
  }
}

function removeFile() {
  uploadedFile.value = null;
  formData.value.financial_file_id = null;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function addCompetitor() {
  formData.value.competitors.push({ name: '', market_share: '' });
}

function removeCompetitor(index) {
  formData.value.competitors.splice(index, 1);
}

function handleSubmit() {
  if (!isValid.value) {
    return;
  }

  // 过滤空的competitors
  const validCompetitors = formData.value.competitors
    .filter(c => c.name.trim())
    .map(c => ({
      name: c.name.trim(),
      market_share: c.market_share.trim()
    }));

  const payload = {
    ...formData.value,
    competitors: validCompetitors
  };

  emit('target-configured', payload);
}
</script>

<style scoped>
.growth-input {
  max-width: 900px;
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
.input-form {
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

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 1rem;
}

.section-hint {
  font-size: 0.875rem;
  color: #9ca3af;
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.form-row:last-child {
  margin-bottom: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #d1d5db;
  margin-bottom: 0.5rem;
}

.form-label.required::after {
  content: ' *';
  color: #ef4444;
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 14px;
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

.form-input.small {
  max-width: 150px;
}

.form-textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 14px;
  background: #111827;
  border: 1px solid #374151;
  color: #f3f4f6;
  border-radius: 8px;
  resize: vertical;
  min-height: 100px;
  font-family: inherit;
  line-height: 1.6;
  transition: all 0.2s ease;
}

.form-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-textarea::placeholder {
  color: #6b7280;
}

/* Stage Selector */
.stage-selector {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75rem;
}

.stage-option {
  padding: 1rem;
  background: #111827;
  border: 2px solid #374151;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.stage-option:hover {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
}

.stage-option.selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.15);
}

.stage-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.stage-name {
  font-size: 13px;
  font-weight: 500;
  color: #d1d5db;
}

/* File Upload */
.file-upload-area {
  position: relative;
}

.upload-prompt {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  background: #111827;
  border: 2px dashed #374151;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-prompt:hover {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
}

.upload-icon {
  font-size: 3rem;
  color: #6b7280;
}

.upload-text {
  flex: 1;
}

.upload-title {
  font-size: 15px;
  font-weight: 500;
  color: #d1d5db;
  margin-bottom: 0.25rem;
}

.upload-hint {
  font-size: 13px;
  color: #6b7280;
}

.file-uploaded {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
}

.file-icon {
  font-size: 2rem;
  color: #10b981;
}

.file-info {
  flex: 1;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #d1d5db;
  margin-bottom: 0.125rem;
}

.file-size {
  font-size: 12px;
  color: #6b7280;
}

.btn-remove {
  padding: 0.5rem;
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.btn-remove:hover {
  background: rgba(239, 68, 68, 0.1);
}

.upload-progress {
  margin-top: 0.75rem;
}

.progress-bar {
  height: 4px;
  background: #374151;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
}

/* Competitor Rows */
.competitor-row {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.75rem;
}

.btn-remove-row {
  padding: 0.5rem;
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.btn-remove-row:hover {
  background: rgba(239, 68, 68, 0.1);
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 6px;
  color: #d1d5db;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-add:hover {
  background: #4b5563;
  border-color: #6b7280;
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

.btn-back,
.btn-next {
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

.btn-back {
  background: #374151;
  color: #d1d5db;
}

.btn-back:hover {
  background: #4b5563;
}

.btn-next {
  background: #3b82f6;
  color: white;
}

.btn-next:hover:not(:disabled) {
  background: #2563eb;
  transform: translateX(2px);
}

.btn-next:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 768px) {
  .growth-input {
    padding: 1rem;
  }

  .input-form {
    padding: 1.5rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .stage-selector {
    grid-template-columns: repeat(2, 1fr);
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-back,
  .btn-next {
    width: 100%;
    justify-content: center;
  }
}
</style>
