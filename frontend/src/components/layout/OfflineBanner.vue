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
            <p class="font-semibold">{{ t('offline.bannerTitle') }}</p>
            <p class="text-sm opacity-90">{{ t('offline.bannerSubtitle') }}</p>
          </div>
        </div>
        <button
          @click="checkConnection"
          class="px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors font-semibold flex items-center gap-2"
        >
          <span class="material-symbols-outlined">refresh</span>
          {{ t('offline.retry') }}
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { useOnlineStatus } from '../../composables/useOnlineStatus';
import { useToast } from '../../composables/useToast';
import { useLanguage } from '../../composables/useLanguage';

const { isOnline } = useOnlineStatus();
const { success, error } = useToast();
const { t } = useLanguage();

const checkConnection = () => {
  if (navigator.onLine) {
    success(t('offline.restored'));
  } else {
    error(t('offline.stillDown'));
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
