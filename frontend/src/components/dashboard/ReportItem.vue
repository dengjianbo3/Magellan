<template>
  <div class="flex items-center justify-between p-4 rounded-lg hover:bg-white/5 transition-colors cursor-pointer border border-transparent hover:border-white/5 group">
    <div class="flex items-center gap-4 flex-1">
      <div
        class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 backdrop-blur-sm transition-colors"
        :class="statusIconContainer"
      >
        <span class="material-symbols-outlined transition-colors" :class="statusIconColor">{{ statusIcon }}</span>
      </div>
      <div class="flex-1 min-w-0">
        <h4 class="text-sm font-bold text-text-primary truncate group-hover:text-white transition-colors">{{ title }}</h4>
        <div class="flex items-center gap-3 mt-1">
          <span class="text-xs text-text-secondary font-medium">{{ date }}</span>
          <span class="text-xs text-white/20">•</span>
          <span class="text-xs text-text-secondary flex items-center gap-1">
            <span class="material-symbols-outlined text-[10px]">smart_toy</span>
            {{ agents }} agents
          </span>
        </div>
      </div>
    </div>
    <span
      class="text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full flex-shrink-0 border"
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

const statusIconContainer = computed(() => {
  return props.status === 'completed'
    ? 'bg-emerald-500/10 border border-emerald-500/20 group-hover:bg-emerald-500/20'
    : 'bg-amber-500/10 border border-amber-500/20 group-hover:bg-amber-500/20';
});

const statusIconColor = computed(() => {
  return props.status === 'completed' ? 'text-emerald-400' : 'text-amber-400';
});

const statusText = computed(() => {
  return props.status === 'completed' ? 'Completed' : 'Processing';
});

const statusBadgeClass = computed(() => {
  return props.status === 'completed'
    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]'
    : 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-[0_0_10px_rgba(245,158,11,0.1)]';
});
</script>
