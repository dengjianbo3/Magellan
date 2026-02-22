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
        @start-analysis="handleStartAnalysis"
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
            @start-analysis="handleStartAnalysis"
          />
        </div>
      </div>
    </transition>

    <!-- Main Content Area -->
    <main class="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
      <!-- Top Bar -->
      <header class="sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-white/10 bg-background-dark/75 px-4 py-4 backdrop-blur-xl md:px-8 md:py-5">
        <div class="flex min-w-0 items-center gap-3">
          <button
            class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-text-secondary transition-colors hover:text-text-primary md:hidden"
            aria-label="Open navigation"
            @click="toggleMobileSidebar"
          >
            <span class="material-symbols-outlined">menu</span>
          </button>
          <div class="min-w-0">
            <h2 class="truncate text-xl font-display font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-text-secondary md:text-2xl">
              {{ currentPageTitle }}
            </h2>
            <p class="hidden truncate text-xs text-text-tertiary sm:block">
              {{ currentPageSubtitle }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3 md:gap-5">
          <!-- Search -->
          <div class="relative hidden group lg:block">
            <div class="absolute inset-0 bg-primary/20 blur-md rounded-lg opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
            <input
              type="text"
              placeholder="Search..."
              class="relative z-10 w-56 rounded-lg border border-white/10 bg-white/5 px-4 py-2 pl-10 text-text-primary placeholder-text-secondary transition-all duration-300 focus:bg-surface/50 focus:outline-none focus:border-primary/50 xl:w-72"
            />
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary z-20">
              search
            </span>
          </div>

          <!-- Notifications -->
          <button class="relative hidden rounded-lg p-2 transition-colors group hover:bg-white/5 sm:inline-flex">
            <span class="material-symbols-outlined text-text-secondary group-hover:text-primary transition-colors">
              notifications
            </span>
            <span class="absolute top-2 right-2 w-2 h-2 bg-accent-cyan rounded-full shadow-[0_0_5px_rgba(6,182,212,0.8)]"></span>
          </button>

          <!-- User Menu -->
          <div class="relative" ref="userMenuRef">
            <button
              @click="toggleUserMenu"
              class="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-2 py-2 transition-colors hover:bg-white/10 md:gap-3 md:px-3"
            >
              <div class="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-glow-sm border border-white/10">
                <span class="text-white text-sm font-bold">{{ userInitials }}</span>
              </div>
              <div class="hidden text-left md:flex md:flex-col">
                <p class="text-sm font-semibold text-text-primary tracking-wide">{{ displayName }}</p>
                <p class="text-xs text-primary font-medium">{{ displayRole }}</p>
              </div>
              <span class="material-symbols-outlined hidden text-sm text-text-secondary md:inline-flex">
                {{ showUserMenu ? 'expand_less' : 'expand_more' }}
              </span>
            </button>

            <!-- Dropdown Menu -->
            <transition
              enter-active-class="transition ease-out duration-100"
              enter-from-class="transform opacity-0 scale-95"
              enter-to-class="transform opacity-100 scale-100"
              leave-active-class="transition ease-in duration-75"
              leave-from-class="transform opacity-100 scale-100"
              leave-to-class="transform opacity-0 scale-95"
            >
              <div
                v-if="showUserMenu"
                class="absolute right-0 mt-2 w-48 rounded-lg bg-surface border border-white/10 shadow-xl z-50"
              >
                <div class="py-1">
                  <button
                    @click="goToSettings"
                    class="flex items-center gap-2 w-full px-4 py-2 text-sm text-text-primary hover:bg-white/5 transition-colors"
                  >
                    <span class="material-symbols-outlined text-lg">settings</span>
                    {{ t('common.settings') }}
                  </button>
                  <hr class="border-white/10 my-1" />
                  <button
                    @click="handleLogout"
                    class="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-400 hover:bg-white/5 transition-colors"
                  >
                    <span class="material-symbols-outlined text-lg">logout</span>
                    {{ t('common.logout') }}
                  </button>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </header>

      <!-- Content Area -->
      <div class="flex-1 overflow-auto px-4 pb-8 pt-5 scroll-smooth md:px-8 md:pb-10 md:pt-6">
        <div class="mx-auto w-full max-w-[1520px]">
          <router-view />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useI18n } from '@/i18n';
