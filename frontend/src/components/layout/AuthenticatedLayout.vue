<template>
  <div class="relative isolate flex h-[100dvh] overflow-hidden bg-background-dark">
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
            :mobile="true"
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

      <div
        class="flex-1 overflow-auto scroll-smooth px-3 pt-14 md:px-8 md:pb-3 md:pt-4"
        :class="keyboardOpen ? 'pb-[calc(env(safe-area-inset-bottom,0px)+1rem)]' : 'pb-[calc(env(safe-area-inset-bottom,0px)+5.2rem)]'"
      >
        <div class="w-full h-full min-h-0">
          <router-view />
        </div>
      </div>

      <nav
        v-if="!keyboardOpen"
        class="mobile-bottom-nav fixed inset-x-0 bottom-0 z-40 flex items-center justify-between border-t border-white/10 bg-background-dark/92 px-2 pb-[calc(env(safe-area-inset-bottom,0px)+0.4rem)] pt-2 backdrop-blur-xl md:hidden"
        aria-label="Mobile quick navigation"
      >
        <button
          v-for="item in mobileQuickTabs"
          :key="item.id"
          type="button"
          class="flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-xl px-1.5 py-1.5 text-[11px] font-medium transition-colors"
          :class="currentTab === item.id ? 'text-primary bg-primary/15' : 'text-text-secondary hover:text-white'"
          @click="handleNavigate(item.id)"
        >
          <span class="material-symbols-outlined text-[20px]">{{ item.icon }}</span>
          <span class="truncate">{{ item.label }}</span>
        </button>
      </nav>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useLanguage } from '@/composables/useLanguage';
import AppSidebar from './AppSidebar.vue';

const router = useRouter();
const route = useRoute();
const { t } = useLanguage();
const mobileSidebarOpen = ref(false);
const keyboardOpen = ref(false);
let detachViewportListener = null;

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

const mobileQuickTabs = computed(() => [
  { id: 'chat', icon: 'chat', label: t('sidebar.chat') },
  { id: 'analysis', icon: 'analytics', label: t('sidebar.analysis') },
  { id: 'roundtable', icon: 'group', label: t('sidebar.roundtable') },
  { id: 'knowledge', icon: 'database', label: t('sidebar.knowledge') },
  { id: 'settings', icon: 'settings', label: t('sidebar.settings') },
]);

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

onMounted(() => {
  const win = window;
  const viewport = win.visualViewport;
  if (!viewport) return;

  const baselineHeight = viewport.height;
  const threshold = Math.max(120, baselineHeight * 0.2);

  const onViewportChange = () => {
    const delta = baselineHeight - viewport.height;
    keyboardOpen.value = delta > threshold;
  };

  viewport.addEventListener('resize', onViewportChange);
  viewport.addEventListener('scroll', onViewportChange);
  detachViewportListener = () => {
    viewport.removeEventListener('resize', onViewportChange);
    viewport.removeEventListener('scroll', onViewportChange);
  };
});

onUnmounted(() => {
  if (typeof detachViewportListener === 'function') {
    detachViewportListener();
    detachViewportListener = null;
  }
});
</script>
