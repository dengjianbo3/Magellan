<template>
  <div class="connection-status" :class="`status-${connectionState}`">
    <!-- Status Icon -->
    <div class="status-icon">
      <span v-if="connectionState === 'disconnected'" class="material-symbols-outlined">cloud_off</span>
      <span v-else-if="connectionState === 'connecting'" class="material-symbols-outlined animate-pulse">sync</span>
      <span v-else-if="connectionState === 'connected'" class="material-symbols-outlined">cloud_done</span>
      <span v-else-if="connectionState === 'error'" class="material-symbols-outlined">error</span>
      <span v-else-if="connectionState === 'reconnecting'" class="material-symbols-outlined animate-spin">autorenew</span>
    </div>

    <!-- Status Text -->
    <div class="status-text">
      <span class="status-label">{{ statusText }}</span>
      <span v-if="reconnectAttempt > 0" class="reconnect-info">
        ({{ reconnectAttempt }}/{{ maxReconnectAttempts }})
      </span>
    </div>

    <!-- Reconnect Button (shown on error) -->
    <button
      v-if="connectionState === 'error' && showReconnectButton"
      @click="handleManualReconnect"
      class="reconnect-btn"
      :disabled="isReconnecting"
    >
      <span class="material-symbols-outlined">refresh</span>
      {{ t('connection.retry') || '重试' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import analysisServiceV2 from '@/services/analysisServiceV2.js';

const { t } = useLanguage();

// Props
const props = defineProps({
  showReconnectButton: {
    type: Boolean,
    default: true
  }
});

// State
const connectionState = ref('disconnected');
const reconnectAttempt = ref(0);
const maxReconnectAttempts = ref(10);
const isReconnecting = ref(false);

// Computed
const statusText = computed(() => {
  const statusMap = {
    'disconnected': t('connection.disconnected') || '未连接',
    'connecting': t('connection.connecting') || '连接中...',
    'connected': t('connection.connected') || '已连接',
    'error': t('connection.error') || '连接错误',
    'reconnecting': t('connection.reconnecting') || '重连中...'
  };
  return statusMap[connectionState.value] || connectionState.value;
});

// Methods
function handleStateChange(newState, oldState) {
  console.log(`[ConnectionStatus] State changed: ${oldState} → ${newState}`);
  connectionState.value = newState;

  // Update reconnect attempt (would need to be exposed from analysisServiceV2)
  if (newState === 'reconnecting') {
    // Note: This is a placeholder - you'd need to expose reconnectAttempts from analysisServiceV2
    // reconnectAttempt.value = analysisServiceV2.reconnectAttempts;
    isReconnecting.value = true;
  } else if (newState === 'connected') {
    reconnectAttempt.value = 0;
    isReconnecting.value = false;
  } else if (newState === 'error') {
    isReconnecting.value = false;
  }
}

function handleManualReconnect() {
  console.log('[ConnectionStatus] Manual reconnect triggered');
  isReconnecting.value = true;

  // TODO: Add manual reconnect method to analysisServiceV2
  // analysisServiceV2.manualReconnect();

  // For now, just update state
  setTimeout(() => {
    isReconnecting.value = false;
  }, 2000);
}

// Lifecycle
onMounted(() => {
  // Get current state
  connectionState.value = analysisServiceV2.getConnectionState();

  // Listen to state changes
  analysisServiceV2.onStateChange(handleStateChange);

  // Also expose reconnect attempt count if available
  maxReconnectAttempts.value = analysisServiceV2.maxReconnectAttempts || 10;
});

onUnmounted(() => {
  // Clean up listener
  analysisServiceV2.offStateChange(handleStateChange);
});
</script>

<style scoped>
.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

/* Status Colors */
.status-disconnected {
  background-color: rgba(156, 163, 175, 0.1);
  color: rgb(156, 163, 175);
}

.status-connecting {
  background-color: rgba(251, 191, 36, 0.1);
  color: rgb(251, 191, 36);
}

.status-connected {
  background-color: rgba(16, 185, 129, 0.1);
  color: rgb(16, 185, 129);
}

.status-error {
  background-color: rgba(239, 68, 68, 0.1);
  color: rgb(239, 68, 68);
}

.status-reconnecting {
  background-color: rgba(249, 115, 22, 0.1);
  color: rgb(249, 115, 22);
}

/* Icon */
.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.status-icon .material-symbols-outlined {
  font-size: inherit;
}

/* Animate spin for reconnecting */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Text */
.status-text {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 500;
}

.status-label {
  white-space: nowrap;
}

.reconnect-info {
  font-size: 0.75rem;
  opacity: 0.7;
}

/* Reconnect Button */
.reconnect-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid currentColor;
  border-radius: 0.375rem;
  color: inherit;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reconnect-btn:hover:not(:disabled) {
  background-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.reconnect-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reconnect-btn .material-symbols-outlined {
  font-size: 1rem;
}

/* Responsive */
@media (max-width: 640px) {
  .connection-status {
    font-size: 0.75rem;
    padding: 0.375rem 0.5rem;
  }

  .status-icon {
    font-size: 1rem;
  }

  .reconnect-info {
    display: none;
  }
}
</style>
