<template>
  <Transition name="slide-down">
    <div
      v-if="!isOnline"
      class="fixed top-0 left-0 right-0 z-50 bg-accent-red text-white py-3 px-6 shadow-lg"
    >
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined animate-pulse">cloud_off</span>
          <div>
            <p class="font-semibold">您当前处于离线状态</p>
            <p class="text-sm opacity-90">部分功能可能无法使用，请检查网络连接</p>
          </div>
        </div>
        <button
          @click="checkConnection"
          class="px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors font-semibold flex items-center gap-2"
        >
          <span class="material-symbols-outlined">refresh</span>
          重试连接
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { useOnlineStatus } from '../../composables/useOnlineStatus';
import { useToast } from '../../composables/useToast';

const { isOnline } = useOnlineStatus();
const { success, error } = useToast();

const checkConnection = () => {
  if (navigator.onLine) {
    success('网络连接已恢复');
  } else {
    error('网络仍然不可用');
  }
};
</script>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
