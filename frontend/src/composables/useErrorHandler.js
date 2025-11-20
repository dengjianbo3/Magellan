/**
 * 错误处理框架
 * 提供统一的错误处理和Toast通知功能
 */

import { ref } from 'vue';

// 全局错误状态 - 所有组件共享
const errors = ref([]);
let nextId = 1;

export function useErrorHandler() {
  /**
   * 处理错误并显示Toast通知
   * @param {Object} error - 错误对象
   * @param {string} error.message - 技术错误消息
   * @param {string} error.userMessage - 用户友好的错误消息
   * @param {string} error.type - 错误类型: 'error' | 'warning' | 'info' | 'success'
   * @param {boolean} error.recoverable - 是否可恢复
   * @param {string} context - 错误发生的上下文(组件.方法)
   * @returns {Object} 错误对象
   */
  const handleError = (error, context = '') => {
    console.error(`[${context}] Error:`, error);

    const errorObj = {
      id: nextId++,
      type: error.type || 'error',
      message: error.userMessage || error.message || '发生了一个错误',
      technical: error.message,
      context,
      timestamp: new Date(),
      recoverable: error.recoverable !== false,
      action: error.action || null,  // 可选的操作按钮
      duration: error.duration || 5000  // 默认5秒后自动消失
    };

    errors.value.push(errorObj);

    // 自动移除
    if (errorObj.duration > 0) {
      setTimeout(() => {
        clearError(errorObj.id);
      }, errorObj.duration);
    }

    return errorObj;
  };

  /**
   * 清除特定错误
   * @param {number} id - 错误ID
   */
  const clearError = (id) => {
    errors.value = errors.value.filter(e => e.id !== id);
  };

  /**
   * 清除所有错误
   */
  const clearAllErrors = () => {
    errors.value = [];
  };

  /**
   * 显示成功消息
   * @param {string} message - 成功消息
   * @param {number} duration - 显示时长(ms)
   */
  const showSuccess = (message, duration = 3000) => {
    return handleError({
      type: 'success',
      userMessage: message,
      duration
    });
  };

  /**
   * 显示警告消息
   * @param {string} message - 警告消息
   * @param {number} duration - 显示时长(ms)
   */
  const showWarning = (message, duration = 5000) => {
    return handleError({
      type: 'warning',
      userMessage: message,
      duration
    });
  };

  /**
   * 显示信息消息
   * @param {string} message - 信息消息
   * @param {number} duration - 显示时长(ms)
   */
  const showInfo = (message, duration = 4000) => {
    return handleError({
      type: 'info',
      userMessage: message,
      duration
    });
  };

  return {
    errors,
    handleError,
    clearError,
    clearAllErrors,
    showSuccess,
    showWarning,
    showInfo
  };
}
