<template>
  <div class="flex items-center justify-between p-4 rounded-lg bg-background-dark hover:bg-background-dark/80 border border-border-color transition-colors cursor-pointer">
    <div class="flex items-center gap-4 flex-1">
      <div
        class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
        :class="statusColor"
      >
        <span class="material-symbols-outlined">{{ statusIcon }}</span>
      </div>
      <div class="flex-1 min-w-0">
        <h4 class="text-sm font-semibold text-text-primary truncate">{{ title }}</h4>
        <div class="flex items-center gap-3 mt-1">
          <span class="text-xs text-text-secondary">{{ date }}</span>
          <span class="text-xs text-text-secondary">•</span>
          <span class="text-xs text-text-secondary">{{ agents }} agents</span>
        </div>
      </div>
    </div>
    <span
      class="text-xs font-semibold px-3 py-1 rounded-full flex-shrink-0"
      :class="statusBadgeClass"
    >
      {{ statusText }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  title: String,
  date: String,
  status: String,
  agents: Number
});

const statusIcon = computed(() => {
  return props.status === 'completed' ? 'check_circle' : 'pending';
});

const statusColor = computed(() => {
  return props.status === 'completed'
    ? 'bg-accent-green/20 text-accent-green'
    : 'bg-accent-yellow/20 text-accent-yellow';
});

const statusText = computed(() => {
  return props.status === 'completed' ? 'Completed' : 'In Progress';
});

const statusBadgeClass = computed(() => {
  return props.status === 'completed'
    ? 'bg-accent-green/20 text-accent-green'
    : 'bg-accent-yellow/20 text-accent-yellow';
});
</script>
