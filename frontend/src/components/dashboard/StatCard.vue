<template>
  <div class="bg-surface border border-border-color rounded-lg p-6 hover:border-primary/50 transition-colors">
    <div class="flex items-start justify-between mb-4">
      <div
        class="w-12 h-12 rounded-lg flex items-center justify-center"
        :class="trendColor"
      >
        <span class="material-symbols-outlined text-2xl">{{ icon }}</span>
      </div>
      <span
        class="text-xs font-semibold px-2 py-1 rounded-full"
        :class="changeClass"
      >
        {{ change }}
      </span>
    </div>
    <h3 class="text-text-secondary text-sm font-medium mb-1">{{ title }}</h3>
    <p class="text-text-primary text-3xl font-bold">{{ value }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  title: String,
  value: String,
  change: String,
  icon: String,
  trend: {
    type: String,
    default: 'neutral'
  }
});

const trendColor = computed(() => {
  switch (props.trend) {
    case 'up':
      return 'bg-accent-green/20 text-accent-green';
    case 'down':
      return 'bg-accent-red/20 text-accent-red';
    default:
      return 'bg-primary/20 text-primary';
  }
});

const changeClass = computed(() => {
  switch (props.trend) {
    case 'up':
      return 'bg-accent-green/20 text-accent-green';
    case 'down':
      return 'bg-accent-red/20 text-accent-red';
    default:
      return 'bg-surface-light text-text-secondary';
  }
});
</script>
