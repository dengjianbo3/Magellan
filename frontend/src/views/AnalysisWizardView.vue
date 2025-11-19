<template>
  <div class="max-w-7xl mx-auto p-8 min-h-screen flex flex-col">
    <!-- Back Button -->
    <button 
      v-if="currentStep > 0"
      @click="currentStep--"
      class="self-start mb-6 flex items-center gap-2 text-text-secondary hover:text-primary transition-colors"
    >
      <span class="material-symbols-outlined">arrow_back</span>
      {{ t('common.back') || 'Back' }}
    </button>

    <!-- Wizard Steps Indicator -->
    <div class="glass-panel rounded-2xl p-8 mb-8 relative overflow-hidden">
      <div class="relative z-10 flex justify-between items-start">
        <!-- Progress Line Container (Constrained to centers of first/last circles) -->
        <div class="absolute top-6 -translate-y-1/2 left-6 right-6 h-1 -z-10">
          <!-- Background Line -->
          <div class="absolute inset-0 bg-white/10 rounded-full"></div>
          
          <!-- Active Progress Line -->
          <div 
            class="absolute left-0 top-0 h-full bg-gradient-to-r from-primary to-accent-cyan rounded-full transition-all duration-500"
            :style="{ width: `${(currentStep / (steps.length - 1)) * 100}%` }"
          ></div>
        </div>

        <div
          v-for="(step, index) in steps"
          :key="index"
          :class="['relative flex flex-col items-center w-12 group cursor-default']"
        >
          <!-- Step Circle -->
          <div 
            class="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold border-2 transition-all duration-300 bg-background-dark relative z-20"
            :class="[
              currentStep === index 
                ? 'border-primary text-white shadow-[0_0_15px_rgba(56,189,248,0.5)] scale-110' 
                : currentStep > index 
                  ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10 border-transparent' 
                  : 'border-white/10 text-text-secondary bg-surface'
            ]"
          >
            <span v-if="currentStep > index" class="material-symbols-outlined text-xl">check</span>
            <span v-else>{{ index + 1 }}</span>
            
            <!-- Ripple Effect for Active -->
            <div v-if="currentStep === index" class="absolute inset-0 rounded-full border-2 border-primary opacity-0 animate-ping"></div>
          </div>

          <!-- Step Label -->
          <div 
            class="absolute top-14 w-48 text-center text-sm font-medium tracking-wide transition-colors duration-300 left-1/2 -translate-x-1/2"
            :class="[
              currentStep === index ? 'text-primary font-bold' : 
              currentStep > index ? 'text-emerald-400' : 'text-text-secondary'
            ]"
          >
            {{ step.label }}
          </div>
        </div>
      </div>
      <!-- Spacer for absolute labels -->
      <div class="h-8"></div>
    </div>

    <!-- Wizard Content Area -->
    <div class="glass-panel rounded-2xl p-8 flex-grow relative overflow-hidden min-h-[600px]">
      <!-- Background Decorative Elements -->
      <div class="absolute top-0 right-0 w-96 h-96 bg-primary/5 blur-[100px] rounded-full pointer-events-none"></div>
      <div class="absolute bottom-0 left-0 w-96 h-96 bg-accent-violet/5 blur-[100px] rounded-full pointer-events-none"></div>

      <div class="relative z-10 h-full">
        <!-- Step 1: Scenario Selection -->
        <transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="transform opacity-0 translate-x-4"
          enter-to-class="transform opacity-100 translate-x-0"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="transform opacity-100 translate-x-0"
          leave-to-class="transform opacity-0 -translate-x-4"
          mode="out-in"
        >
          <ScenarioSelection
            v-if="currentStep === 0"
            @scenario-selected="handleScenarioSelected"
            class="h-full"
          />

          <!-- Step 2: Target Input -->
          <component
            v-else-if="currentStep === 1"
            :is="targetInputComponent"
            :scenario="selectedScenario"
            @target-configured="handleTargetConfigured"
            @back="currentStep--"
            class="h-full"
          />

          <!-- Step 3: Analysis Config -->
          <AnalysisConfig
            v-else-if="currentStep === 2"
            :scenario="selectedScenario"
            @config-complete="handleConfigComplete"
            @back="currentStep--"
            class="h-full"
          />

          <!-- Step 4: Analysis Progress -->
          <AnalysisProgress
            v-else-if="currentStep === 3"
            :session-id="sessionId"
            :scenario="selectedScenario"
            :depth="analysisConfig.depth"
            @analysis-complete="handleAnalysisComplete"
            class="h-full"
          />
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import analysisServiceV2 from '@/services/analysisServiceV2.js';

