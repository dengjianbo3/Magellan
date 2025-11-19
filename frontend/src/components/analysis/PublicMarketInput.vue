<template>
  <div class="public-market-input">
    <!-- Header -->
    <div class="header">
      <h1>{{ t('publicMarket.title') }}</h1>
      <p class="subtitle">{{ t('publicMarket.subtitle') }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="input-form">
      <!-- Target Company -->
      <div class="form-section">
        <h3 class="section-title">{{ t('publicMarket.targetCompany') }}</h3>
        <div class="form-group">
          <label class="form-label required">{{ t('publicMarket.tickerOrName') }}</label>
          <input
            v-model="formData.ticker"
            type="text"
            class="form-input"
            :placeholder="t('publicMarket.searchPlaceholder')"
            required
            @input="formData.ticker = formData.ticker.toUpperCase()"
          />
          <p class="form-hint">{{ t('publicMarket.tickerHint') }}</p>
        </div>
      </div>

      <!-- Select Research Period -->
      <div class="form-section">
        <h3 class="section-title">{{ t('publicMarket.selectResearchPeriod') }}</h3>
        <div class="period-selector">
          <div
            v-for="period in researchPeriods"
            :key="period.value"
            :class="['period-option', { 'selected': formData.research_period === period.value }]"
            @click="formData.research_period = period.value"
          >
            {{ t(period.labelKey) }}
          </div>
        </div>

        <!-- Custom Range (shown when Custom Range is selected) -->
        <div v-if="formData.research_period === 'custom'" class="custom-range">
          <div class="date-range">
            <div class="form-group">
              <label class="form-label">{{ t('publicMarket.startDate') }}</label>
              <input
                v-model="formData.custom_start_date"
                type="date"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('publicMarket.endDate') }}</label>
              <input
                v-model="formData.custom_end_date"
                type="date"
                class="form-input"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Choose Key Metrics -->
      <div class="form-section">
        <h3 class="section-title">{{ t('publicMarket.chooseKeyMetrics') }}</h3>
        <div class="metrics-grid">
          <div
            v-for="metric in keyMetrics"
            :key="metric.value"
            :class="['metric-chip', { 'selected': formData.key_metrics.includes(metric.value) }]"
            @click="toggleMetric(metric.value)"
          >
            {{ t(metric.labelKey) }}
          </div>
          <div class="metric-chip add-metric" @click="showAddMetricDialog">
            <span class="material-symbols-outlined">add</span>
            <span>{{ t('publicMarket.addMetric') }}</span>
          </div>
        </div>
      </div>

      <!-- Upload Filings or Research -->
      <div class="form-section">
        <h3 class="section-title">{{ t('publicMarket.uploadFilings') }}</h3>
        <div
          class="file-upload-area"
          :class="{ 'dragover': isDragging }"
          @drop.prevent="handleDrop"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @click="triggerFileInput"
        >
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf,.doc,.docx,.xls,.xlsx"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />

          <div v-if="uploadedFiles.length === 0" class="upload-placeholder">
            <span class="material-symbols-outlined upload-icon">cloud_upload</span>
            <p class="upload-text">{{ t('publicMarket.clickToUpload') }}</p>
            <p class="upload-hint">{{ t('publicMarket.uploadHint') }}</p>
          </div>

          <div v-else class="uploaded-files">
            <div v-for="(file, index) in uploadedFiles" :key="index" class="file-item">
              <span class="material-symbols-outlined file-icon">description</span>
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <button
                type="button"
                class="btn-remove"
                @click.stop="removeFile(index)"
              >
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="form-actions">
        <button type="button" class="btn-back" @click="handleBack">
          <span class="material-symbols-outlined">arrow_back</span>
          <span>{{ t('common.back') }}</span>
        </button>
        <button type="submit" class="btn-next">
          <span>{{ t('common.next') }}</span>
          <span class="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage';

const { t } = useLanguage();

// Emits
const emit = defineEmits(['target-configured', 'back']);

// State
const formData = ref({
  ticker: '',
  research_period: 'annually',
  custom_start_date: '',
  custom_end_date: '',
  key_metrics: ['pe_ratio', 'price_to_sales', 'roe'],
  filings_file_ids: []
});

const isDragging = ref(false);
const uploadedFiles = ref([]);
const fileInputRef = ref(null);

// Research Periods
const researchPeriods = computed(() => [
  { value: 'quarterly', labelKey: 'publicMarket.quarterly' },
  { value: 'annually', labelKey: 'publicMarket.annually' },
  { value: 'custom', labelKey: 'publicMarket.customRange' }
]);

// Key Metrics
const keyMetrics = computed(() => [
  { value: 'pe_ratio', labelKey: 'publicMarket.peRatio' },
  { value: 'price_to_sales', labelKey: 'publicMarket.priceToSales' },
  { value: 'roe', labelKey: 'publicMarket.roe' },
  { value: 'debt_to_equity', labelKey: 'publicMarket.debtToEquity' },
  { value: 'ebitda_margin', labelKey: 'publicMarket.ebitdaMargin' }
]);

// Methods
function toggleMetric(metricValue) {
  const index = formData.value.key_metrics.indexOf(metricValue);
  if (index > -1) {
    formData.value.key_metrics.splice(index, 1);
  } else {
    formData.value.key_metrics.push(metricValue);
  }
}

function showAddMetricDialog() {
  const customMetric = prompt(t('publicMarket.enterCustomMetric'));
  if (customMetric && customMetric.trim()) {
    const metricValue = customMetric.toLowerCase().replace(/\s+/g, '_');
    if (!formData.value.key_metrics.includes(metricValue)) {
      formData.value.key_metrics.push(metricValue);
    }
  }
}

