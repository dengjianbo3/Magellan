<template>
  <div class="unified-analysis-form w-full max-w-5xl mx-auto">


    <!-- Scenario Header -->
    <div class="glass-card p-8 mb-8">
      <div class="flex items-center gap-4">
        <div class="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center text-4xl backdrop-blur-sm border border-primary/20">
          {{ scenario.icon }}
        </div>
        <div>
          <h2 class="text-2xl font-bold text-white">{{ getScenarioName(scenario) }}</h2>
          <p class="text-text-secondary mt-1">{{ getScenarioDescription(scenario) }}</p>
        </div>
      </div>
    </div>

    <!-- Main Form -->
    <form @submit.prevent="handleSubmit">
      <div class="glass-card p-8 mb-6">
        <!-- Section 1: Target Input -->
        <h3 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">target</span>
          <span>{{ t('analysisWizard.targetInfo') }}</span>
        </h3>

        <!-- Dynamic Fields from scenario configuration -->
        <div class="space-y-6">
          <DynamicFormField
            v-for="field in formFields"
            :key="field.name"
            :ref="el => fieldRefs[field.name] = el"
            :field="field"
            v-model="formData[field.name]"
          />
        </div>
      </div>

      <div class="glass-card p-8 mb-6">
        <!-- Section 2: Analysis Configuration -->
        <h3 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">settings</span>
          <span>{{ t('analysisWizard.analysisSettings') }}</span>
        </h3>

        <!-- Analysis Mode Selection -->
        <div class="mb-6">
          <label class="form-label required">{{ t('analysisWizard.analysisMode') }}</label>
          <div class="mode-selector grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            <!-- Quick Mode -->
            <div
              :class="[
                'mode-card',
                { 'selected': config.mode === 'quick' }
              ]"
              @click="config.mode = 'quick'"
            >
              <div class="mode-icon">
                <span class="material-symbols-outlined">flash_on</span>
              </div>
              <div class="mode-content">
                <h4 class="mode-title">{{ t('analysisWizard.quickMode') }}</h4>
                <p class="mode-description">{{ t('analysisWizard.quickModeDesc') }}</p>
                <div class="mode-duration">
                  <span class="material-symbols-outlined">schedule</span>
                  <span>{{ formatDuration(scenario.modes?.quick?.duration) }}</span>
                </div>
              </div>
              <div class="mode-check">
                <span v-if="config.mode === 'quick'" class="material-symbols-outlined">check_circle</span>
              </div>
            </div>

            <!-- Standard Mode -->
            <div
              :class="[
                'mode-card',
                { 'selected': config.mode === 'standard' }
              ]"
              @click="config.mode = 'standard'"
            >
              <div class="mode-icon">
                <span class="material-symbols-outlined">analytics</span>
              </div>
              <div class="mode-content">
                <h4 class="mode-title">{{ t('analysisWizard.standardMode') }}</h4>
                <p class="mode-description">{{ t('analysisWizard.standardModeDesc') }}</p>
                <div class="mode-duration">
                  <span class="material-symbols-outlined">schedule</span>
                  <span>{{ formatDuration(scenario.modes?.standard?.duration) }}</span>
                </div>
              </div>
              <div class="mode-check">
                <span v-if="config.mode === 'standard'" class="material-symbols-outlined">check_circle</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Analysis Focus Areas -->
        <div class="mb-6" v-if="scenario.focus">
          <label class="form-label">{{ t('analysisWizard.analysisFocus') }}</label>
          <p class="form-hint mb-4">{{ t('analysisWizard.analysisFocusHint') }}</p>
          <div class="focus-tags flex flex-wrap gap-3">
            <div
              v-for="(focus, index) in getFocusAreas()"
              :key="index"
              :class="[
                'focus-tag',
                { 'selected': config.focusAreas.includes(focus) }
              ]"
              @click="toggleFocus(focus)"
            >
              <span>{{ focus }}</span>
              <span v-if="config.focusAreas.includes(focus)" class="material-symbols-outlined">check</span>
            </div>
          </div>
        </div>

        <!-- Report Language -->
        <div class="mb-6">
          <label class="form-label">{{ t('analysisWizard.reportLanguage') }}</label>
          <select v-model="config.language" class="form-input glass-input">
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </div>

        <!-- Additional Options -->
        <div>
          <label class="form-label">{{ t('analysisWizard.additionalOptions') }}</label>
          <div class="space-y-3 mt-3">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="config.includeComparison"
                class="checkbox-input"
              />
              <span class="checkbox-box"></span>
              <span class="checkbox-text">{{ t('analysisWizard.includeComparison') }}</span>
            </label>

            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="config.includeRisks"
                class="checkbox-input"
              />
              <span class="checkbox-box"></span>
              <span class="checkbox-text">{{ t('analysisWizard.includeRisks') }}</span>
            </label>

            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="config.detailedFinancials"
                class="checkbox-input"
              />
              <span class="checkbox-box"></span>
              <span class="checkbox-text">{{ t('analysisWizard.detailedFinancials') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-4">
        <button
          type="submit"
          class="btn btn-primary flex-1"
          :disabled="isSubmitting"
        >
          <span v-if="!isSubmitting">{{ t('analysisWizard.startAnalysis') }}</span>
          <span v-else class="flex items-center gap-2">
            <span class="animate-spin material-symbols-outlined">progress_activity</span>
            <span>{{ t('common.starting') }}</span>
          </span>
          <span v-if="!isSubmitting" class="material-symbols-outlined">play_arrow</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useLanguage } from '@/composables/useLanguage';
import DynamicFormField from '@/components/common/DynamicFormField.vue';
import { getScenarioFormFields } from '@/config/scenarios.js';

const { t, locale } = useLanguage();

const props = defineProps({
  scenario: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['analysis-start', 'back']);

// Form state
const formData = ref({});
const fieldRefs = ref({});
const config = ref({
  mode: 'quick',
  focusAreas: [],
  language: locale.value,
  includeComparison: false,
  includeRisks: true,
  detailedFinancials: false
});
const isSubmitting = ref(false);

// Get form fields from scenario configuration
const formFields = computed(() => {
  return getScenarioFormFields(props.scenario.id, locale.value);
});

// Initialize form data
onMounted(() => {
  formFields.value.forEach(field => {
    formData.value[field.name] = field.type === 'number' ? 0 : '';
  });
});

// Helper functions
function getScenarioName(scenario) {
  if (typeof scenario.name === 'string') return scenario.name;
  return scenario.name[locale.value] || scenario.name.zh || scenario.name.en || '';
}

function getScenarioDescription(scenario) {
  if (typeof scenario.description === 'string') return scenario.description;
  return scenario.description[locale.value] || scenario.description.zh || scenario.description.en || '';
}

function getFocusAreas() {
  if (!props.scenario.focus) return [];
  const focusArray = props.scenario.focus[locale.value] || props.scenario.focus.zh || props.scenario.focus.en || [];
  return Array.isArray(focusArray) ? focusArray : [];
}

function toggleFocus(focus) {
  const index = config.value.focusAreas.indexOf(focus);
  if (index > -1) {
    config.value.focusAreas.splice(index, 1);
  } else {
    config.value.focusAreas.push(focus);
  }
}

function formatDuration(seconds) {
  if (!seconds) return '';
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (secs === 0) {
    return `${minutes}${t('common.min')}`;
  }
  return `${minutes}${t('common.min')} ${secs}${t('common.sec')}`;
}

function goBack() {
  emit('back');
}

async function handleSubmit() {
  // Validate all fields
  let isValid = true;
  for (const fieldName in fieldRefs.value) {
    const fieldRef = fieldRefs.value[fieldName];
    if (fieldRef && fieldRef.validate) {
      if (!fieldRef.validate()) {
        isValid = false;
      }
    }
  }

  if (!isValid) {
    return;
  }

  isSubmitting.value = true;

  try {
    // Filter out empty optional fields and handle File objects
    const targetData = {};
    for (const key in formData.value) {
      const value = formData.value[key];
      if (value !== '' && value !== null && value !== undefined && value !== 0) {
        // Check if value is a File object
        if (value instanceof File) {
          // Convert File to base64
          const base64 = await fileToBase64(value);
          targetData[`${key}_base64`] = base64;
          targetData[`${key}name`] = value.name;
          console.log(`[UnifiedForm] Converted file ${value.name} to base64 (${base64.length} chars)`);
        } else {
          targetData[key] = value;
        }
      }
    }

    emit('analysis-start', {
      target: targetData,
      config: config.value
    });
  } catch (error) {
    console.error('[UnifiedForm] Error preparing form data:', error);
  } finally {
    isSubmitting.value = false;
  }
}

// Helper function to convert File to base64
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // Remove data URL prefix (e.g., "data:application/pdf;base64,")
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
</script>

<style scoped>
.unified-analysis-form {
  /* padding: 2rem 1rem; Removed to avoid double padding with parent */
}

/* Glass Card */
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1.5rem;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.glass-card:hover {
  border-color: rgba(56, 189, 248, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

/* Form Elements */
.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(203 213 225);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-label.required::after {
  content: ' *';
  color: rgb(239 68 68);
}

.form-hint {
  font-size: 0.875rem;
  color: rgb(148 163 184);
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.75rem;
  transition: all 0.3s ease;
  outline: none;
}

.glass-input {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.form-input:hover {
  border-color: rgba(56, 189, 248, 0.3);
  background: rgba(255, 255, 255, 0.08);
}

.form-input:focus {
  border-color: rgb(56, 189, 248);
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1);
}

select.form-input {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23a0aec0' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}

/* Mode Selector */
.mode-selector {
  gap: 1rem;
}

.mode-card {
  position: relative;
  padding: 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.mode-card:hover {
  border-color: rgba(56, 189, 248, 0.3);
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.mode-card.selected {
  border-color: rgb(56, 189, 248);
  background: rgba(56, 189, 248, 0.1);
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
}

.mode-icon {
  font-size: 2rem;
  color: rgb(56, 189, 248);
}

.mode-content {
  flex: 1;
}

.mode-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.5rem;
}

.mode-description {
  font-size: 0.875rem;
  color: rgb(148 163 184);
  margin-bottom: 0.75rem;
}

.mode-duration {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: rgb(56, 189, 248);
}

.mode-check {
  color: rgb(56, 189, 248);
  font-size: 1.5rem;
}

/* Focus Tags */
.focus-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.focus-tag {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 2rem;
  font-size: 0.875rem;
  color: rgb(203 213 225);
  cursor: pointer;
  transition: all 0.3s ease;
}

.focus-tag:hover {
  border-color: rgba(56, 189, 248, 0.3);
  background: rgba(255, 255, 255, 0.08);
}

.focus-tag.selected {
  border-color: rgb(56, 189, 248);
  background: rgba(56, 189, 248, 0.1);
  color: rgb(56, 189, 248);
}

.focus-tag .material-symbols-outlined {
  font-size: 1rem;
}

/* Checkboxes */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  padding: 0.75rem;
  border-radius: 0.5rem;
  transition: all 0.3s ease;
}

.checkbox-label:hover {
  background: rgba(255, 255, 255, 0.05);
}

.checkbox-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-box {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.25rem;
  transition: all 0.3s ease;
  position: relative;
  flex-shrink: 0;
}

.checkbox-input:checked + .checkbox-box {
  background: rgb(56, 189, 248);
  border-color: rgb(56, 189, 248);
}

.checkbox-input:checked + .checkbox-box::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 0.875rem;
  font-weight: 700;
}

.checkbox-text {
  font-size: 0.875rem;
  color: rgb(203 213 225);
}

/* Buttons */
.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 0.75rem;
  transition: all 0.3s ease;
  border: none;
  cursor: pointer;
  outline: none;
}

.btn-primary {
  background: linear-gradient(135deg, rgb(56, 189, 248), rgb(14, 165, 233));
  color: white;
  box-shadow: 0 4px 14px rgba(56, 189, 248, 0.4);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.6);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: rgb(203 213 225);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(56, 189, 248, 0.3);
  transform: translateY(-2px);
}

@media (max-width: 640px) {
  .mode-selector {
    grid-template-columns: 1fr;
  }
}
</style>
