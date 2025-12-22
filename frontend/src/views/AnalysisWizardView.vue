<template>
  <div class="max-w-7xl mx-auto p-8 min-h-screen flex flex-col">
    <!-- Back Button -->
    <button 
      v-if="currentStep === 1"
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

          <!-- Step 2: Unified Analysis Form (Target Input + Config) -->
          <UnifiedAnalysisForm
            v-else-if="currentStep === 1"
            :scenario="selectedScenario"
            @analysis-start="handleAnalysisStart"
            @back="currentStep--"
            class="h-full"
          />

          <!-- Step 3: Analysis Progress -->
          <AnalysisProgress
            v-else-if="currentStep === 2"
            :session-id="sessionId"
            :scenario="selectedScenario"
            :depth="analysisConfig.depth"
            :project-name="targetConfig.company_name || targetConfig.target_name || targetConfig.industry_name"
            :target-data="targetConfig"
            @analysis-complete="handleAnalysisComplete"
            @upgrade="handleUpgradeToStandard"
            class="h-full"
          />
        </transition>
      </div>
    </div>

    <!-- Session Recovery Dialog -->
    <div
      v-if="showRecoveryDialog && pendingSession"
      class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50"
    >
      <div class="glass-panel border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
        <div class="flex flex-col items-center text-center mb-6">
          <div class="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center mb-4 shadow-[0_0_20px_rgba(56,189,248,0.3)]">
            <span class="material-symbols-outlined text-primary text-3xl">history</span>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">{{ t('analysisWizard.sessionRecovery') || '检测到未完成的分析' }}</h3>
          <p class="text-sm text-text-secondary">
            {{ t('analysisWizard.sessionRecoveryDesc') || '您有一个进行中的分析任务，是否要继续？' }}
          </p>
        </div>

        <!-- Session Info -->
        <div class="mb-6 p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="flex items-center justify-between mb-2">
            <span class="text-text-secondary text-sm">{{ t('analysisWizard.projectName') || '项目名称' }}</span>
            <span class="text-white font-medium">{{ pendingSession.projectName }}</span>
          </div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-text-secondary text-sm">{{ t('analysisWizard.scenario') || '分析场景' }}</span>
            <span class="text-primary font-medium">{{ pendingSession.scenario?.name || pendingSession.scenario?.id }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-text-secondary text-sm">{{ t('analysisWizard.startedAt') || '开始时间' }}</span>
            <span class="text-text-secondary text-sm">{{ new Date(pendingSession.startedAt).toLocaleString() }}</span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <button
            @click="dismissRecovery"
            class="flex-1 px-6 py-3 rounded-xl border border-white/10 text-white hover:bg-white/10 transition-colors font-bold"
          >
            {{ t('analysisWizard.startNew') || '开始新分析' }}
          </button>
          <button
            @click="recoverSession"
            class="flex-1 px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white hover:shadow-glow transition-all font-bold"
          >
            {{ t('analysisWizard.continueSession') || '继续分析' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useLanguage } from '@/composables/useLanguage.js';
import { useToast } from '@/composables/useToast';
import analysisServiceV2 from '@/services/analysisServiceV2.js';
import sessionManager from '@/services/sessionManager.js';

import ScenarioSelection from '@/components/analysis/ScenarioSelection.vue';
import UnifiedAnalysisForm from '@/components/analysis/UnifiedAnalysisForm.vue';
import AnalysisProgress from '@/components/analysis/AnalysisProgress.vue';

const { t } = useLanguage();
const { error } = useToast();
const router = useRouter();

// Current Step
const currentStep = ref(0);

// Steps Definition
const steps = computed(() => [
  { label: t('analysisWizard.selectScenario') || 'Select Scenario' },
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

// Session Recovery State
const showRecoveryDialog = ref(false);
const pendingSession = ref(null);

// Check for active sessions on mount
onMounted(() => {
  checkForActiveSessions();
});

function checkForActiveSessions() {
  const activeSessions = sessionManager.getActiveSessions();
  console.log('[Wizard] Active sessions:', activeSessions);

  if (activeSessions.length > 0) {
    // Filter out stale sessions (older than 24 hours)
    const MAX_SESSION_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours
    const now = Date.now();

    const validSessions = activeSessions.filter(session => {
      const sessionAge = now - (session.startedAt || 0);
      if (sessionAge > MAX_SESSION_AGE_MS) {
        // Mark stale session as failed and skip it
        console.log('[Wizard] Cleaning stale session:', session.sessionId, 'age:', Math.round(sessionAge / 3600000), 'hours');
        sessionManager.updateSession(session.sessionId, { status: 'failed' });
        return false;
      }
      return true;
    });

    if (validSessions.length > 0) {
      // Show recovery dialog for the most recent valid session
      pendingSession.value = validSessions[0];
      showRecoveryDialog.value = true;
    }
  }
}

// Recover session
async function recoverSession() {
  if (!pendingSession.value) return;

  console.log('[Wizard] Recovering session:', pendingSession.value.sessionId);

  // Restore state
  selectedScenario.value = pendingSession.value.scenario;
  targetConfig.value = pendingSession.value.targetData;
  analysisConfig.value = pendingSession.value.configData;
  sessionId.value = pendingSession.value.sessionId;

  // Move to progress step
  currentStep.value = 2;

  // Close dialog
  showRecoveryDialog.value = false;
  pendingSession.value = null;
}

// Dismiss recovery and start fresh
function dismissRecovery() {
  if (pendingSession.value) {
    // Mark session as completed/failed
    sessionManager.updateSession(pendingSession.value.sessionId, {
      status: 'failed'
    });
  }

  showRecoveryDialog.value = false;
  pendingSession.value = null;
}

// Handle Scenario Selection
function handleScenarioSelected(scenario) {
  console.log('[Wizard] Scenario selected:', scenario);
  selectedScenario.value = scenario;
  currentStep.value = 1;
}

// Handle Analysis Start (Target + Config combined)
async function handleAnalysisStart(data) {
  console.log('[Wizard] Analysis starting with:', data);

  const { target, config } = data;
  targetConfig.value = target;
  analysisConfig.value = config;

  // Start Analysis
  try {
    // Prepare service state (reset buffer, disconnect old sessions)
    analysisServiceV2.prepare();

    // IMPORTANT: Reset component-level sessionId to ensure we use the new session
    sessionId.value = null;

    const request = {
      project_name: target.company_name || target.target_name || target.industry_name || 'Analysis Project',
      scenario: selectedScenario.value.id,
      target: target,
      config: config
    };

    console.log('[Wizard] Starting real analysis...', request);

    // IMPORTANT: Move to progress step FIRST so AnalysisProgress can mount and register listeners
    // before workflow_start message arrives
    currentStep.value = 2;

    // Small delay to ensure component is fully mounted
    await new Promise(resolve => setTimeout(resolve, 100));

    // Real API call
    const result = await analysisServiceV2.startAnalysis(request);
    sessionId.value = result.sessionId;

    console.log('[Wizard] Analysis started successfully:', result);

    // Save session to SessionManager
    sessionManager.saveSession({
      sessionId: sessionId.value,
      projectName: request.project_name,
      scenario: selectedScenario.value,
      targetData: target,
      configData: config,
      status: 'running',
      progress: 0,
      currentStep: 0,
      startedAt: Date.now()
    });

    console.log('[Wizard] Session saved to localStorage');

  } catch (err) {
    console.error('[Wizard] Failed to start analysis:', err);
    error(t('analysisWizard.analysisError') + ': ' + (err.message || t('analysisWizard.unknownError')));

    // Go back to config step on error
    currentStep.value = 2;
  }
}

// Handle Analysis Completion
function handleAnalysisComplete(result) {
  console.log('[Wizard] Analysis complete:', result);
  console.log('[Wizard] Current sessionId.value:', sessionId.value);
  console.log('[Wizard] Service sessionId:', analysisServiceV2.sessionId);

  if (result?.view === 'report') {
    // User clicked "查看完整报告"
    // Navigate to the report view with the session ID
    // Use the service's sessionId as the source of truth (in case component ref is stale)
    const reportSessionId = analysisServiceV2.sessionId || sessionId.value;
    console.log('[Wizard] Navigating to report with sessionId:', reportSessionId);

    if (reportSessionId) {
        router.push({
        name: 'ReportsView',
        query: {
            sessionId: reportSessionId
        }
        });
    } else {
        error(t('analysisWizard.sessionNotFound'));
    }
  }
}

// Handle Upgrade to Standard Analysis
async function handleUpgradeToStandard(upgradeData) {
  console.log('[Wizard] Upgrading to standard analysis:', upgradeData);

  try {
    // Reset session ID to prepare for new analysis
    sessionId.value = null;

    // Update config to standard depth
    analysisConfig.value = {
      ...analysisConfig.value,
      depth: 'standard'
    };

    // Use the upgrade method from service
    const result = await analysisServiceV2.upgradeToStandard({
      projectName: upgradeData.projectName,
      scenarioId: upgradeData.scenario?.id || selectedScenario.value?.id,
      target: upgradeData.target || targetConfig.value,
      originalConfig: analysisConfig.value
    });

    sessionId.value = result.sessionId;
    console.log('[Wizard] Standard analysis started:', result);

    // Update session manager
    sessionManager.saveSession({
      sessionId: sessionId.value,
      projectName: upgradeData.projectName,
      scenario: selectedScenario.value,
      targetData: targetConfig.value,
      configData: analysisConfig.value,
      status: 'running',
      progress: 0,
      currentStep: 0,
      startedAt: Date.now()
    });

  } catch (err) {
    console.error('[Wizard] Failed to upgrade to standard analysis:', err);
    error(t('analysisWizard.analysisError') + ': ' + (err.message || t('analysisWizard.unknownError')));
  }
}
</script>