function triggerFileInput() {
  fileInputRef.value?.click();
}

function handleFileSelect(event) {
  const files = Array.from(event.target.files);
  uploadedFiles.value.push(...files);
}

function handleDrop(event) {
  isDragging.value = false;
  const files = Array.from(event.dataTransfer.files);
  uploadedFiles.value.push(...files);
}

function removeFile(index) {
  uploadedFiles.value.splice(index, 1);
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function handleBack() {
  emit('back');
}

async function handleSubmit() {
  // Validate
  if (!formData.value.ticker) {
    alert(t('publicMarket.tickerRequired'));
    return;
  }

  if (formData.value.research_period === 'custom') {
    if (!formData.value.custom_start_date || !formData.value.custom_end_date) {
      alert(t('publicMarket.customRangeRequired'));
      return;
    }
  }

  // TODO: Upload files and get file IDs
  // For now, just emit the form data
  const targetData = {
    ticker: formData.value.ticker,
    research_period: formData.value.research_period,
    custom_start_date: formData.value.custom_start_date || undefined,
    custom_end_date: formData.value.custom_end_date || undefined,
    key_metrics: formData.value.key_metrics,
    filings_file_ids: formData.value.filings_file_ids
  };

  console.log('[PublicMarketInput] Submitting:', targetData);
  emit('target-configured', targetData);
}
</script>

<style scoped>
.public-market-input {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 32px;
}

/* Header */
.header {
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary, #e5e5e5);
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 14px;
  color: var(--text-secondary, #a1a1a1);
  margin: 0;
  line-height: 1.5;
}

/* Form */
.input-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Form Section */
.form-section {
  background: var(--card-bg, #1a1a1a);
  border: 1px solid var(--border-color, #3a3a3a);
  border-radius: 12px;
  padding: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #e5e5e5);
  margin: 0 0 16px 0;
}

/* Form Group */
.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #e5e5e5);
  margin-bottom: 8px;
}

.form-label.required::after {
  content: ' *';
  color: #ef4444;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-color, #3a3a3a);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary, #e5e5e5);
  background: var(--input-bg, #2a2a2a);
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color, #3b82f6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-hint {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin: 6px 0 0 0;
  line-height: 1.4;
}

/* Period Selector */
.period-selector {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.period-option {
  padding: 12px 16px;
  text-align: center;
  background: var(--secondary-bg, #2a2a2a);
  border: 2px solid var(--border-color, #3a3a3a);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #e5e5e5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.period-option:hover {
  background: var(--hover-bg, #3a3a3a);
}

.period-option.selected {
  background: var(--primary-color, #3b82f6);
  color: white;
  border-color: var(--primary-color, #3b82f6);
}

/* Custom Range */
.custom-range {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #3a3a3a);
}

.date-range {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

/* Metrics Grid */
.metrics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  background: var(--secondary-bg, #2a2a2a);
  border: 1px solid var(--border-color, #3a3a3a);
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #e5e5e5);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.metric-chip:hover {
  background: var(--hover-bg, #3a3a3a);
}

.metric-chip.selected {
  background: var(--primary-color, #3b82f6);
  color: white;
  border-color: var(--primary-color, #3b82f6);
}

.metric-chip.add-metric {
  background: transparent;
  border: 1px dashed var(--border-color, #3a3a3a);
  color: var(--text-secondary, #6b7280);
}

.metric-chip.add-metric:hover {
  border-color: var(--primary-color, #3b82f6);
  color: var(--primary-color, #3b82f6);
  background: rgba(59, 130, 246, 0.1);
}

/* File Upload */
.file-upload-area {
  border: 2px dashed var(--border-color, #3a3a3a);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--secondary-bg, #2a2a2a);
}

.file-upload-area:hover,
.file-upload-area.dragover {
  border-color: var(--primary-color, #3b82f6);
  background: rgba(59, 130, 246, 0.1);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 48px;
  color: var(--icon-color, #9ca3af);
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #e5e5e5);
  margin: 0;
}

.upload-hint {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin: 0;
}

/* Uploaded Files */
.uploaded-files {
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--card-bg, #1a1a1a);
  border: 1px solid var(--border-color, #3a3a3a);
  border-radius: 8px;
}

.file-icon {
  font-size: 24px;
  color: var(--icon-color, #6b7280);
}

.file-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #e5e5e5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
}

.btn-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: var(--secondary-bg, #2a2a2a);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-remove:hover {
  background: #fee2e2;
  color: #dc2626;
}

.btn-remove .material-symbols-outlined {
  font-size: 18px;
}

/* Action Buttons */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 24px;
  border-top: 1px solid var(--border-color, #3a3a3a);
}

.btn-back,
.btn-next {
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
}

.btn-back {
  background: var(--secondary-bg, #4b5563);
  color: white;
  border: 1px solid var(--border-color, #3a3a3a);
}

.btn-back:hover {
  background: var(--secondary-hover, #374151);
}

.btn-next {
  background: var(--primary-color, #3b82f6);
  color: white;
}

.btn-next:hover {
  background: var(--primary-hover, #2563eb);
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
  .public-market-input {
    padding: 16px;
  }

  .period-selector {
    grid-template-columns: 1fr;
  }

  .date-range {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column-reverse;
    gap: 12px;
  }

  .form-actions button {
    width: 100%;
    justify-content: center;
  }
}
</style>
