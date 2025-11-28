<template>
  <div class="form-field" :class="{ 'has-error': error }">
    <!-- Label -->
    <label v-if="field.label" class="form-label" :class="{ 'required': field.required }">
      {{ getLabel(field.label) }}
    </label>

    <!-- Text Input -->
    <input
      v-if="field.type === 'text'"
      v-model="localValue"
      type="text"
      class="form-input glass-input"
      :placeholder="getPlaceholder(field.placeholder)"
      :required="field.required"
      @blur="validate"
    />

    <!-- Number Input -->
    <input
      v-else-if="field.type === 'number'"
      v-model.number="localValue"
      type="number"
      class="form-input glass-input"
      :placeholder="getPlaceholder(field.placeholder)"
      :required="field.required"
      :min="field.validation?.min"
      :max="field.validation?.max"
      @blur="validate"
    />

    <!-- Select Dropdown -->
    <select
      v-else-if="field.type === 'select'"
      v-model="localValue"
      class="form-input glass-input"
      :required="field.required"
      @change="validate"
    >
      <option value="" disabled>{{ getPlaceholder(field.placeholder) || t('common.pleaseSelect') }}</option>
      <option
        v-for="option in field.options"
        :key="option.value"
        :value="option.value"
      >
        {{ getLabel(option.label) }}
      </option>
    </select>

    <!-- Button Group (for stage selection, etc.) -->
    <div
      v-else-if="field.type === 'button-group'"
      class="button-group"
    >
      <button
        v-for="option in field.options"
        :key="option.value"
        type="button"
        :class="[
          'option-button',
          { 'selected': localValue === option.value }
        ]"
        @click="selectOption(option.value)"
      >
        <span v-if="option.icon" class="option-icon">{{ option.icon }}</span>
        <span class="option-label">{{ getLabel(option.label) }}</span>
      </button>
    </div>

    <!-- File Upload -->
    <div v-else-if="field.type === 'file'" class="file-upload-area">
      <input
        :id="`file-${field.name}`"
        type="file"
        class="hidden-file-input"
        :accept="field.accept"
        :required="field.required"
        @change="handleFileChange"
      />
      <label
        :for="`file-${field.name}`"
        class="file-upload-label glass-input"
      >
        <span class="material-symbols-outlined text-primary">upload_file</span>
        <span class="file-upload-text">
          {{ uploadedFileName || getPlaceholder(field.placeholder) || t('common.clickToUpload') }}
        </span>
      </label>
      <p v-if="uploadedFileName" class="file-info">
        {{ formatFileSize(uploadedFileSize) }}
      </p>
    </div>

    <!-- Textarea -->
    <textarea
      v-else-if="field.type === 'textarea'"
      v-model="localValue"
      class="form-input glass-input"
      :placeholder="getPlaceholder(field.placeholder)"
      :required="field.required"
      :rows="field.rows || 4"
      @blur="validate"
    ></textarea>

    <!-- Hint Text -->
    <p v-if="field.hint && !error" class="form-hint">
      {{ getLabel(field.hint) }}
    </p>

    <!-- Error Message -->
    <p v-if="error" class="form-error">
      {{ error }}
    </p>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage';

const { t, locale } = useLanguage();

const props = defineProps({
  field: {
    type: Object,
    required: true
  },
  modelValue: {
    type: [String, Number, Object, Array],
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'validate']);

// Local value for two-way binding
const localValue = ref(props.modelValue);

// File upload state
const uploadedFileName = ref('');
const uploadedFileSize = ref(0);

// Validation error
const error = ref('');

// Watch for prop changes
watch(() => props.modelValue, (newValue) => {
  localValue.value = newValue;
});

// Watch for local changes
watch(localValue, (newValue) => {
  emit('update:modelValue', newValue);
  validate();
});

// Helper functions
function getLabel(label) {
  if (typeof label === 'string') return label;
  if (typeof label === 'object') return label[locale.value] || label['zh'] || label['en'] || '';
  return '';
}

function getPlaceholder(placeholder) {
  if (!placeholder) return '';
  if (typeof placeholder === 'string') return placeholder;
  if (typeof placeholder === 'object') return placeholder[locale.value] || placeholder['zh'] || placeholder['en'] || '';
  return '';
}

function selectOption(value) {
  localValue.value = value;
  validate();
}

function handleFileChange(event) {
  const file = event.target.files[0];
  if (file) {
    uploadedFileName.value = file.name;
    uploadedFileSize.value = file.size;
    localValue.value = file;
    validate();
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function validate() {
  error.value = '';

  // Required validation
  if (props.field.required && !localValue.value) {
    error.value = t('validation.required');
    emit('validate', false);
    return false;
  }

  // Min length validation
  if (props.field.validation?.minLength && localValue.value.length < props.field.validation.minLength) {
    error.value = t('validation.minLength').replace('{n}', props.field.validation.minLength);
    emit('validate', false);
    return false;
  }

  // Max length validation
  if (props.field.validation?.maxLength && localValue.value.length > props.field.validation.maxLength) {
    error.value = t('validation.maxLength').replace('{n}', props.field.validation.maxLength);
    emit('validate', false);
    return false;
  }

  // Min/Max number validation
  if (props.field.type === 'number') {
    if (props.field.validation?.min !== undefined && localValue.value < props.field.validation.min) {
      error.value = t('validation.min').replace('{n}', props.field.validation.min);
      emit('validate', false);
      return false;
    }
    if (props.field.validation?.max !== undefined && localValue.value > props.field.validation.max) {
      error.value = t('validation.max').replace('{n}', props.field.validation.max);
      emit('validate', false);
      return false;
    }
  }

  // Pattern validation
  if (props.field.validation?.pattern && localValue.value) {
    const regex = new RegExp(props.field.validation.pattern);
    if (!regex.test(localValue.value)) {
      error.value = t('validation.pattern');
      emit('validate', false);
      return false;
    }
  }

  emit('validate', true);
  return true;
}

// Expose validate method
defineExpose({ validate });
</script>

<style scoped>
.form-field {
  margin-bottom: 1.5rem;
}

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

.form-input::placeholder {
  color: rgb(148 163 184);
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

.button-group {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.option-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.75rem;
  color: rgb(203 213 225);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.option-button:hover {
  border-color: rgba(56, 189, 248, 0.5);
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.option-button.selected {
  border-color: rgb(56, 189, 248);
  background: rgba(56, 189, 248, 0.1);
  color: rgb(56, 189, 248);
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
}

.option-icon {
  font-size: 2rem;
}

.option-label {
  font-size: 0.875rem;
}

.file-upload-area {
  position: relative;
}

.hidden-file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}

.file-upload-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.file-upload-label:hover {
  border-color: rgba(56, 189, 248, 0.5);
  transform: translateY(-2px);
}

.file-upload-text {
  flex: 1;
  color: rgb(148 163 184);
}

.file-info {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: rgb(148 163 184);
}

.form-hint {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: rgb(148 163 184);
}

.form-error {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: rgb(239 68 68);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.form-error::before {
  content: '⚠️';
}

.form-field.has-error .form-input {
  border-color: rgb(239 68 68);
}

textarea.form-input {
  resize: vertical;
  min-height: 100px;
  line-height: 1.5;
}
</style>
