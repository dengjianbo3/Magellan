<template>
  <div class="early-stage-input">
    <!-- Progress Steps -->
    <div class="progress-steps">
      <div class="step completed">
        <div class="step-number">1</div>
        <div class="step-label">{{ t('earlyStage.selectScenario') }}</div>
      </div>
      <div class="step active">
        <div class="step-number">2</div>
        <div class="step-label">{{ t('earlyStage.inputTarget') }}</div>
      </div>
      <div class="step">
        <div class="step-number">3</div>
        <div class="step-label">{{ t('earlyStage.configAnalysis') }}</div>
      </div>
      <div class="step">
        <div class="step-number">4</div>
        <div class="step-label">{{ t('earlyStage.analyzing') }}</div>
      </div>
    </div>

    <!-- Header -->
    <div class="header">
      <h1>{{ t('earlyStage.title') }}</h1>
      <p class="subtitle">{{ t('earlyStage.subtitle') }}</p>
    </div>

    <!-- Form -->
    <form @submit.prevent="handleSubmit" class="input-form">
      <!-- 公司名称 -->
      <div class="form-group">
        <label class="form-label required">
          {{ t('earlyStage.companyName') }}
        </label>
        <input
          v-model="formData.company_name"
          type="text"
          class="form-input"
          :placeholder="t('earlyStage.companyNamePlaceholder')"
          required
        />
        <span class="form-hint">{{ t('earlyStage.companyNameHint') }}</span>
      </div>

      <!-- 融资阶段 -->
      <div class="form-group">
        <label class="form-label required">
          {{ t('earlyStage.fundingStage') }}
        </label>
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

      <!-- 所属行业 -->
      <div class="form-group">
        <label class="form-label">
          {{ t('earlyStage.industry') }}
        </label>
        <input
          v-model="formData.industry"
          type="text"
          class="form-input"
          :placeholder="t('earlyStage.industryPlaceholder')"
        />
      </div>

      <!-- 商业计划书上传 -->
      <div class="form-group">
        <label class="form-label">
          {{ t('earlyStage.businessPlan') }}
        </label>
        <div class="file-upload-area">
          <input
            ref="fileInput"
            type="file"
            @change="handleFileChange"
            accept=".pdf,.ppt,.pptx,.doc,.docx"
            style="display: none"
          />
          <div v-if="!uploadedFile" class="upload-prompt" @click="$refs.fileInput.click()">
            <span class="material-symbols-outlined upload-icon">upload_file</span>
            <div class="upload-text">
              <div class="upload-title">{{ t('earlyStage.clickToUpload') }}</div>
              <div class="upload-hint">{{ t('earlyStage.supportedFormats') }}</div>
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
            <div class="progress-text">{{ t('earlyStage.uploading') }}...</div>
          </div>
        </div>
      </div>

      <!-- 成立年份 -->
      <div class="form-group">
        <label class="form-label">
          {{ t('earlyStage.foundedYear') }}
        </label>
        <input
          v-model.number="formData.founded_year"
          type="text"
          class="form-input"
          :placeholder="t('earlyStage.foundedYearPlaceholder')"
        />
      </div>

      <!-- 团队成员 -->
      <div class="form-group">
        <label class="form-label">
          {{ t('earlyStage.teamMembers') }}
        </label>
        <textarea
          v-model="teamMembersText"
          class="form-textarea"
          :placeholder="t('earlyStage.teamMembersPlaceholder')"
          rows="5"
        ></textarea>
        <span class="form-hint">{{ t('earlyStage.teamMembersHint') }}</span>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button type="button" class="btn-back" @click="$emit('back')">
          <span class="material-symbols-outlined">arrow_back</span>
          <span>{{ t('earlyStage.back') }}</span>
        </button>
        <button type="submit" class="btn-next" :disabled="!isValid">
          <span>{{ t('earlyStage.next') }}</span>
          <span class="material-symbols-outlined">arrow_forward</span>
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
  { value: 'angel', label: 'Angel', icon: '👼' },
  { value: 'seed', label: 'Seed', icon: '🌱' },
  { value: 'pre-a', label: 'Pre-A', icon: '🚀' },
  { value: 'series-a', label: 'Series A', icon: '💎' }
]);

const formData = ref({
  company_name: '',
  stage: '',
  industry: '',
  bp_file_id: null,
  founded_year: null,
  team_members: []
});

const uploadedFile = ref(null);
const uploading = ref(false);
const teamMembersText = ref('');

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

    const response = await fetch('http://localhost:8000/api/upload_bp', {
      method: 'POST',
      body: formDataUpload
    });

    if (!response.ok) {
      throw new Error('Upload failed');
    }

    const result = await response.json();
    formData.value.bp_file_id = result.file_id;
    uploadedFile.value = file;

    console.log('[EarlyStageInput] File uploaded:', result);

  } catch (error) {
    console.error('[EarlyStageInput] Upload error:', error);
    alert(t('earlyStage.uploadError'));
  } finally {
    uploading.value = false;
  }
}

function removeFile() {
  uploadedFile.value = null;
  formData.value.bp_file_id = null;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function handleSubmit() {
  if (!isValid.value) {
    return;
  }

  // 解析团队成员
  if (teamMembersText.value.trim()) {
    const members = teamMembersText.value
      .split('\n')
      .filter(line => line.trim())
      .map(line => {
        const parts = line.split(',').map(s => s.trim());
        return {
          name: parts[0] || '',
          role: parts[1] || '',
          background: parts[2] || ''
        };
      });
    formData.value.team_members = members;
  }

  emit('target-configured', formData.value);
}
</script>

<style scoped>
.early-stage-input {
  max-width: 700px;
  margin: 0 auto;
  padding: 2rem;
}

/* Progress Steps */
.progress-steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 3rem;
  position: relative;
}

.progress-steps::before {
  content: '';
  position: absolute;
  top: 20px;
  left: 0;
  right: 0;
  height: 2px;
  background: #374151;
  z-index: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  position: relative;
  z-index: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #1f2937;
  border: 2px solid #374151;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: #6b7280;
  font-size: 16px;
  transition: all 0.3s ease;
}

.step.completed .step-number {
  background: #10b981;
  border-color: #10b981;
  color: white;
}

.step.active .step-number {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

.step-label {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  white-space: nowrap;
}

.step.completed .step-label,
.step.active .step-label {
  color: #d1d5db;
  font-weight: 500;
}

/* Header */
.header {
  text-align: center;
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
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.75rem;
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

.form-textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 14px;
  background: #111827;
  border: 1px solid #374151;
  color: #f3f4f6;
  border-radius: 8px;
  resize: vertical;
  min-height: 120px;
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

.form-hint {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-top: 0.375rem;
}

/* Stage Selector */
.stage-selector {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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
  padding: 1.5rem;
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
  font-size: 2.5rem;
  color: #6b7280;
}

.upload-text {
  flex: 1;
}

.upload-title {
  font-size: 14px;
  font-weight: 500;
  color: #d1d5db;
  margin-bottom: 0.25rem;
}

.upload-hint {
  font-size: 12px;
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

/* Actions */
.form-actions {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 2rem;
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
  .early-stage-input {
    padding: 1rem;
  }

  .stage-selector {
    grid-template-columns: repeat(2, 1fr);
  }

  .step-label {
    font-size: 10px;
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
