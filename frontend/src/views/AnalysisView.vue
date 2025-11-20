<template>
  <div class="analysis-view">
    <!-- Step 0: Scenario Selection -->
    <ScenarioSelection
      v-if="currentStep === 0"
      @scenario-selected="handleScenarioSelected"
    />

    <!-- Step 1: Unified Analysis Form (Target Input + Config) -->
    <UnifiedAnalysisForm
      v-else-if="currentStep === 1"
      :scenario="selectedScenario"
      @analysis-start="handleAnalysisStart"
      @back="goBack"
    />

    <!-- Step 2: Analysis in Progress -->
    <AnalysisProgress
      v-else-if="currentStep === 2"
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
import UnifiedAnalysisForm from '@/components/analysis/UnifiedAnalysisForm.vue';
import AnalysisProgress from '@/components/analysis/AnalysisProgress.vue';
import analysisServiceV2 from '@/services/analysisServiceV2.js';

// Emits
const emit = defineEmits(['analysis-complete', 'cancel']);

// State
const currentStep = ref(0);
const selectedScenario = ref(null);
const sessionId = ref(null);
const analysisDepth = ref('quick');

// Step 0: Scenario Selected
function handleScenarioSelected(scenario) {
  console.log('[AnalysisView] Scenario selected:', scenario);
  selectedScenario.value = scenario;
  currentStep.value = 1;
}

// Step 1: Analysis Start (Target + Config combined)
async function handleAnalysisStart(data) {
  console.log('[AnalysisView] Analysis starting with:', data);

  const { target, config } = data;
  analysisDepth.value = config.mode || 'quick';

  // Start analysis
  try {
    const response = await analysisServiceV2.startAnalysis({
      scenario_id: selectedScenario.value.id,
      target: target,
      config: config,
      depth: analysisDepth.value
    });

    sessionId.value = response.session_id;
    currentStep.value = 2; // 现在是第2步（之前是第3步）
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
