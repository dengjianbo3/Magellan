# V3 主题系统实施指南

**目标**: 实现浅色/深色主题切换，默认使用友好的浅色主题  
**参考**: SubTracker 应用设计  
**优先级**: P0 - 立即实施

---

## 🎨 主题对比

### 浅色主题（Light Theme - 默认）
- 背景：浅灰蓝渐变
- 卡片：白色
- 文字：深色
- **适用场景**：日间办公、长时间使用

### 深色主题（Dark Theme - Base44）
- 背景：深蓝黑
- 卡片：暗色
- 文字：浅色
- **适用场景**：夜间工作、偏好深色的用户

---

## 📁 文件结构

```
frontend/src/
├── styles/
│   ├── themes/
│   │   ├── light.css          # 浅色主题（新增）
│   │   ├── dark.css           # 深色主题（Base44）
│   │   └── theme-variables.css # 主题变量定义
│   ├── components/
│   │   ├── button.css
│   │   ├── card.css
│   │   └── ...
│   └── main.css
├── composables/
│   └── useTheme.ts            # 主题切换逻辑
└── components/
    └── ThemeToggle.vue        # 主题切换按钮
```

---

## 🛠️ 实施步骤

### 步骤 1: 创建主题变量文件

#### `frontend/src/styles/themes/theme-variables.css`

```css
/* 
 * 主题变量定义
 * 所有颜色、间距、圆角等都通过 CSS 变量定义
 */

/* 默认主题（浅色） */
:root {
  /* 背景色 */
  --bg-primary: #f0f4f8;
  --bg-secondary: #ffffff;
  --bg-tertiary: #f8f9fa;
  --bg-gradient: linear-gradient(135deg, #f0f4f8 0%, #e8eef3 100%);
  
  /* 文字颜色 */
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --text-tertiary: #999999;
  --text-inverse: #ffffff;
  
  /* 边框颜色 */
  --border-light: #e0e0e0;
  --border-medium: #bdbdbd;
  --border-dark: #9e9e9e;
  
  /* 强调色 */
  --accent-primary: #2196f3;
  --accent-primary-hover: #1976d2;
  --accent-primary-light: #e3f2fd;
  
  /* 状态颜色 */
  --success: #4caf50;
  --success-light: #e8f5e9;
  --success-dark: #2e7d32;
  
  --warning: #ff9800;
  --warning-light: #fff3e0;
  --warning-dark: #ef6c00;
  
  --danger: #f44336;
  --danger-light: #ffebee;
  --danger-dark: #c62828;
  
  --info: #2196f3;
  --info-light: #e3f2fd;
  --info-dark: #1565c0;
  
  /* 阴影 */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.08);
  --shadow-xl: 0 12px 32px rgba(0, 0, 0, 0.12);
  
  /* 圆角 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;
  
  /* 间距 */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  /* 字体 */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-mono: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  
  /* 字号 */
  --text-xs: 12px;
  --text-sm: 13px;
  --text-base: 14px;
  --text-lg: 16px;
  --text-xl: 18px;
  --text-2xl: 24px;
  --text-3xl: 32px;
  
  /* 标签颜色 */
  --tag-ai-bg: #e3f2fd;
  --tag-ai-text: #1565c0;
  
  --tag-saas-bg: #f1f8e9;
  --tag-saas-text: #558b2f;
  
  --tag-hardware-bg: #fff3e0;
  --tag-hardware-text: #ef6c00;
  
  /* 图表颜色 */
  --chart-1: #42a5f5;
  --chart-2: #66bb6a;
  --chart-3: #ffa726;
  --chart-4: #ab47bc;
  --chart-5: #26c6da;
}

/* 深色主题 */
[data-theme="dark"] {
  /* 背景色 */
  --bg-primary: #0A0E1A;
  --bg-secondary: #131829;
  --bg-tertiary: #1a2035;
  --bg-gradient: linear-gradient(135deg, #0A0E1A 0%, #131829 100%);
  
  /* 文字颜色 */
  --text-primary: #e8eaf0;
  --text-secondary: #9ba3b4;
  --text-tertiary: #6b7280;
  --text-inverse: #1a1a1a;
  
  /* 边框颜色 */
  --border-light: #2d3748;
  --border-medium: #4a5568;
  --border-dark: #718096;
  
  /* 强调色 */
  --accent-primary: #3B82F6;
  --accent-primary-hover: #2563eb;
  --accent-primary-light: #1e3a5f;
  
  /* 状态颜色 */
  --success: #10B981;
  --success-light: #1a3a2e;
  --success-dark: #059669;
  
  --warning: #F59E0B;
  --warning-light: #3a2f1a;
  --warning-dark: #d97706;
  
  --danger: #EF4444;
  --danger-light: #3a1a1a;
  --danger-dark: #dc2626;
  
  --info: #3B82F6;
  --info-light: #1e3a5f;
  --info-dark: #2563eb;
  
  /* 阴影 */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
  --shadow-xl: 0 12px 32px rgba(0, 0, 0, 0.6);
  
  /* 标签颜色 - 深色版本 */
  --tag-ai-bg: #1e3a5f;
  --tag-ai-text: #60a5fa;
  
  --tag-saas-bg: #1a3a2e;
  --tag-saas-text: #86efac;
  
  --tag-hardware-bg: #3a2f1a;
  --tag-hardware-text: #fbbf24;
}
```

