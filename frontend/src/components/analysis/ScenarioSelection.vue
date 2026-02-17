<template>
  <div class="w-full max-w-7xl mx-auto">
    <!-- Backend Unavailable Banner -->
    <div v-if="loadError" class="mb-8 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 backdrop-blur-sm">
      <div class="flex items-center gap-3">
        <span class="material-symbols-outlined text-rose-400 text-2xl">error</span>
        <div class="flex-1">
          <p class="text-rose-300 font-medium">{{ t('analysisWizard.backendUnavailable') || 'Backend service is unavailable. Please start backend services.' }}</p>
          <p class="text-rose-400/70 text-sm mt-1">{{ loadError }}</p>
        </div>
        <button
          class="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-bold transition-colors"
          @click="reloadScenarios"
        >
          {{ t('common.retry') || 'Retry' }}
        </button>
      </div>
    </div>

    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-display font-bold text-white mb-4 tracking-tight">{{ t('analysisWizard.selectScenario') }}</h1>
      <p class="text-text-secondary text-lg">{{ t('analysisWizard.selectScenarioHint') }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4"></div>
      <p class="text-text-secondary font-medium animate-pulse">{{ t('analysisWizard.loadingScenarios') }}</p>
    </div>

    <!-- Scenarios Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 mb-12">
      <div
        v-for="scenario in scenarios"
        :key="scenario.id"
        :class="[
          'relative p-8 rounded-2xl border transition-all duration-500 overflow-hidden group cursor-pointer h-full flex flex-col',
          selectedScenario === scenario.id
            ? 'bg-surface border-primary shadow-[0_0_30px_rgba(56,189,248,0.2)] scale-105 z-10'
            : 'bg-surface/40 border-white/5 hover:border-primary/30 hover:bg-surface/60 hover:-translate-y-2 hover:shadow-xl',
          scenario.status && scenario.status !== 'active' ? 'opacity-60 cursor-not-allowed grayscale hover:transform-none' : ''
        ]"
        @click="selectScenario(scenario)"
      >
        <!-- Background Glow -->
        <div 
          class="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-primary/10 to-transparent blur-3xl rounded-full -mr-16 -mt-16 transition-opacity duration-500"
          :class="selectedScenario === scenario.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-50'"
        ></div>

        <!-- Icon -->
        <div class="relative z-10 mb-6 text-center">
          <div class="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-white/5 border border-white/10 group-hover:scale-110 transition-transform duration-500 backdrop-blur-sm">
             <span class="text-5xl filter drop-shadow-lg">{{ scenario.icon }}</span>
          </div>
        </div>

        <!-- Title and Description -->
        <div class="relative z-10 text-center mb-8">
          <h3 class="text-xl font-bold text-white mb-3 group-hover:text-primary transition-colors">{{ scenario.name }}</h3>
          <p class="text-text-secondary text-sm leading-relaxed h-10 line-clamp-2">{{ scenario.description }}</p>
        </div>

        <!-- Duration Info -->
        <div class="relative z-10 border-t border-white/10 pt-6 space-y-3">
          <div class="flex justify-between items-center text-sm">
            <span class="text-text-secondary">{{ t('analysisWizard.quickJudgment') }}:</span>
            <span class="text-white font-mono font-bold">{{ scenario.quick_mode_duration }}</span>
          </div>
          <div class="flex justify-between items-center text-sm">
            <span class="text-text-secondary">{{ t('analysisWizard.standardAnalysis') }}:</span>
            <span class="text-white font-mono font-bold">{{ scenario.standard_mode_duration || t('analysisWizard.na') }}</span>
          </div>
        </div>

        <!-- Selected Indicator -->
        <div v-if="selectedScenario === scenario.id" class="absolute top-4 right-4 text-primary animate-fade-in">
          <span class="material-symbols-outlined text-3xl drop-shadow-[0_0_10px_rgba(56,189,248,0.8)]">check_circle</span>
        </div>

        <!-- Coming Soon Badge -->
        <div
          v-if="scenario.status && scenario.status !== 'active'"
          class="absolute top-4 left-4 px-3 py-1 rounded-full text-xs font-bold tracking-wide bg-amber-500/20 text-amber-300 border border-amber-500/30"
        >
          {{ t('analysisWizard.comingSoon') || '即将推出' }}
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex justify-end border-t border-white/10 pt-8">
      <button
        class="flex items-center gap-3 px-8 py-3.5 rounded-xl font-bold text-white transition-all duration-300 shadow-lg"
        :class="[
          selectedScenario
            ? 'bg-gradient-to-r from-primary to-primary-dark hover:shadow-glow hover:-translate-y-1 hover:scale-105 cursor-pointer'
            : 'bg-surface-light text-text-secondary cursor-not-allowed opacity-50'
        ]"
        :disabled="!selectedScenario"
        @click="handleNext"
      >
        <span>{{ t('analysisWizard.nextStep') }}</span>
        <span class="material-symbols-outlined group-hover:translate-x-1 transition-transform">arrow_forward</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import analysisServiceV2 from '@/services/analysisServiceV2.js';

const { t } = useLanguage();

const emit = defineEmits(['scenario-selected']);

const loading = ref(true);
const rawScenarios = ref([]);
const selectedScenario = ref(null);
const loadError = ref('');

// Icon mapping: backend icon names to emojis
const iconMap = {
  'rocket': '🚀',
  'chart': '📈',
  'building': '🏛️',
  'bitcoin': '💎',
  'search': '🔍'
};

const scenarios = computed(() => {
  // Map raw IDs to translated content and fix icons
  return rawScenarios.value.map(s => {
    let translationKey = '';
    if (s.id === 'early-stage-investment') translationKey = 'earlyStage';
    else if (s.id === 'growth-investment') translationKey = 'growth';
    else if (s.id === 'public-market-investment') translationKey = 'publicMarket';
    else if (s.id === 'industry-research') translationKey = 'industryResearch';
    else if (s.id === 'alternative-investment') translationKey = 'alternative';

    // Map backend icon name to emoji
    const icon = iconMap[s.icon] || s.icon;

    if (translationKey) {
      return {
        ...s,
        icon,
        name: t(`scenarios.${translationKey}.name`) || s.name,
        description: t(`scenarios.${translationKey}.description`) || s.description
      };
    }
    return { ...s, icon };
  });
});

onMounted(async () => {
  await reloadScenarios();
});

function selectScenario(scenario) {
  if (scenario.status && scenario.status !== 'active') {
    return; // 暂不支持的场景,不能选择
  }
  selectedScenario.value = scenario.id;
}

function handleNext() {
  if (selectedScenario.value) {
    const scenario = rawScenarios.value.find(s => s.id === selectedScenario.value);
    emit('scenario-selected', scenario);
  }
}

async function reloadScenarios() {
  loading.value = true;
  loadError.value = '';
  try {
    rawScenarios.value = await analysisServiceV2.getScenarios();
  } catch (e) {
    rawScenarios.value = [];
    loadError.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}
</script>
