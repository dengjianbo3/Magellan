<template>
  <div class="bg-background-dark border border-border-color rounded-lg p-4 hover:border-primary/50 transition-colors">
    <div class="flex items-start justify-between mb-3">
      <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
        <span class="material-symbols-outlined text-primary">{{ icon }}</span>
      </div>
      <span
        class="w-2 h-2 rounded-full flex-shrink-0"
        :class="statusColor"
      ></span>
    </div>
    <h4 class="text-sm font-semibold text-text-primary mb-1">{{ name }}</h4>
    <p class="text-xs text-text-secondary">
      {{ tasks > 0 ? `${tasks} active tasks` : 'No active tasks' }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  name: String,
  status: String,
  tasks: Number,
  icon: String
});

const statusColor = computed(() => {
  return props.status === 'active' ? 'bg-accent-green' : 'bg-text-secondary';
});
</script>