---

### 步骤 2: 创建主题切换逻辑

#### `frontend/src/composables/useTheme.ts`

```typescript
import { ref, watch, onMounted } from 'vue';

type Theme = 'light' | 'dark';

const THEME_STORAGE_KEY = 'subtracker-theme';

const currentTheme = ref<Theme>('light');

export function useTheme() {
  // 获取保存的主题或使用默认主题（浅色）
  const getSavedTheme = (): Theme => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return (saved === 'dark' || saved === 'light') ? saved : 'light';
  };

  // 应用主题到 DOM
  const applyTheme = (theme: Theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    currentTheme.value = theme;
  };

  // 切换主题
  const toggleTheme = () => {
    const newTheme: Theme = currentTheme.value === 'light' ? 'dark' : 'light';
    applyTheme(newTheme);
    localStorage.setItem(THEME_STORAGE_KEY, newTheme);
  };

  // 设置特定主题
  const setTheme = (theme: Theme) => {
    applyTheme(theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  };

  // 初始化主题
  onMounted(() => {
    const savedTheme = getSavedTheme();
    applyTheme(savedTheme);
  });

  return {
    currentTheme,
    toggleTheme,
    setTheme,
    isDark: computed(() => currentTheme.value === 'dark'),
    isLight: computed(() => currentTheme.value === 'light')
  };
}
```

---

### 步骤 3: 创建主题切换组件

#### `frontend/src/components/ThemeToggle.vue`

```vue
<template>
  <button 
    class="theme-toggle"
    @click="toggleTheme"
    :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
  >
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
import { useTheme } from '@/composables/useTheme';

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
  transition: all 0.2s ease;
  color: var(--text-secondary);
}

.theme-toggle:hover {
  background: var(--border-light);
  color: var(--text-primary);
  transform: rotate(10deg);
}

.theme-toggle:active {
  transform: scale(0.95) rotate(10deg);
}

.icon-sun,
.icon-moon {
  transition: all 0.3s ease;
}
</style>
```

---

### 步骤 4: 更新 App.vue

#### `frontend/src/App.vue`

```vue
<template>
  <div class="app-container">
    <!-- 顶部栏 -->
    <header class="app-header">
      <div class="header-left">
        <img src="@/assets/logo.svg" alt="SubTracker" class="logo" />
        <h1 class="app-title">SubTracker</h1>
      </div>
      <div class="header-right">
        <!-- 搜索 -->
        <button class="icon-btn" title="搜索">
          <svg class="icon" />
        </button>
        
        <!-- 主题切换 -->
        <ThemeToggle />
        
        <!-- 设置 -->
        <button class="icon-btn" title="设置">
          <svg class="icon" />
        </button>
        
        <!-- 用户头像 -->
        <div class="user-avatar">
          <img src="@/assets/avatar.jpg" alt="User" />
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="app-layout">
      <!-- 左侧导航 -->
      <aside class="app-sidebar">
        <nav class="nav-menu">
          <router-link 
            v-for="item in menuItems" 
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: $route.path === item.path }"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
        </nav>
      </aside>

      <!-- 主内容 -->
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ThemeToggle from '@/components/ThemeToggle.vue';

const menuItems = ref([
  { path: '/', icon: '🏠', label: '任务驾驶舱' },
  { path: '/reports', icon: '📊', label: '报告视图' },
  { path: '/persona', icon: '🎭', label: '机构画像' },
  { path: '/im-workbench', icon: '📝', label: 'IM 工作台' }
]);
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--bg-gradient);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-secondary);
  box-shadow: var(--shadow-sm);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 32px;
  height: 32px;
}

.app-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
}

.icon-btn:hover {
  background: var(--border-light);
  color: var(--text-primary);
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  overflow: hidden;
  border: 2px solid var(--border-light);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.app-layout {
  display: flex;
  min-height: calc(100vh - 72px);
}

.app-sidebar {
  width: 240px;
  background: var(--bg-secondary);
  padding: 24px 16px;
  box-shadow: var(--shadow-sm);
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  text-decoration: none;
  color: var(--text-secondary);
  font-size: var(--text-base);
  transition: all 0.2s;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  font-weight: 600;
}

.nav-icon {
  font-size: 20px;
}

.app-main {
  flex: 1;
  padding: 24px;
}
</style>
```

