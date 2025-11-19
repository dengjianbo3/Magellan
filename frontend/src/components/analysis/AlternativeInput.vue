<template>
  <div class="alternative-input">
    <!-- Header -->
    <div class="header">
      <h1>{{ t('alternative.title') }}</h1>
      <p class="subtitle">{{ t('alternative.subtitle') }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="input-form">
      <!-- Project Overview -->
      <div class="form-section">
        <h3 class="section-title">{{ t('alternative.projectOverview') }}</h3>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label required">{{ t('alternative.assetClass') }}</label>
            <select v-model="formData.asset_type" class="form-select" required>
              <option value="">{{ t('alternative.selectAssetClass') }}</option>
              <option value="crypto">{{ t('alternative.crypto') }}</option>
              <option value="defi">{{ t('alternative.defi') }}</option>
              <option value="nft">{{ t('alternative.nft') }}</option>
              <option value="web3">{{ t('alternative.web3') }}</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label required">{{ t('alternative.projectName') }}</label>
            <input
              v-model="formData.project_name"
              type="text"
              class="form-input"
              :placeholder="t('alternative.projectNamePlaceholder')"
              required
            />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('alternative.investmentSize') }}</label>
          <div class="input-with-currency">
            <span class="currency-prefix">$</span>
            <input
              v-model.number="formData.investment_size"
              type="number"
              class="form-input-currency"
              placeholder="5,000,000"
              step="1000"
            />
            <span class="currency-suffix">USD</span>
          </div>
        </div>
      </div>

      <!-- Documentation -->
      <div class="form-section">
        <h3 class="section-title">{{ t('alternative.documentation') }}</h3>
        <p class="section-hint">{{ t('alternative.dueDiligenceReport') }}</p>

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
            accept=".pdf,.doc,.docx,.xlsx,.xls"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />

          <div v-if="uploadedFiles.length === 0" class="upload-placeholder">
            <span class="material-symbols-outlined upload-icon">cloud_upload</span>
            <p class="upload-text">{{ t('alternative.clickToUpload') }}</p>
            <p class="upload-hint">{{ t('alternative.uploadHint') }}</p>
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

      <!-- Key Stakeholders -->
      <div class="form-section">
        <h3 class="section-title">{{ t('alternative.keyStakeholders') }}</h3>
        <p class="section-hint">{{ t('alternative.projectTeamMembers') }}</p>

        <div class="team-members-list">
          <div v-for="(member, index) in formData.team_members" :key="index" class="team-member-row">
            <div class="member-field">
              <label class="field-label">{{ t('alternative.name') }}</label>
              <input
                v-model="member.name"
                type="text"
                class="form-input"
                :placeholder="t('alternative.namePlaceholder')"
              />
            </div>
            <div class="member-field">
              <label class="field-label">{{ t('alternative.role') }}</label>
              <input
                v-model="member.role"
                type="text"
                class="form-input"
                :placeholder="t('alternative.rolePlaceholder')"
              />
            </div>
            <button
              v-if="formData.team_members.length > 1"
              type="button"
              class="btn-remove-member"
              @click="removeMember(index)"
            >
              <span class="material-symbols-outlined">delete</span>
            </button>
          </div>
        </div>

        <button type="button" class="btn-add-member" @click="addMember">
          <span class="material-symbols-outlined">add</span>
          <span>{{ t('alternative.addMember') }}</span>
        </button>
      </div>

      <!-- Analysis Directives -->
      <div class="form-section">
        <h3 class="section-title">{{ t('alternative.analysisDirectives') }}</h3>
        <p class="section-hint">{{ t('alternative.keyQuestions') }}</p>

        <textarea
          v-model="formData.analysis_directives"
          rows="4"
          class="form-textarea"
          :placeholder="t('alternative.analysisDirectivesPlaceholder')"
        ></textarea>
      </div>

      <!-- Risk Warning -->
      <div class="warning-box">
        <span class="material-symbols-outlined warning-icon">warning</span>
        <div class="warning-content">
          <strong>{{ t('alternative.riskWarningTitle') }}</strong>
          <p>{{ t('alternative.riskWarningText') }}</p>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="form-actions">
        <button type="button" class="btn-back" @click="handleBack">
          <span class="material-symbols-outlined">arrow_back</span>
          <span>{{ t('common.back') }}</span>
        </button>
        <button type="submit" class="btn-next">
          <span>{{ t('alternative.startAnalysis') }}</span>
          <span class="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useLanguage } from '@/composables/useLanguage';

