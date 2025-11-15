<template>
  <div class="flex h-screen bg-background-dark overflow-hidden">
    <!-- Sidebar -->
    <AppSidebar
      :active-tab="activeTab"
      @navigate="handleNavigate"
      @start-analysis="handleStartAnalysis"
    />

    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Top Bar -->
      <header class="flex items-center justify-between px-6 py-4 bg-surface border-b border-border-color">
        <div class="flex items-center gap-3">
          <h2 class="text-xl font-bold text-text-primary">{{ currentPageTitle }}</h2>
        </div>

        <div class="flex items-center gap-4">
          <!-- Search -->
          <div class="relative">
            <input
              type="text"
              placeholder="Search..."
              class="w-64 px-4 py-2 pl-10 rounded-lg bg-background-dark border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
            />
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
              search
            </span>
          </div>

          <!-- Notifications -->
          <button class="relative p-2 rounded-lg hover:bg-background-dark transition-colors">
            <span class="material-symbols-outlined text-text-secondary">
              notifications
            </span>
            <span class="absolute top-1 right-1 w-2 h-2 bg-accent-red rounded-full"></span>
          </button>

          <!-- User Menu -->
          <div class="flex items-center gap-3 pl-4 border-l border-border-color">
            <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <span class="text-background-dark text-sm font-bold">{{ userInitials }}</span>
            </div>
            <div class="flex flex-col">
              <p class="text-sm font-semibold text-text-primary">{{ userName }}</p>
              <p class="text-xs text-text-secondary">{{ userRole }}</p>
            </div>
          </div>
        </div>
      </header>

      <!-- Content Area -->
      <div class="flex-1 overflow-auto p-6">
        <slot></slot>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import AppSidebar from './AppSidebar.vue';

const props = defineProps({
  activeTab: {
    type: String,
    default: 'dashboard'
  },
  userName: {
    type: String,
    default: 'John Doe'
  },
  userRole: {
    type: String,
    default: 'Analyst'
  }
});

const emit = defineEmits(['navigate', 'start-analysis']);

const pageTitles = {
  dashboard: 'Dashboard',
  reports: 'Reports',
  analysis: 'Analysis',
  roundtable: 'Roundtable Discussion',
  agents: 'AI Agents',
  knowledge: 'Knowledge Base',
  settings: 'Settings'
};

const currentPageTitle = computed(() => pageTitles[props.activeTab] || 'Dashboard');

const userInitials = computed(() => {
  return props.userName
    .split(' ')
    .map(name => name[0])
    .join('')
    .toUpperCase();
});

const handleNavigate = (tabId) => {
  emit('navigate', tabId);
};

const handleStartAnalysis = () => {
  emit('start-analysis');
};
</script>
