<template>
  <div class="relative isolate flex h-screen overflow-hidden bg-background-dark">
    <!-- Background decoration -->
    <div class="pointer-events-none absolute inset-0 z-0">
      <div class="absolute -left-40 -top-36 h-[420px] w-[420px] rounded-full bg-primary/10 blur-3xl"></div>
      <div class="absolute -right-32 top-1/4 h-[320px] w-[320px] rounded-full bg-accent-cyan/10 blur-3xl"></div>
      <div class="absolute bottom-0 left-1/3 h-[260px] w-[420px] -translate-x-1/2 rounded-full bg-primary-dark/10 blur-3xl"></div>
    </div>

    <!-- Desktop Sidebar -->
    <div class="relative z-20 hidden h-full md:block">
      <AppSidebar
        :active-tab="currentTab"
        @navigate="handleNavigate"
      />
    </div>

    <!-- Mobile Sidebar Drawer -->
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="mobileSidebarOpen" class="fixed inset-0 z-[70] md:hidden">
        <button
          class="absolute inset-0 bg-black/60 backdrop-blur-[1px]"
          aria-label="Close navigation"
          @click="mobileSidebarOpen = false"
        />
        <div class="absolute inset-y-0 left-0">
          <AppSidebar
            :active-tab="currentTab"
            @navigate="handleNavigate"
          />
        </div>
      </div>
    </transition>

    <!-- Main Content Area -->
    <main class="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
      <button
        class="absolute left-3 top-3 z-30 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-white/8 text-text-secondary transition-colors hover:text-text-primary md:hidden"
        aria-label="Open navigation"
        @click="toggleMobileSidebar"
      >
        <span class="material-symbols-outlined">menu</span>
      </button>

      <div class="flex-1 overflow-auto scroll-smooth px-4 pb-2 pt-4 md:px-8 md:pb-3 md:pt-4">
        <div class="w-full h-full min-h-0">
          <router-view />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import AppSidebar from './AppSidebar.vue';

const router = useRouter();
const route = useRoute();
const mobileSidebarOpen = ref(false);

// Computed properties
const currentTab = computed(() => {
  const routeToTab = {
    ChatHub: 'chat',
    ReportsView: 'reports',
    AnalysisWizard: 'analysis',
    Roundtable: 'roundtable',
    AutoTrading: 'trading',
    Agents: 'agents',
    Knowledge: 'knowledge',
    Settings: 'settings'
  };
  return routeToTab[route.name] || 'chat';
});

const toggleMobileSidebar = () => {
  mobileSidebarOpen.value = !mobileSidebarOpen.value;
};

const handleNavigate = (tabId) => {
  mobileSidebarOpen.value = false;
  const tabToRoute = {
    chat: 'ChatHub',
    reports: 'ReportsView',
    analysis: 'AnalysisWizard',
    roundtable: 'Roundtable',
    trading: 'AutoTrading',
    agents: 'Agents',
    knowledge: 'Knowledge',
    settings: 'Settings'
  };
  router.push({ name: tabToRoute[tabId] || 'ChatHub' });
};


watch(
  () => route.fullPath,
  () => {
    mobileSidebarOpen.value = false;
  }
);
</script>