---

### 步骤 5: 更新 main.ts

#### `frontend/src/main.ts`

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'

// 导入主题变量（必须最先导入）
import './styles/themes/theme-variables.css'

// 导入其他样式
import 'element-plus/dist/index.css'
import './styles/main.css'

const app = createApp(App)

app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

---

### 步骤 6: 更新全局样式

#### `frontend/src/styles/main.css`

```css
/* 
 * 全局样式
 * 使用 CSS 变量确保主题一致性
 */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 标题 */
h1, h2, h3, h4, h5, h6 {
  color: var(--text-primary);
  font-weight: 600;
  line-height: 1.3;
}

h1 { font-size: var(--text-3xl); }
h2 { font-size: var(--text-2xl); }
h3 { font-size: var(--text-xl); }
h4 { font-size: var(--text-lg); }

/* 链接 */
a {
  color: var(--accent-primary);
  text-decoration: none;
  transition: color 0.2s;
}

a:hover {
  color: var(--accent-primary-hover);
}

/* 按钮 */
button {
  font-family: var(--font-sans);
  font-size: var(--text-base);
}

/* 输入框 */
input, textarea {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  color: var(--text-primary);
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  transition: all 0.2s;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-primary-light);
}

/* 卡片 */
.card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-md);
  transition: all 0.3s;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

/* 按钮样式 */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: 12px 24px;
  background: var(--accent-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

.btn-primary:hover {
  background: var(--accent-primary-hover);
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.4);
  transform: translateY(-1px);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: 12px 24px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: var(--border-light);
  border-color: var(--border-medium);
}

/* 标签 */
.tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 500;
}

.tag-ai {
  background: var(--tag-ai-bg);
  color: var(--tag-ai-text);
}

.tag-saas {
  background: var(--tag-saas-bg);
  color: var(--tag-saas-text);
}

.tag-hardware {
  background: var(--tag-hardware-bg);
  color: var(--tag-hardware-text);
}

/* 工具类 */
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }
.text-tertiary { color: var(--text-tertiary); }

.bg-primary { background: var(--bg-primary); }
.bg-secondary { background: var(--bg-secondary); }
.bg-tertiary { background: var(--bg-tertiary); }
```

---

## 🎯 测试清单

实施完成后，请测试以下功能：

- [ ] 默认启动时显示浅色主题
- [ ] 点击主题切换按钮，主题正确切换
- [ ] 刷新页面，主题保持不变（localStorage 生效）
- [ ] 所有页面的颜色都正确响应主题变化
- [ ] 卡片、按钮、输入框等组件在两种主题下都清晰可见
- [ ] 图标颜色随主题变化
- [ ] Element Plus 组件样式也跟随主题

---

## 📊 预期效果对比

### 浅色主题效果（推荐默认）
```
✅ 背景：渐变浅灰蓝（#f0f4f8 → #e8eef3）
✅ 卡片：纯白色（#ffffff）
✅ 文字：深色（#1a1a1a）
✅ 阴影：柔和的黑色半透明
✅ 整体感觉：明亮、清爽、专业
```

### 深色主题效果（可选）
```
✅ 背景：深蓝黑（#0A0E1A）
✅ 卡片：暗色（#131829）
✅ 文字：浅色（#e8eaf0）
✅ 阴影：深色半透明
✅ 整体感觉：酷炫、专注、护眼
```

---

## 🚀 后续优化

1. **自动主题切换** - 根据系统时间自动切换
2. **跟随系统** - 检测系统主题偏好
3. **更多主题** - 添加其他配色方案
4. **主题预览** - 添加主题预览功能

---

**实施优先级：P0 - 立即开始**  
**预计工时：4-6 小时**  
**影响范围：全局 UI**
