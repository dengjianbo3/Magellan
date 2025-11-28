<template>
  <div class="fixed top-4 right-4 z-50 space-y-3 pointer-events-none">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'pointer-events-auto max-w-sm rounded-lg shadow-lg border p-4 flex items-start gap-3 transition-all duration-300',
          toast.visible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-full',
          toast.type === 'success' ? 'bg-accent-green/20 border-accent-green text-accent-green' :
          toast.type === 'error' ? 'bg-accent-red/20 border-accent-red text-accent-red' :
          toast.type === 'warning' ? 'bg-accent-yellow/20 border-accent-yellow text-accent-yellow' :
          'bg-primary/20 border-primary text-primary'
        ]"
      >
        <!-- Icon -->
        <span class="material-symbols-outlined flex-shrink-0">
          {{
            toast.type === 'success' ? 'check_circle' :
            toast.type === 'error' ? 'error' :
            toast.type === 'warning' ? 'warning' :
            'info'
          }}
        </span>

        <!-- Message -->
        <div class="flex-1 text-sm font-semibold text-text-primary">
          {{ toast.message }}
        </div>

        <!-- Close Button -->
        <button
          @click="removeToast(toast.id)"
          class="flex-shrink-0 text-text-secondary hover:text-text-primary transition-colors"
        >
          <span class="material-symbols-outlined text-lg">close</span>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToast } from '../../composables/useToast';

const { toasts, removeToast } = useToast();
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
