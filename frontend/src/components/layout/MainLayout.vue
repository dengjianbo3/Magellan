<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <AppSidebar
      :active-tab="activeTab"
      @navigate="handleNavigate"
      @start-analysis="handleStartAnalysis"
    />

    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col overflow-hidden relative">
      <!-- Top Bar -->
      <header class="flex items-center justify-between px-8 py-5 bg-background-dark/60 backdrop-blur-md border-b border-white/5 z-40">
        <div class="flex items-center gap-3">
          <h2 class="text-2xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-text-secondary tracking-tight">{{ currentPageTitle }}</h2>
        </div>

        <div class="flex items-center gap-6">
          <!-- Search -->
          <div class="relative group">
            <div class="absolute inset-0 bg-primary/20 blur-md rounded-lg opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
            <input
              type="text"
              placeholder="Search..."
              class="relative z-10 w-64 px-4 py-2 pl-10 rounded-lg bg-white/5 border border-white/10 text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary/50 focus:bg-surface/50 transition-all duration-300"
            />
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary z-20">
              search
            </span>
          </div>

          <!-- Notifications -->
          <button class="relative p-2 rounded-lg hover:bg-white/5 transition-colors group">
            <span class="material-symbols-outlined text-text-secondary group-hover:text-primary transition-colors">
              notifications
            </span>
            <span class="absolute top-2 right-2 w-2 h-2 bg-accent-cyan rounded-full shadow-[0_0_5px_rgba(6,182,212,0.8)]"></span>
          </button>

          <!-- User Menu -->
          <div class="flex items-center gap-3 pl-6 border-l border-white/10">
            <div class="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-glow-sm border border-white/10">
              <span class="text-white text-sm font-bold">{{ userInitials }}</span>
            </div>
            <div class="flex flex-col">
              <p class="text-sm font-semibold text-text-primary tracking-wide">{{ userName }}</p>
              <p class="text-xs text-primary font-medium">{{ userRole }}</p>
            </div>
          </div>
        </div>
      </header>

      <!-- Content Area -->
      <div class="flex-1 overflow-auto p-8 scroll-smooth">
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
