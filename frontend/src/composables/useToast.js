/**
 * Toast Notification Composable
 * 提供全局Toast通知功能
 */

import { ref } from 'vue';

const toasts = ref([]);
let toastId = 0;

export function useToast() {
  const addToast = (message, type = 'info', duration = 3000) => {
    const id = toastId++;
    const toast = {
      id,
      message,
      type, // 'success', 'error', 'warning', 'info'
      duration,
      visible: true
    };

    toasts.value.push(toast);

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  };

  const removeToast = (id) => {
    const index = toasts.value.findIndex(t => t.id === id);
    if (index > -1) {
      toasts.value[index].visible = false;
      // Remove from array after animation
      setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id);
      }, 300);
    }
  };

  const success = (message, duration = 3000) => {
    return addToast(message, 'success', duration);
  };

  const error = (message, duration = 5000) => {
    return addToast(message, 'error', duration);
  };

  const warning = (message, duration = 4000) => {
    return addToast(message, 'warning', duration);
  };

  const info = (message, duration = 3000) => {
    return addToast(message, 'info', duration);
  };

  const clear = () => {
    toasts.value = [];
  };

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
    clear
  };
}
