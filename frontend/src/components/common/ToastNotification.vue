<template>
  <teleport to="body">
    <div class="toast-container">
      <transition-group name="toast" tag="div">
        <div
          v-for="error in errors"
          :key="error.id"
          class="toast"
          :class="`toast-${error.type}`"
          @click="clearError(error.id)"
        >
          <div class="toast-icon">
            <span class="material-symbols-outlined">{{ getIcon(error.type) }}</span>
          </div>
          <div class="toast-content">
            <p class="toast-message">{{ error.message }}</p>
            <p v-if="error.context && showTechnical" class="toast-context">
              {{ error.context }}
            </p>
          </div>
          <button @click.stop="clearError(error.id)" class="toast-close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import { computed } from 'vue';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  showTechnical: {
    type: Boolean,
    default: false
  }
});

const { errors, clearError } = useErrorHandler();

function getIcon(type) {
  const icons = {
    error: 'error',
    warning: 'warning',
    info: 'info',
    success: 'check_circle'
  };
  return icons[type] || 'info';
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 12px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 320px;
  max-width: 480px;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  pointer-events: auto;
  cursor: pointer;
  transition: all 0.3s ease;
}

.toast:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  transform: translateY(-2px);
}

.toast-error {
  background: #fef2f2;
  border-left: 4px solid #ef4444;
  color: #991b1b;
}

.toast-warning {
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  color: #92400e;
}

.toast-info {
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  color: #1e40af;
}

.toast-success {
  background: #f0fdf4;
  border-left: 4px solid #10b981;
  color: #065f46;
}

.toast-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.toast-icon .material-symbols-outlined {
  font-size: 24px;
}

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-message {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.5;
  word-wrap: break-word;
}

.toast-context {
  margin: 4px 0 0 0;
  font-size: 12px;
  opacity: 0.7;
  font-family: monospace;
}

.toast-close {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.toast-close:hover {
  opacity: 1;
}

.toast-close .material-symbols-outlined {
  font-size: 18px;
}

/* Vue Transition */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.toast-move {
  transition: transform 0.3s ease;
}

/* 响应式 */
@media (max-width: 768px) {
  .toast-container {
    left: 12px;
    right: 12px;
    top: 12px;
  }

  .toast {
    min-width: auto;
    max-width: none;
  }
}
</style>
