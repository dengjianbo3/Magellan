<template>
  <aside
    :class="[
      'flex flex-col flex-shrink-0 bg-background-dark border-r border-border-color p-4 text-text-primary transition-all duration-300 ease-in-out',
      collapsed ? 'w-[72px]' : 'w-64'
    ]"
  >
    <!-- Logo & Collapse Button -->
    <div :class="['flex items-center mb-8', collapsed ? 'justify-center px-2' : 'justify-between px-2']">
      <div class="flex items-center gap-3 overflow-hidden">
        <!-- Megellan Logo -->
        <svg
          class="w-10 h-10 text-primary flex-shrink-0"
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

        <!-- Brand Text -->
        <div v-show="!collapsed" class="flex flex-col whitespace-nowrap">
          <h1 class="text-base font-bold leading-normal">Megellan</h1>
          <p class="text-text-secondary text-sm font-normal leading-normal">AI Investment Analysis</p>
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
          'group flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
          activeTab === item.id
            ? 'bg-surface border border-border-color'
            : 'hover:bg-surface/50'
        ]"
      >
        <span
          :class="[
            'material-symbols-outlined',
            activeTab === item.id ? 'text-primary' : 'text-text-secondary group-hover:text-text-primary'
          ]"
        >
          {{ item.icon }}
        </span>
        <p
          v-show="!collapsed"
          :class="[
            'text-sm font-semibold leading-normal whitespace-nowrap',
            activeTab === item.id ? 'text-text-primary' : 'text-text-secondary group-hover:text-text-primary'
          ]"
        >
          {{ item.label }}
        </p>
      </button>
    </nav>

    <!-- Bottom Actions -->
    <div class="flex flex-col gap-4">
      <!-- Start New Analysis Button -->
      <button
        :class="[
          'flex items-center justify-center overflow-hidden rounded-lg h-10 bg-primary text-background-dark text-sm font-bold leading-normal hover:bg-primary/90 transition-all duration-300',
          collapsed ? 'w-12 px-0' : 'w-full px-4'
        ]"
        @click="emit('start-analysis')"
      >
        <span v-show="!collapsed" class="truncate">{{ t('sidebar.startNewAnalysis') }}</span>
        <span v-show="collapsed" class="material-symbols-outlined">add</span>
      </button>

      <!-- Collapse Toggle -->
      <div class="border-t border-border-color">
        <button
          @click="toggleCollapse"
          class="w-full flex items-center gap-3 mt-4 px-3 py-2 rounded-lg hover:bg-surface/50 text-text-secondary hover:text-text-primary transition-colors"
        >
          <span
            :class="[
              'material-symbols-outlined transition-transform duration-300',
              collapsed ? 'rotate-180' : ''
            ]"
          >
            menu_open
          </span>
          <span v-show="!collapsed" class="text-sm font-medium whitespace-nowrap">{{ t('sidebar.collapse') }}</span>
        </button>
      </div>
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
