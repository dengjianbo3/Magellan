<template>
  <button 
    class="theme-toggle"
    @click="toggleTheme"
    :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
    :aria-label="isDark ? '切换到浅色模式' : '切换到深色模式'"
  >
    <!-- 太阳图标（浅色模式） -->
    <svg 
      v-if="isLight" 
      class="icon-sun"
      xmlns="http://www.w3.org/2000/svg" 
      width="20" 
      height="20" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      stroke-width="2" 
      stroke-linecap="round" 
      stroke-linejoin="round"
    >
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
    
    <!-- 月亮图标（深色模式） -->
    <svg 
      v-else 
      class="icon-moon"
      xmlns="http://www.w3.org/2000/svg" 
      width="20" 
      height="20" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      stroke-width="2" 
      stroke-linecap="round" 
      stroke-linejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  </button>
</template>

<script setup lang="ts">
import { useTheme } from '../composables/useTheme';

const { isDark, isLight, toggleTheme } = useTheme();
</script>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  color: var(--text-secondary);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--border-light);
  color: var(--text-primary);
  transform: rotate(10deg);
}

.theme-toggle:active {
  transform: scale(0.95) rotate(10deg);
}

.theme-toggle:focus {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-primary-light);
}

.icon-sun,
.icon-moon {
  transition: all var(--transition-slow);
  animation: icon-enter var(--transition-slow) ease-out;
}

@keyframes icon-enter {
  from {
    opacity: 0;
    transform: rotate(-90deg) scale(0.5);
  }
  to {
    opacity: 1;
    transform: rotate(0deg) scale(1);
  }
}

/* 深色模式特定样式 */
[data-theme="dark"] .theme-toggle {
  background: var(--bg-tertiary);
}

[data-theme="dark"] .theme-toggle:hover {
  background: var(--border-light);
}
</style>
