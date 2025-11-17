<script setup>
import { ref } from 'vue';
import MainLayout from './components/layout/MainLayout.vue';
import DashboardView from './views/DashboardView.vue';
import AnalysisView from './views/AnalysisView.vue';
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

const handleNavigate = (tabId) => {
  activeTab.value = tabId;
  showAgentChat.value = false;
};

const handleStartAnalysis = () => {
  activeTab.value = 'analysis';
  showAgentChat.value = false;
  console.log('Starting new analysis...');
};

const handleCancelAnalysis = () => {
  activeTab.value = 'dashboard';
  showAgentChat.value = false;
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
    <!-- Agent Chat View (Full Screen) -->
    <AgentChatView v-if="showAgentChat" :analysis-config="analysisFormData" @back="showAgentChat = false" />

    <!-- Dashboard View -->
    <DashboardView v-else-if="activeTab === 'dashboard'" @navigate="handleNavigate" />

    <!-- Reports View -->
    <ReportsView v-else-if="activeTab === 'reports'" />

    <!-- Analysis View -->
    <AnalysisView
      v-else-if="activeTab === 'analysis'"
      @cancel="handleCancelAnalysis"
      @start-analysis="handleAnalysisStart"
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