import ScenarioSelection from '@/components/analysis/ScenarioSelection.vue';
import EarlyStageInput from '@/components/analysis/EarlyStageInput.vue';
import GrowthInput from '@/components/analysis/GrowthInput.vue';
import PublicMarketInput from '@/components/analysis/PublicMarketInput.vue';
import AlternativeInput from '@/components/analysis/AlternativeInput.vue';
import IndustryResearchInput from '@/components/analysis/IndustryResearchInput.vue';
import AnalysisConfig from '@/components/analysis/AnalysisConfig.vue';
import AnalysisProgress from '@/components/analysis/AnalysisProgress.vue';

const { t } = useLanguage();

// Current Step
const currentStep = ref(0);

// Steps Definition
const steps = computed(() => [
  { label: t('analysisWizard.selectScenario') || 'Select Scenario' },
  { label: t('analysisWizard.inputTarget') || 'Target Input' },
  { label: t('analysisWizard.configAnalysis') || 'Configuration' },
  { label: t('analysisWizard.analyzing') || 'Analysis' }
]);

// Selected Scenario
const selectedScenario = ref(null);

// Target Config
const targetConfig = ref({});

// Analysis Config
const analysisConfig = ref({
  depth: 'quick', // quick | standard | comprehensive
  timeframe: '1Y',
  focus_areas: [],
  language: 'zh'
});

// Session ID
const sessionId = ref(null);

// Dynamic Target Input Component
const targetInputComponent = computed(() => {
  if (!selectedScenario.value) return null;

  const componentMap = {
    'early-stage-investment': EarlyStageInput,
    'growth-investment': GrowthInput,
    'public-market-investment': PublicMarketInput,
    'alternative-investment': AlternativeInput,
    'industry-research': IndustryResearchInput
  };

  return componentMap[selectedScenario.value.id];
});

// Handle Scenario Selection
function handleScenarioSelected(scenario) {
  console.log('[Wizard] Scenario selected:', scenario);
  selectedScenario.value = scenario;
  currentStep.value = 1;
}

// Handle Target Configuration
function handleTargetConfigured(config) {
  console.log('[Wizard] Target configured:', config);
  targetConfig.value = config;
  currentStep.value = 2;
}

// Handle Config Completion
async function handleConfigComplete(config) {
  console.log('[Wizard] Config complete:', config);
  analysisConfig.value = config;

  // Start Analysis
  try {
    const request = {
      project_name: targetConfig.value.company_name || 'Analysis Project',
      scenario: selectedScenario.value.id,
      target: targetConfig.value,
      config: analysisConfig.value
    };

    // Mock API call for now if service is missing or fails
    // const result = await analysisServiceV2.startAnalysis(request);
    // sessionId.value = result.sessionId;
    
    // Simulate success for UI demo
    sessionId.value = 'mock-session-' + Date.now();

    // Move to progress step
    currentStep.value = 3;

  } catch (error) {
    console.error('[Wizard] Failed to start analysis:', error);
    alert('Failed to start analysis: ' + error.message);
  }
}

// Handle Analysis Completion
function handleAnalysisComplete(result) {
  console.log('[Wizard] Analysis complete:', result);
  // TODO: Navigate to report view
}
</script>