const { t } = useLanguage();

// Emits
const emit = defineEmits(['target-configured', 'back']);

// State
const formData = ref({
  asset_type: '',
  project_name: '',
  investment_size: null,
  dd_file_ids: [],
  team_members: [
    { name: '', role: '' }
  ],
  analysis_directives: ''
});

const isDragging = ref(false);
const uploadedFiles = ref([]);
const fileInputRef = ref(null);

// Methods
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

function addMember() {
  formData.value.team_members.push({ name: '', role: '' });
}

function removeMember(index) {
  formData.value.team_members.splice(index, 1);
}

function handleBack() {
  emit('back');
}

async function handleSubmit() {
  // Validate
  if (!formData.value.asset_type) {
    alert(t('alternative.assetTypeRequired'));
    return;
  }

  if (!formData.value.project_name) {
    alert(t('alternative.projectNameRequired'));
    return;
  }

  // TODO: Upload files and get file IDs
  const targetData = {
    asset_type: formData.value.asset_type,
    project_name: formData.value.project_name,
    investment_size: formData.value.investment_size || undefined,
    dd_file_ids: formData.value.dd_file_ids,
    team_members: formData.value.team_members.filter(m => m.name || m.role),
    analysis_directives: formData.value.analysis_directives || undefined
  };

  console.log('[AlternativeInput] Submitting:', targetData);
  emit('target-configured', targetData);
}
</script>

<style scoped>
.alternative-input {
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
  color: #e5e5e5;
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 14px;
  color: #a1a1a1;
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
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 12px;
  padding: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #e5e5e5;
  margin: 0 0 8px 0;
}

.section-hint {
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 16px 0;
}

/* Form Row */
.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.form-row:last-child {
  margin-bottom: 0;
}

/* Form Group */
.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label,
.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #e5e5e5;
  margin-bottom: 8px;
}

.form-label.required::after {
  content: ' *';
  color: #ef4444;
}

.form-select,
.form-input,
.form-textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  font-size: 14px;
  color: #e5e5e5;
  background: #2a2a2a;
  transition: all 0.2s ease;
}

.form-select:focus,
.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
  line-height: 1.5;
}

/* Currency Input */
.input-with-currency {
  display: flex;
  align-items: center;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  padding: 0 14px;
  transition: all 0.2s ease;
}

.input-with-currency:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.currency-prefix,
.currency-suffix {
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  white-space: nowrap;
}

.currency-prefix {
  margin-right: 8px;
}

.currency-suffix {
  margin-left: 8px;
}

.form-input-currency {
  flex: 1;
  padding: 10px 0;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #e5e5e5;
}

.form-input-currency:focus {
  outline: none;
}

/* File Upload */
.file-upload-area {
  border: 2px dashed #3a3a3a;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #2a2a2a;
}

.file-upload-area:hover,
.file-upload-area.dragover {
  border-color: #3b82f6;
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
  color: #9ca3af;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: #e5e5e5;
  margin: 0;
}

.upload-hint {
  font-size: 13px;
  color: #6b7280;
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
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
}

.file-icon {
  font-size: 24px;
  color: #6b7280;
}

.file-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #e5e5e5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 13px;
  color: #6b7280;
}

.btn-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: #2a2a2a;
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

/* Team Members */
.team-members-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.team-member-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 12px;
  align-items: end;
}

.member-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: #a1a1a1;
  margin: 0;
}

.btn-remove-member {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #e5e5e5;
}

.btn-remove-member:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #dc2626;
}

.btn-add-member {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 10px;
  background: transparent;
  border: 1px dashed #3a3a3a;
  border-radius: 8px;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-add-member:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

/* Warning Box */
.warning-box {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid #f59e0b;
  border-radius: 8px;
}

.warning-icon {
  font-size: 24px;
  color: #f59e0b;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-content strong {
  display: block;
  font-size: 14px;
  color: #fbbf24;
  margin-bottom: 4px;
}

.warning-content p {
  font-size: 13px;
  color: #a1a1a1;
  line-height: 1.5;
  margin: 0;
}

/* Action Buttons */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 24px;
  border-top: 1px solid #3a3a3a;
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
  background: #4b5563;
  color: white;
}

.btn-back:hover {
  background: #374151;
}

.btn-next {
  background: #3b82f6;
  color: white;
}

.btn-next:hover {
  background: #2563eb;
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
  .alternative-input {
    padding: 16px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .team-member-row {
    grid-template-columns: 1fr;
  }

  .btn-remove-member {
    width: 100%;
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
