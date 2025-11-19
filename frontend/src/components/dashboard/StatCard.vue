<template>
  <div class="glass-card p-6 relative overflow-hidden group rounded-xl">
    <!-- Background Glow Effect -->
    <div class="absolute -right-6 -top-6 w-24 h-24 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-colors duration-500"></div>
    
    <div class="relative z-10">
      <div class="flex items-start justify-between mb-4">
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg backdrop-blur-sm border border-white/10 transition-transform group-hover:scale-110 duration-300"
          :class="trendColor"
        >
          <span class="material-symbols-outlined text-2xl">{{ icon }}</span>
        </div>
        <span
          class="text-xs font-bold px-2.5 py-1 rounded-full border border-white/5 backdrop-blur-md"
          :class="changeClass"
        >
          {{ change }}
        </span>
      </div>
      <h3 class="text-text-secondary text-sm font-medium mb-1 tracking-wide uppercase">{{ title }}</h3>
      <p class="text-white text-3xl font-display font-bold tracking-tight group-hover:text-primary transition-colors">{{ value }}</p>
    </div>
    
    <!-- Bottom Highlight -->
    <div class="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
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
      return 'bg-emerald-500/10 text-emerald-400 shadow-emerald-500/10';
    case 'down':
      return 'bg-rose-500/10 text-rose-400 shadow-rose-500/10';
    default:
      return 'bg-primary/10 text-primary shadow-primary/10';
  }
});

const changeClass = computed(() => {
  switch (props.trend) {
    case 'up':
      return 'bg-emerald-500/10 text-emerald-400';
    case 'down':
      return 'bg-rose-500/10 text-rose-400';
    default:
      return 'bg-white/5 text-text-secondary';
  }
});
</script>
