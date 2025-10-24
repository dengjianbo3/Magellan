import { ref, computed } from 'vue';

type Theme = 'dark';

// 全局主题状态 - 固定为深色
const currentTheme = ref<Theme>('dark');

/**
 * 主题管理 Hook - 固定深色主题
 */
export function useTheme() {
  // 应用主题到 DOM
  const applyTheme = () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    currentTheme.value = 'dark';
  };

  // 切换主题 - 禁用（固定深色）
  const toggleTheme = () => {
    // 不做任何操作，保持深色主题
    console.log('Theme is locked to dark mode');
  };

  // 设置特定主题 - 禁用（固定深色）
  const setTheme = () => {
    applyTheme();
  };

  // 初始化主题
  const initTheme = () => {
    applyTheme();
  };

  return {
    // 状态 - 固定为深色
    currentTheme: computed(() => 'dark' as Theme),
    isDark: computed(() => true),
    isLight: computed(() => false),
    
    // 方法
    toggleTheme,
    setTheme,
    initTheme
  };
}

// 在应用启动时初始化主题
export function initThemeOnStartup() {
  const { initTheme } = useTheme();
  initTheme();
}
