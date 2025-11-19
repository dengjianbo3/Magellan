<template>
  <div class="analysis-view">
    <!-- Step 0: Scenario Selection -->
    <ScenarioSelection
      v-if="currentStep === 0"
      @scenario-selected="handleScenarioSelected"
    />

    <!-- Step 1: Input Target (Dynamic based on scenario) -->
    <div v-else-if="currentStep === 1">
      <IndustryResearchInput
        v-if="selectedScenario?.id === 'industry_research'"
        @target-configured="handleTargetConfigured"
        @back="goBack"
      />
      <PublicMarketInput
        v-else-if="selectedScenario?.id === 'public_market_dd'"
        @target-configured="handleTargetConfigured"
        @back="goBack"
      />
      <GrowthInput
        v-else-if="selectedScenario?.id === 'growth_stage_dd'"
        @target-configured="handleTargetConfigured"
        @back="goBack"
      />
      <EarlyStageInput
        v-else-if="selectedScenario?.id === 'early_stage_dd'"
        @target-configured="handleTargetConfigured"
        @back="goBack"
      />
      <AlternativeInput
        v-else-if="selectedScenario?.id === 'alternative_investment_dd'"
        @target-configured="handleTargetConfigured"
        @back="goBack"
      />
    </div>

    <!-- Step 2: Analysis Configuration -->
    <div v-else-if="currentStep === 2">
      <EarlyStageConfig
        v-if="selectedScenario?.id === 'early_stage_dd'"
        :scenario="selectedScenario"
        :target="targetData"
        @config-complete="handleConfigComplete"
        @back="goBack"
      />
      <GrowthConfig
        v-else-if="selectedScenario?.id === 'growth_stage_dd'"
        :scenario="selectedScenario"
        :target="targetData"
        @config-complete="handleConfigComplete"
        @back="goBack"
      />
      <PublicMarketConfig
        v-else-if="selectedScenario?.id === 'public_market_dd'"
        :scenario="selectedScenario"
        :target="targetData"
        @config-complete="handleConfigComplete"
        @back="goBack"
      />
      <AlternativeConfig
        v-else-if="selectedScenario?.id === 'alternative_investment_dd'"
        :scenario="selectedScenario"
        :target="targetData"
        @config-complete="handleConfigComplete"
        @back="goBack"
      />
      <IndustryResearchConfig
        v-else-if="selectedScenario?.id === 'industry_research'"
        :scenario="selectedScenario"
        :target="targetData"
        @config-complete="handleConfigComplete"
        @back="goBack"
      />
      <AnalysisConfig
        v-else
        :scenario="selectedScenario"
        :target="targetData"
        @config-complete="handleConfigComplete"
        @back="goBack"
      />
    </div>

    <!-- Step 3: Analysis in Progress -->
    <AnalysisProgress
      v-else-if="currentStep === 3"
      :session-id="sessionId"
      :scenario="selectedScenario"
      :depth="analysisDepth"
      @analysis-complete="handleAnalysisComplete"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import ScenarioSelection from '@/components/analysis/ScenarioSelection.vue';
import IndustryResearchInput from '@/components/analysis/IndustryResearchInput.vue';
import PublicMarketInput from '@/components/analysis/PublicMarketInput.vue';
import GrowthInput from '@/components/analysis/GrowthInput.vue';
import EarlyStageInput from '@/components/analysis/EarlyStageInput.vue';
import AlternativeInput from '@/components/analysis/AlternativeInput.vue';
import AnalysisConfig from '@/components/analysis/AnalysisConfig.vue';
import EarlyStageConfig from '@/components/analysis/EarlyStageConfig.vue';
import GrowthConfig from '@/components/analysis/GrowthConfig.vue';
import PublicMarketConfig from '@/components/analysis/PublicMarketConfig.vue';
import AlternativeConfig from '@/components/analysis/AlternativeConfig.vue';
import IndustryResearchConfig from '@/components/analysis/IndustryResearchConfig.vue';
import AnalysisProgress from '@/components/analysis/AnalysisProgress.vue';
import analysisServiceV2 from '@/services/analysisServiceV2.js';

// Emits
const emit = defineEmits(['analysis-complete', 'cancel']);

// State
const currentStep = ref(0);
const selectedScenario = ref(null);
const targetData = ref(null);
const configData = ref(null);
const sessionId = ref(null);
const analysisDepth = ref('quick');

// Step 0: Scenario Selected
function handleScenarioSelected(scenario) {
  console.log('[AnalysisView] Scenario selected:', scenario);
  selectedScenario.value = scenario;
  currentStep.value = 1;
}

// Step 1: Target Configured
function handleTargetConfigured(data) {
  console.log('[AnalysisView] Target configured:', data);
  targetData.value = data;
  currentStep.value = 2;
}

// Step 2: Config Complete
async function handleConfigComplete(config) {
  console.log('[AnalysisView] Config complete:', config);
  configData.value = config;

  // Start analysis
  try {
    const response = await analysisServiceV2.startAnalysis({
      scenario_id: selectedScenario.value.id,
      target: targetData.value,
      config: config,
      depth: analysisDepth.value
    });

    sessionId.value = response.session_id;
    currentStep.value = 3;
  } catch (error) {
    console.error('[AnalysisView] Failed to start analysis:', error);
    alert('Failed to start analysis: ' + error.message);
  }
}

// Step 3: Analysis Complete
function handleAnalysisComplete(result) {
  console.log('[AnalysisView] Analysis complete:', result);
  emit('analysis-complete', result);
}

// Cancel
function handleCancel() {
  console.log('[AnalysisView] Analysis cancelled');
  emit('cancel');
}

// Go back
function goBack() {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}
</script>

<style scoped>
.analysis-view {
  width: 100%;
  min-height: 100vh;
}
</style>
