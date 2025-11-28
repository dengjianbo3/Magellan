<template>
  <aside
    :class="[
      'flex flex-col flex-shrink-0 bg-surface/30 backdrop-blur-xl border-r border-white/5 p-4 text-text-primary transition-all duration-300 ease-in-out relative z-50',
      collapsed ? 'w-[72px]' : 'w-64'
    ]"
  >
    <!-- Logo & Collapse Button -->
    <div :class="['flex items-center mb-8', collapsed ? 'justify-center px-2' : 'justify-between px-2']">
      <div class="flex items-center gap-3 overflow-hidden group">
        <!-- Megellan Logo -->
        <div class="relative">
          <div class="absolute inset-0 bg-primary/20 blur-lg rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          <svg
            class="w-10 h-10 text-primary relative z-10 drop-shadow-[0_0_8px_rgba(56,189,248,0.5)]"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            viewBox="0 0 24 24"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5"></path>
            <path d="M2 12l10 5 10-5"></path>
          </svg>
        </div>

        <!-- Brand Text -->
        <div v-show="!collapsed" class="flex flex-col whitespace-nowrap animate-fade-in">
          <h1 class="text-lg font-display font-bold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-white to-primary-dark">Megellan</h1>
          <p class="text-text-secondary text-xs font-medium tracking-wider">{{ t('sidebar.brandSubtitle') }}</p>
        </div>
      </div>
    </div>

    <!-- Navigation Links -->
    <nav class="flex flex-col gap-2 flex-grow">
      <button
        v-for="item in navItems"
        :key="item.id"
        @click="emit('navigate', item.id)"
        :class="[
          'group relative flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-300 overflow-hidden',
          activeTab === item.id
            ? 'bg-primary/10 text-primary'
            : 'hover:bg-white/5 text-text-secondary hover:text-text-primary'
        ]"
      >
        <!-- Active Indicator Line -->
        <div 
          v-if="activeTab === item.id" 
          class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-primary rounded-r-full shadow-[0_0_8px_rgba(56,189,248,0.8)]"
        ></div>

        <span
          :class="[
            'material-symbols-outlined transition-colors',
            activeTab === item.id ? 'text-primary drop-shadow-[0_0_5px_rgba(56,189,248,0.5)]' : 'group-hover:text-text-primary'
          ]"
        >
          {{ item.icon }}
        </span>
        <p
          v-show="!collapsed"
          :class="[
            'text-sm font-medium leading-normal whitespace-nowrap transition-colors',
            activeTab === item.id ? 'text-text-primary font-semibold' : ''
          ]"
        >
          {{ item.label }}
        </p>
      </button>
    </nav>

    <!-- Bottom Actions -->
    <div class="flex flex-col gap-4 mt-auto pt-4 border-t border-white/5">
      <!-- Start New Analysis Button -->
      <button
        :class="[
          'relative flex items-center justify-center overflow-hidden rounded-lg h-10 text-white text-sm font-bold leading-normal transition-all duration-300 group',
          'bg-gradient-to-r from-primary to-primary-dark hover:from-primary-dark hover:to-primary shadow-glow-sm hover:shadow-glow',
          collapsed ? 'w-10 mx-auto px-0' : 'w-full px-4'
        ]"
        @click="emit('start-analysis')"
      >
        <div class="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 skew-y-12"></div>
        <span v-show="!collapsed" class="relative z-10 truncate tracking-wide">{{ t('sidebar.startNewAnalysis') }}</span>
        <span v-show="collapsed" class="relative z-10 material-symbols-outlined text-lg">add</span>
      </button>

      <!-- Collapse Toggle -->
      <button
        @click="toggleCollapse"
        class="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors"
      >
        <span
          :class="[
            'material-symbols-outlined transition-transform duration-300',
            collapsed ? 'rotate-180' : ''
          ]"
        >
          menu_open
        </span>
        <span v-show="!collapsed" class="text-xs font-medium tracking-wider uppercase">{{ t('sidebar.collapse') }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLanguage } from '../../composables/useLanguage';

const { t } = useLanguage();

defineProps({
  activeTab: {
    type: String,
    default: 'dashboard'
  }
});

const emit = defineEmits(['navigate', 'start-analysis']);

const collapsed = ref(false);

// 使用 computed 让 navItems 响应语言变化
const navItems = computed(() => [
  { id: 'dashboard', icon: 'dashboard', label: t('sidebar.dashboard') },
  { id: 'reports', icon: 'article', label: t('sidebar.reports') },
  { id: 'analysis', icon: 'analytics', label: t('sidebar.analysis') },
  { id: 'roundtable', icon: 'group', label: t('sidebar.roundtable') },
  { id: 'agents', icon: 'smart_toy', label: t('sidebar.agents') },
  { id: 'knowledge', icon: 'database', label: t('sidebar.knowledge') },
  { id: 'settings', icon: 'settings', label: t('sidebar.settings') },
]);

const toggleCollapse = () => {
  collapsed.value = !collapsed.value;
};
</script>
