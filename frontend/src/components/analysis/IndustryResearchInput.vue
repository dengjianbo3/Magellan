<template>
  <div class="industry-research-input">
    <!-- Header -->
    <div class="input-header">
      <h1 class="input-title">{{ t('industryResearch.defineTarget') }}</h1>
      <p class="input-subtitle">{{ t('industryResearch.defineTargetDesc') }}</p>
    </div>

    <!-- Form Content -->
    <div class="form-content">
      <!-- Industry Name & Research Scope -->
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">
            {{ t('industryResearch.industryName') }}
            <span class="required">*</span>
          </label>
          <input
            v-model="formData.industry_name"
            type="text"
            class="form-input"
            :placeholder="t('industryResearch.industryPlaceholder')"
          />
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('industryResearch.researchScope') }}</label>
          <select v-model="formData.geo_scope" class="form-input form-select">
            <option value="">{{ t('industryResearch.selectScope') }}</option>
            <option value="global">{{ t('industryResearch.global') }}</option>
            <option value="china">{{ t('industryResearch.china') }}</option>
            <option value="us">{{ t('industryResearch.us') }}</option>
            <option value="europe">{{ t('industryResearch.europe') }}</option>
            <option value="asia">{{ t('industryResearch.asia') }}</option>
          </select>
        </div>
      </div>

      <!-- Main Products/Services -->
      <div class="form-group">
        <label class="form-label">{{ t('industryResearch.mainProducts') }}</label>
        <textarea
          v-model="formData.main_products"
          class="form-input form-textarea"
          rows="3"
          :placeholder="t('industryResearch.mainProductsPlaceholder')"
        ></textarea>
      </div>

      <!-- Market Size Row -->
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">{{ t('industryResearch.marketSize') }}</label>
          <div class="input-with-unit">
            <input
              v-model.number="formData.market_size"
              type="number"
              class="form-input"
              :placeholder="t('industryResearch.marketSizePlaceholder')"
              min="0"
              step="1"
            />
            <span class="input-unit">{{ t('industryResearch.billionYuan') }}</span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('industryResearch.maxRegions') }}</label>
          <input
            v-model.number="formData.max_regions"
            type="number"
            class="form-input"
            :placeholder="t('industryResearch.maxRegionsPlaceholder')"
            min="0"
          />
        </div>
      </div>

      <!-- Key Participants (Tags) -->
      <div class="form-group">
        <label class="form-label">{{ t('industryResearch.keyParticipants') }}</label>
        <div class="tags-container">
          <div
            v-for="(participant, index) in formData.key_participants"
            :key="index"
            class="tag"
          >
            <span class="tag-text">{{ participant }}</span>
            <button
              type="button"
              class="tag-remove"
              @click="removeParticipant(index)"
              :title="t('common.remove')"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <input
            v-model="newParticipant"
            type="text"
            class="tag-input"
            :placeholder="t('industryResearch.participantPlaceholder')"
            @keydown.enter.prevent="addParticipant"
          />
        </div>
        <p class="form-hint">{{ t('industryResearch.participantHint') }}</p>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="form-footer">
      <button type="button" class="btn-back" @click="handleBack">
        <span class="material-symbols-outlined">arrow_back</span>
        {{ t('common.cancel') }}
      </button>
      <button type="button" class="btn-next" @click="handleNext">
        <span class="material-symbols-outlined">auto_awesome</span>
        {{ t('industryResearch.startAnalysis') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useLanguage } from '@/composables/useLanguage';

const { t } = useLanguage();

// Emits
const emit = defineEmits(['target-configured', 'back']);

// Form Data
const formData = ref({
  industry_name: '',
  geo_scope: '',
  main_products: '',
  market_size: null,
  max_regions: null,
  key_participants: []
});

const newParticipant = ref('');

// Methods
function addParticipant() {
  const value = newParticipant.value.trim();
  if (value && !formData.value.key_participants.includes(value)) {
    formData.value.key_participants.push(value);
    newParticipant.value = '';
  }
}

function removeParticipant(index) {
  formData.value.key_participants.splice(index, 1);
}

function handleBack() {
  emit('back');
}

function handleNext() {
  // Validation
  if (!formData.value.industry_name) {
    alert(t('industryResearch.industryNameRequired'));
    return;
  }

  // Build research_topic from industry_name and geo_scope
  const geoText = formData.value.geo_scope
    ? t(`industryResearch.${formData.value.geo_scope}`)
    : '';
  const research_topic = `${geoText}${formData.value.industry_name}${t('industryResearch.marketResearch')}`;

  const targetData = {
    industry_name: formData.value.industry_name,
    research_topic: research_topic,
    geo_scope: formData.value.geo_scope || 'global',
    main_products: formData.value.main_products,
    market_size: formData.value.market_size,
    max_regions: formData.value.max_regions,
    key_participants: formData.value.key_participants
  };

  console.log('[IndustryResearchInput] Target configured:', targetData);
  emit('target-configured', targetData);
}
</script>

<style scoped>
.industry-research-input {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  color: #e5e5e5;
}

/* Header */
.input-header {
  margin-bottom: 2rem;
}

.input-title {
  font-size: 2rem;
  font-weight: 700;
  color: #e5e5e5;
  margin: 0 0 0.5rem 0;
}

.input-subtitle {
  font-size: 1rem;
  color: #a1a1a1;
  margin: 0;
}

/* Form Content */
.form-content {
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-row:last-child {
  margin-bottom: 0;
}

.form-label {
  font-size: 0.95rem;
  font-weight: 500;
  color: #e5e5e5;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.required {
  color: #ef4444;
  font-size: 1.1rem;
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
  font-family: inherit;
}

.form-input::placeholder {
  color: #6b7280;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  background: #2a2a2a;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
  line-height: 1.5;
}

.input-with-unit {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-unit .form-input {
  flex: 1;
  padding-right: 5rem;
}

.input-unit {
  position: absolute;
  right: 0.75rem;
  font-size: 0.9rem;
  color: #6b7280;
  pointer-events: none;
}

/* Tags */
.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  min-height: 48px;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: #3b82f6;
  color: white;
  border-radius: 6px;
  font-size: 0.875rem;
}

.tag-text {
  line-height: 1;
}

.tag-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.2s;
  padding: 0;
}

.tag-remove:hover {
  background: rgba(255, 255, 255, 0.3);
}

.tag-remove .material-symbols-outlined {
  font-size: 14px;
  color: white;
}

.tag-input {
  flex: 1;
  min-width: 120px;
  padding: 0.375rem 0;
  border: none;
  background: transparent;
  color: #e5e5e5;
  font-size: 0.875rem;
  outline: none;
}

.tag-input::placeholder {
  color: #6b7280;
}

.form-hint {
  font-size: 0.85rem;
  color: #6b7280;
  margin: 0.25rem 0 0 0;
}

/* Footer */
.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1.5rem;
  border-top: 1px solid #3a3a3a;
}

.btn-back,
.btn-next {
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

.btn-next {
  background: #3b82f6;
  color: white;
}

.btn-next:hover {
  background: #2563eb;
}

.btn-back .material-symbols-outlined,
.btn-next .material-symbols-outlined {
  font-size: 20px;
}

/* Responsive */
@media (max-width: 768px) {
  .industry-research-input {
    padding: 1rem;
  }

  .input-title {
    font-size: 1.5rem;
  }

  .form-content {
    padding: 1.5rem;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .form-footer {
    flex-direction: column;
    gap: 1rem;
  }

  .btn-back,
  .btn-next {
    width: 100%;
    justify-content: center;
  }
}
</style>
