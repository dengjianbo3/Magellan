<template>
  <div class="glass-card rounded-xl p-5 group cursor-pointer relative overflow-hidden">
    <div class="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
    
    <div class="relative z-10">
      <div class="flex items-start justify-between mb-4">
        <div class="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:border-primary/50 group-hover:bg-primary/10 transition-all duration-300">
          <span class="material-symbols-outlined text-text-secondary group-hover:text-primary transition-colors">{{ icon }}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[10px] uppercase tracking-wider font-bold text-text-secondary">{{ status }}</span>
          <span
            class="w-2 h-2 rounded-full flex-shrink-0 transition-all duration-300"
            :class="statusColor"
          ></span>
        </div>
      </div>
      
      <h4 class="text-base font-bold text-text-primary mb-1 group-hover:text-white transition-colors">{{ name }}</h4>
      <p class="text-xs text-text-secondary font-medium">
        {{ tasks > 0 ? `${tasks} ACTIVE TASKS` : 'IDLE' }}
      </p>

      <!-- Progress Bar for visual flair -->
      <div class="w-full h-1 bg-white/5 rounded-full mt-4 overflow-hidden">
        <div 
          class="h-full bg-primary/50 rounded-full transition-all duration-1000 group-hover:bg-primary"
          :style="{ width: tasks > 0 ? '60%' : '0%' }"
        ></div>
      </div>
    </div>
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
  return props.status === 'active' || props.tasks > 0
    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' 
    : 'bg-slate-600';
});
</script>