import AppSidebar from './AppSidebar.vue';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const { t } = useI18n();

const showUserMenu = ref(false);
const mobileSidebarOpen = ref(false);
const userMenuRef = ref(null);

// Page titles mapping
const pageTitles = {
  Dashboard: 'Dashboard',
  ReportsView: 'Reports',
  AnalysisWizard: 'Analysis',
  Roundtable: 'Brainstorm Session',
  AutoTrading: 'Auto Trading',
  Agents: 'AI Agents',
  Knowledge: 'Knowledge Base',
  Settings: 'Settings'
};

const pageSubtitles = {
  Dashboard: 'Overview and key operational metrics',
  ReportsView: 'Generated analyses and exported documents',
  AnalysisWizard: 'Configure and run scenario-based analysis',
  Roundtable: 'Multi-agent expert brainstorming workspace',
  AutoTrading: 'Automated strategy monitoring and execution',
  Agents: 'AI agent capabilities and status',
  Knowledge: 'Uploaded documents and retrieval controls',
  Settings: 'Account and system preferences'
};

// Computed properties
const currentTab = computed(() => {
  const routeToTab = {
    Dashboard: 'dashboard',
    ReportsView: 'reports',
    AnalysisWizard: 'analysis',
    Roundtable: 'roundtable',
    AutoTrading: 'trading',
    Agents: 'agents',
    Knowledge: 'knowledge',
    Settings: 'settings'
  };
  return routeToTab[route.name] || 'dashboard';
});

const currentPageTitle = computed(() => {
  if (route.name === 'Roundtable') {
    return t('roundtable.title') || pageTitles[route.name] || 'Dashboard';
  }
  return pageTitles[route.name] || 'Dashboard';
});

const currentPageSubtitle = computed(() => {
  if (route.name === 'Roundtable') {
    return t('roundtable.subtitle') || pageSubtitles[route.name] || '';
  }
  return pageSubtitles[route.name] || '';
});

const displayName = computed(() => authStore.userName || 'User');
const displayRole = computed(() => {
  const roleMap = {
    admin: t('roles.admin') || 'System Administrator',
    institution: t('roles.institution') || 'Institution User',
    analyst: t('roles.analyst') || 'Investment Analyst',
    guest: t('roles.guest') || 'Guest'
  };
  return roleMap[authStore.userRole] || authStore.userRole;
});

const userInitials = computed(() => {
  const name = displayName.value;
  if (!name) return 'U';
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
});

// Methods
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value;
};

const toggleMobileSidebar = () => {
  mobileSidebarOpen.value = !mobileSidebarOpen.value;
};

const handleClickOutside = (event) => {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target)) {
    showUserMenu.value = false;
  }
};

const handleNavigate = (tabId) => {
  mobileSidebarOpen.value = false;
  const tabToRoute = {
    dashboard: 'Dashboard',
    reports: 'ReportsView',
    analysis: 'AnalysisWizard',
    roundtable: 'Roundtable',
    trading: 'AutoTrading',
    agents: 'Agents',
    knowledge: 'Knowledge',
    settings: 'Settings'
  };
  router.push({ name: tabToRoute[tabId] || 'Dashboard' });
};

const handleStartAnalysis = () => {
  mobileSidebarOpen.value = false;
  router.push({ name: 'AnalysisWizard' });
};

const goToSettings = () => {
  showUserMenu.value = false;
  router.push({ name: 'Settings' });
};

const handleLogout = async () => {
  showUserMenu.value = false;
  await authStore.logout();
  router.push({ name: 'Login' });
};

// Lifecycle
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

watch(
  () => route.fullPath,
  () => {
    mobileSidebarOpen.value = false;
  }
);
</script>
