<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <AppSidebar
      :active-tab="currentTab"
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
          <div class="relative" ref="userMenuRef">
            <button
              @click="toggleUserMenu"
              class="flex items-center gap-3 pl-6 border-l border-white/10 hover:bg-white/5 rounded-lg px-3 py-2 transition-colors"
            >
              <div class="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-glow-sm border border-white/10">
                <span class="text-white text-sm font-bold">{{ userInitials }}</span>
              </div>
              <div class="flex flex-col text-left">
                <p class="text-sm font-semibold text-text-primary tracking-wide">{{ displayName }}</p>
                <p class="text-xs text-primary font-medium">{{ displayRole }}</p>
              </div>
              <span class="material-symbols-outlined text-text-secondary text-sm">
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
      <div class="flex-1 overflow-auto p-8 scroll-smooth">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useI18n } from '@/i18n';
import AppSidebar from './AppSidebar.vue';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const { t } = useI18n();

const showUserMenu = ref(false);
const userMenuRef = ref(null);

// Page titles mapping
const pageTitles = {
  Dashboard: 'Dashboard',
  ReportsView: 'Reports',
  AnalysisWizard: 'Analysis',
  Roundtable: 'Roundtable Discussion',
  Agents: 'AI Agents',
  Knowledge: 'Knowledge Base',
  Settings: 'Settings'
};

// Computed properties
const currentTab = computed(() => {
  const routeToTab = {
    Dashboard: 'dashboard',
    ReportsView: 'reports',
    AnalysisWizard: 'analysis',
    Roundtable: 'roundtable',
    Agents: 'agents',
    Knowledge: 'knowledge',
    Settings: 'settings'
  };
  return routeToTab[route.name] || 'dashboard';
});

const currentPageTitle = computed(() => pageTitles[route.name] || 'Dashboard');

const displayName = computed(() => authStore.userName || 'User');
const displayRole = computed(() => {
  const roleMap = {
    admin: '系统管理员',
    institution: '机构用户',
    analyst: '投资分析师',
    guest: '访客'
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

const handleClickOutside = (event) => {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target)) {
    showUserMenu.value = false;
  }
};

const handleNavigate = (tabId) => {
  const tabToRoute = {
    dashboard: 'Dashboard',
    reports: 'ReportsView',
    analysis: 'AnalysisWizard',
    roundtable: 'Roundtable',
    agents: 'Agents',
    knowledge: 'Knowledge',
    settings: 'Settings'
  };
  router.push({ name: tabToRoute[tabId] || 'Dashboard' });
};

const handleStartAnalysis = () => {
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
</script>
