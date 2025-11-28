<script setup>
import { ref } from 'vue';
import MainLayout from './components/layout/MainLayout.vue';
import DashboardView from './views/DashboardView.vue';
import AnalysisView from './views/AnalysisView.vue';
import AnalysisWizardView from './views/AnalysisWizardView.vue';
import AgentChatView from './views/AgentChatView.vue';
import RoundtableView from './views/RoundtableView.vue';
import ReportsView from './views/ReportsView.vue';
import AgentsView from './views/AgentsView.vue';
import KnowledgeView from './views/KnowledgeView.vue';
import SettingsView from './views/SettingsView.vue';
import ToastContainer from './components/layout/ToastContainer.vue';
import OfflineBanner from './components/layout/OfflineBanner.vue';

const activeTab = ref('dashboard');
const showAgentChat = ref(false);
const showAnalysisWizard = ref(false);

const handleNavigate = (tabId) => {
  activeTab.value = tabId;
  showAgentChat.value = false;
  showAnalysisWizard.value = false;
};

const handleStartAnalysis = () => {
  // 启动新的分析向导 V2
  showAnalysisWizard.value = true;
  showAgentChat.value = false;
  console.log('Starting new analysis wizard V2...');
};

const handleCancelAnalysis = () => {
  activeTab.value = 'dashboard';
  showAgentChat.value = false;
  showAnalysisWizard.value = false;
};

const analysisFormData = ref(null);

const handleAnalysisStart = (formData) => {
  console.log('Analysis started with:', formData);
  // Store form data for AgentChatView to use
  analysisFormData.value = formData;
  // Navigate to live analysis/chat view
  showAgentChat.value = true;
};
</script>

<template>
  <!-- Offline Banner (Global) -->
  <OfflineBanner />

  <!-- Toast Container (Global) -->
  <ToastContainer />

  <MainLayout
    :active-tab="activeTab"
    user-name="张伟"
    user-role="投资分析师"
    @navigate="handleNavigate"
    @start-analysis="handleStartAnalysis"
  >
    <!-- Analysis Wizard V2 (Full Screen) -->
    <AnalysisWizardView v-if="showAnalysisWizard" @back="showAnalysisWizard = false" />

    <!-- Agent Chat View (Full Screen) -->
    <AgentChatView v-else-if="showAgentChat" :analysis-config="analysisFormData" @back="showAgentChat = false" />

    <!-- Dashboard View -->
    <DashboardView v-else-if="activeTab === 'dashboard'" @navigate="handleNavigate" />

    <!-- Reports View -->
    <ReportsView v-else-if="activeTab === 'reports'" />

    <!-- Analysis View - 使用新的 Wizard V2 -->
    <AnalysisWizardView
      v-else-if="activeTab === 'analysis'"
      @back="activeTab = 'dashboard'"
    />

    <!-- Roundtable Discussion View -->
    <RoundtableView v-else-if="activeTab === 'roundtable'" />

    <!-- AI Agents View -->
    <AgentsView v-else-if="activeTab === 'agents'" />

    <!-- Knowledge Base View -->
    <KnowledgeView v-else-if="activeTab === 'knowledge'" />

    <!-- Settings View -->
    <SettingsView v-else-if="activeTab === 'settings'" />
  </MainLayout>
</template>
